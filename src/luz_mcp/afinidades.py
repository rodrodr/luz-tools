"""Afinidades Elegidas: collectively signed measures, their signatures, the co-authorship network
and the published network metrics, joined to the speeches of Luz y Taquígrafos.

Tables (all `ae_*`, loaded by `load`):
    ae_measures      one row per measure, with its full text and the Luz rows where it is read and defended
    ae_signatures    one row per signature
    ae_edges         one row per pair of co-signatories of a measure (the published edge list)
    ae_deputies      one row per deputy and legislature (the register)
    ae_metrics       published network metrics per deputy and period (not recomputed)
    ae_proximity     published party and family proximities (and party co-signature weights)
    ae_party_stats   published per-party statistics; ae_communities: party communities
    ae_parties · ae_topics   dictionaries
The Afinidades legislature labels (1933-1936) differ from Luz's (1933-1935): they are matched by
their starting year.
"""
from __future__ import annotations

import json
import os
import re
import tempfile
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

from parlaibero_mcp import library as libmod, store
from parlaibero_mcp.analysis import CHAIR_RX, NOT_CHAIR_RX

FILES = {
    "measures": "2REP_measures_v3.csv", "signatures": "2REP_cosponsorship_v3.csv",
    "edges": "2REP_coauthor_edgelist_v3.csv", "deputies": "representative_metadata_v3.csv",
    "metrics": "representatives_metrics_v3.json", "roles": "representatives_roles_v3.json",
    "parties": "party_dictionary_v3.csv", "topics": "topic_taxonomy_v3.csv",
}
PERIODS = ("1931-1933", "1933-1936", "1936-1939", "total")
ROLES = ("Diputado aislado", "Diputado de perfil bajo", "Cuadro de partido", "Referente de partido",
         "Articulador", "Líder de Cámara")
DOI_AE = "10.7910/DVN/CGOCUS"
GROUP_COLUMNS = {"party": "partido", "family": "familia_partidos", "ideology": "ideologia"}


def _q(sql: str, params: list | None = None, max_rows: int = 1_000_000) -> list[dict]:
    cols, rows, _ = store.run_query(sql, params or [], max_rows=max_rows)
    return [{k: store.jsonable(v) for k, v in zip(cols, r)} for r in rows]


def _csv(path: Path) -> str:
    return (f"read_csv('{str(path).replace(chr(39), chr(39) * 2)}', header=true, all_varchar=true, delim=',', "
            f"quote='\"', escape='\"', max_line_size=67108864)")


# ── loading ───────────────────────────────────────────────────────────────────

def load(con, folder: Path) -> dict:
    """(Re)create the ae_* tables from the Afinidades files in `folder`, fill the register labels of
    each Luz intervention and the deputies register, and run the checks. Returns the check report."""
    folder = Path(folder)
    f = {k: folder / v for k, v in FILES.items()}
    con.execute(f"""CREATE OR REPLACE TABLE ae_measures AS SELECT
        CAST(id_medida AS INTEGER) AS id_medida, legislatura, CAST(num_sesion AS INTEGER) AS num_sesion,
        TRY_CAST(fecha_sesion AS DATE) AS fecha_sesion, TRY_CAST(fecha_firma AS DATE) AS fecha_firma,
        TRY_CAST(diaries_id_inicio AS BIGINT) AS diaries_id_inicio, TRY_CAST(orden_diaries AS INTEGER) AS orden_diaries,
        tipo, titulo, tema_principal, nullif(tema_secundario, 'ninguno') AS tema_secundario,
        TRY_CAST(n_firmas AS INTEGER) AS n_firmas, TRY_CAST(n_firmas_ilegibles AS INTEGER) AS n_firmas_ilegibles,
        TRY_CAST(id_dip_primer_autor AS INTEGER) AS id_dip_primer_autor, primer_autor, primer_autor_original,
        defensa, TRY_CAST(id_dip_defensor AS INTEGER) AS id_dip_defensor,
        defensor_es_primer_autor = 'True' AS defensor_es_primer_autor,
        TRY_CAST(diaries_id_defensa AS BIGINT) AS diaries_id_defensa, TRY_CAST(fecha_defensa AS DATE) AS fecha_defensa,
        texto FROM {_csv(f['measures'])}""")
    con.execute(f"""CREATE OR REPLACE TABLE ae_signatures AS SELECT id_firma, CAST(id_medida AS INTEGER) AS id_medida,
        archivo, TRY_CAST(num_sesion AS INTEGER) AS num_sesion, legislatura, TRY_CAST(fecha_sesion AS DATE) AS fecha_sesion,
        TRY_CAST(fecha_firma AS DATE) AS fecha_firma, tipo_medida, truncada = '1' AS truncada,
        TRY_CAST(firmas_declaradas AS INTEGER) AS firmas_declaradas, TRY_CAST(orden_firma AS INTEGER) AS orden_firma,
        tipo_fila, nombre_original, TRY_CAST(id_dip AS INTEGER) AS id_dip, nombre_completo, distrito, partido,
        partido_historico, familia_partidos, ideologia FROM {_csv(f['signatures'])}""")
    con.execute(f"""CREATE OR REPLACE TABLE ae_edges AS SELECT CAST(id_medida AS INTEGER) AS id_medida,
        id_legislature AS legislatura, CAST(id_dip1 AS INTEGER) AS id_dip1, name_dip1,
        CAST(id_dip2 AS INTEGER) AS id_dip2, name_dip2, ideo_dip1, ideo_dip2, truncada = '1' AS truncada
        FROM {_csv(f['edges'])}""")
    con.execute(f"""CREATE OR REPLACE TABLE ae_deputies AS SELECT CAST(id_dip AS INTEGER) AS id_dip, legislatura,
        nombre_completo, nombre, apellidos, distrito, partido, partido_historico, familia_partidos, ideologia,
        nombre_completo_original, nombre_variantes FROM {_csv(f['deputies'])}""")
    con.execute(f"CREATE OR REPLACE TABLE ae_parties AS SELECT * FROM {_csv(f['parties'])}")
    con.execute(f"CREATE OR REPLACE TABLE ae_topics AS SELECT * FROM {_csv(f['topics'])}")
    _load_metrics(con, f["metrics"], f["roles"])
    _fill_register_labels(con)
    con.execute("""CREATE OR REPLACE TABLE ae_dataset AS SELECT ? AS doi, ? AS version, now() AS imported_at""",
                [DOI_AE, _version(folder)])
    return checks(con)


def _version(folder: Path) -> str | None:
    v = folder / ".version"
    return v.read_text().strip() if v.exists() else None


def _load_metrics(con, metrics_path: Path, roles_path: Path) -> None:
    m = json.loads(metrics_path.read_text(encoding="utf-8"))
    rows = []
    for dip, d in m["deputies"].items():
        for period, metrics in d.get("metrics", {}).items():
            rows.append({"id_dip": int(dip), "period": period, "nombre_completo": d.get("nombre_completo"),
                         "partido": (d.get("partido") or {}).get(period) if period != "total" else None,
                         "familia_partidos": (d.get("familia_partidos") or {}).get(period) if period != "total" else None,
                         **metrics})
    prox = []
    for kind, key in (("party", "party_proximity"), ("family", "familia_proximity"), ("party_weight", "party_weights")):
        for period, mat in m.get(key, {}).items():
            for a, row in mat.items():
                for b, v in row.items():
                    prox.append({"kind": kind, "period": period, "a": a, "b": b, "value": v})
    stats = [{"period": period, "partido": party, **{k: (json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list))
                                                         else v) for k, v in s.items()}}
             for period, d in m.get("party_stats", {}).items() for party, s in d.items()]
    comm = [{"period": period, "partido": party, "community": c, "modularity": d.get("modularity")}
            for period, d in m.get("party_communities", {}).items() for party, c in d.get("communities", {}).items()]
    roles = json.loads(roles_path.read_text(encoding="utf-8")) if roles_path.exists() else {}
    role_rows = [{"id_dip": int(dip), "period": p, "role": r} for dip, d in roles.items() for p, r in d.items()]
    meta = {"thresholds": json.dumps(m.get("meta", {}).get("thresholds"), ensure_ascii=False),
            "generated": m.get("meta", {}).get("generated")}
    with tempfile.TemporaryDirectory() as tmp:
        for name, data in (("ae_metrics", rows), ("ae_proximity", prox), ("ae_party_stats", stats),
                           ("ae_communities", comm), ("ae_roles", role_rows), ("ae_metrics_meta", [meta])):
            path = os.path.join(tmp, f"{name}.json")
            with open(path, "w", encoding="utf-8") as fh:
                for r in data:
                    fh.write(json.dumps(r, ensure_ascii=False) + "\n")
            con.execute(f"CREATE OR REPLACE TABLE {name} AS SELECT * FROM read_json_auto(?, format='newline_delimited',"
                        f" sample_size=-1)", [path])


def _fill_register_labels(con) -> None:
    """Each Luz intervention gets its speaker's labels in the Afinidades register for that
    legislature (matched by the year it starts), and the deputies table is the register."""
    con.execute("""UPDATE interventions AS i SET reg_party = d.partido, reg_family = d.familia_partidos,
                   reg_ideology = d.ideologia FROM ae_deputies d
                   WHERE i.country = 'LT' AND i.id_dep = CAST(d.id_dip AS VARCHAR)
                     AND left(i.legislature, 4) = left(d.legislatura, 4)""")
    for col in ("party_family", "ideology", "reg_party", "reg_family", "reg_ideology"):
        con.execute(f"ALTER TABLE deputies ADD COLUMN IF NOT EXISTS {col} VARCHAR")
    con.execute("DELETE FROM deputies WHERE country = 'LT'")
    # the term of every member: from the first to the last sitting of that legislature in Luz
    con.execute("""INSERT INTO deputies BY NAME
        SELECT 'LT' AS country, CAST(d.id_dip AS VARCHAR) AS id_dep, d.nombre_completo AS speaker_name,
               d.nombre AS first_name, d.apellidos AS last_name, d.partido AS party,
               d.partido_historico AS parliamentary_group, d.distrito AS district, d.legislatura AS legislature,
               CAST(s.d0 AS VARCHAR) AS start_date, CAST(s.d1 AS VARCHAR) AS end_date, d.nombre_variantes AS notes,
               d.familia_partidos AS party_family, d.ideologia AS ideology,
               d.partido AS reg_party, d.familia_partidos AS reg_family, d.ideologia AS reg_ideology
        FROM ae_deputies d JOIN (SELECT left(legislature, 4) AS y, min(date) AS d0, max(date) AS d1
                                 FROM interventions WHERE country = 'LT' GROUP BY 1) s
          ON s.y = left(d.legislatura, 4)""")


def checks(con) -> dict:
    """Independent checks of the loaded tables: published counts, links to Luz, and the published
    degree against the one recomputed from the edge list."""
    one = lambda sql: con.execute(sql).fetchone()[0]
    rep = {
        "measures": one("SELECT count(*) FROM ae_measures"),
        "signatures": one("SELECT count(*) FROM ae_signatures"),
        "edges": one("SELECT count(*) FROM ae_edges"),
        "deputy_legislatures": one("SELECT count(*) FROM ae_deputies"),
        "deputies": one("SELECT count(DISTINCT id_dip) FROM ae_deputies"),
        "deputies_with_coauthorship": one("SELECT count(DISTINCT x) FROM (SELECT id_dip1 x FROM ae_edges "
                                          "UNION SELECT id_dip2 FROM ae_edges)"),
        "measures_defended": one("SELECT count(*) FROM ae_measures WHERE defensa = 'sí'"),
    }
    # every Luz row a measure points to exists, and is in the measure's session date
    rep["start_rows_missing"] = one("""SELECT count(*) FROM ae_measures m WHERE diaries_id_inicio IS NOT NULL AND NOT EXISTS
        (SELECT 1 FROM interventions i WHERE i.country = 'LT' AND i.row_n = m.diaries_id_inicio)""")
    rep["start_rows_other_date"] = one("""SELECT count(*) FROM ae_measures m JOIN interventions i
        ON i.country = 'LT' AND i.row_n = m.diaries_id_inicio WHERE i.date <> m.fecha_sesion""")
    rep["defence_rows_missing"] = one("""SELECT count(*) FROM ae_measures m WHERE diaries_id_defensa IS NOT NULL AND NOT EXISTS
        (SELECT 1 FROM interventions i WHERE i.country = 'LT' AND i.row_n = m.diaries_id_defensa)""")
    rep["defence_rows_other_date"] = one("""SELECT count(*) FROM ae_measures m JOIN interventions i
        ON i.country = 'LT' AND i.row_n = m.diaries_id_defensa WHERE i.date <> m.fecha_defensa""")
    rep["defence_rows_other_speaker"] = one("""SELECT count(*) FROM ae_measures m JOIN interventions i
        ON i.country = 'LT' AND i.row_n = m.diaries_id_defensa
        WHERE m.id_dip_defensor IS NOT NULL AND coalesce(i.id_dep, '') <> CAST(m.id_dip_defensor AS VARCHAR)""")
    # degree recomputed from the edge list (distinct co-authors per period) vs the published one
    con.execute("""CREATE OR REPLACE TEMP TABLE _deg AS
        WITH e AS (SELECT legislatura AS period, id_dip1 a, id_dip2 b FROM ae_edges
                   UNION ALL SELECT 'total', id_dip1, id_dip2 FROM ae_edges),
             x AS (SELECT period, a AS id_dip, b AS other FROM e UNION SELECT period, b, a FROM e)
        SELECT period, id_dip, count(DISTINCT other) AS degree FROM x GROUP BY ALL""")
    rep["degree_checked"] = one("SELECT count(*) FROM ae_metrics m JOIN _deg d USING (period, id_dip)")
    rep["degree_differs"] = one("SELECT count(*) FROM ae_metrics m JOIN _deg d USING (period, id_dip) "
                                "WHERE m.degree <> d.degree")
    rep["roles_differ_from_metrics"] = one("SELECT count(*) FROM ae_roles r JOIN ae_metrics m USING (id_dip, period) "
                                           "WHERE r.role <> m.role")
    rep["linked_speech_rows_without_register"] = one("""SELECT count(*) FROM interventions WHERE country = 'LT'
        AND id_dep IS NOT NULL AND reg_party IS NULL""")
    con.execute("CREATE OR REPLACE TABLE ae_checks AS SELECT ? AS report", [json.dumps(rep)])
    return rep


# ── helpers ───────────────────────────────────────────────────────────────────

def _fold(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s or "") if unicodedata.category(c) != "Mn").lower().strip()


def resolve_deputy(who: str | int) -> dict:
    """A deputy by id_dip or by (part of) the name, accent- and case-insensitive."""
    s = str(who).strip()
    if s.isdigit():
        rows = _q("SELECT id_dip, any_value(nombre_completo) AS name FROM ae_deputies WHERE id_dip = ? GROUP BY 1",
                  [int(s)])
    else:
        pat = "%" + _fold(s).replace(" ", "%") + "%"
        rows = _q("""SELECT id_dip, any_value(nombre_completo) AS name FROM ae_deputies
                     WHERE strip_accents(lower(nombre_completo)) LIKE ? OR strip_accents(lower(coalesce(nombre_variantes, ''))) LIKE ?
                     GROUP BY 1 ORDER BY 2""", [pat, pat])
    if not rows:
        raise LookupError(f"No deputy matches {who!r}.")
    if len(rows) > 1:
        raise LookupError(f"{len(rows)} deputies match {who!r}: " + "; ".join(f"{r['id_dip']} {r['name']}" for r in rows[:15])
                          + (" …" if len(rows) > 15 else "") + ". Use the id_dip.")
    return rows[0]


def _lt_legislature(period: str) -> str:
    """Afinidades label → Luz label (they share the starting year)."""
    return {"1931": "1931-1933", "1933": "1933-1935", "1936": "1936-1939"}.get(str(period)[:4], period)


def _measure_filter(legislature=None, topic=None, measure_type=None, date_from=None, date_to=None,
                    measure_ids=None, alias="m") -> tuple[str, list]:
    a = f"{alias}." if alias else ""
    w, p = "", []
    if legislature:
        w += f" AND left({a}legislatura, 4) = left(?, 4)"
        p.append(legislature)
    if topic:
        w += f" AND (lower({a}tema_principal) = lower(?) OR lower(coalesce({a}tema_secundario, '')) = lower(?))"
        p += [topic, topic]
    if measure_type:
        w += f" AND {a}tipo ILIKE ?"
        p.append(measure_type)
    if date_from:
        w += f" AND {a}fecha_sesion >= CAST(? AS DATE)"
        p.append(_d(date_from, True))
    if date_to:
        w += f" AND {a}fecha_sesion <= CAST(? AS DATE)"
        p.append(_d(date_to, False))
    if measure_ids:
        w += f" AND {a}id_medida IN ({', '.join('?' * len(measure_ids))})"
        p += [int(x) for x in measure_ids]
    return w, p


def _d(d: str, start: bool) -> str:
    d = str(d).strip()
    if re.fullmatch(r"\d{4}", d):
        return f"{d}-01-01" if start else f"{d}-12-31"
    return d


def _version_note() -> dict:
    v = _q("SELECT version FROM ae_dataset")
    lt = store.loaded().get("LT", {})
    return {"afinidades_elegidas": {"doi": "10.7910/DVN/CGOCUS", "version": v[0]["version"] if v else None},
            "luz_y_taquigrafos": {"doi": "10.7910/DVN/THQCMI", "version": lt.get("version")}}


def _require() -> None:
    try:
        store.run_query("SELECT 1 FROM ae_measures LIMIT 1")
    except Exception:
        raise store.NoData("Afinidades Elegidas is not loaded. Run download_data (or `luz-mcp download`).")


# ── measures and signatures ───────────────────────────────────────────────────

def search_measures(text=None, topic=None, measure_type=None, legislature=None, date_from=None, date_to=None,
                    signer=None, first_author=None, signer_party=None, signer_family=None, defence=None,
                    limit=20, offset=0) -> dict:
    _require()
    w, p = _measure_filter(legislature, topic, measure_type, date_from, date_to)
    if text:
        from parlaibero_mcp.textutil import search_regex
        w += " AND (regexp_matches(m.texto, ?) OR regexp_matches(m.titulo, ?))"
        rx = search_regex(text)
        p += [rx, rx]
    if signer:
        d = resolve_deputy(signer)
        w += " AND m.id_medida IN (SELECT id_medida FROM ae_signatures WHERE id_dip = ?)"
        p.append(d["id_dip"])
    if first_author:
        d = resolve_deputy(first_author)
        w += " AND m.id_dip_primer_autor = ?"
        p.append(d["id_dip"])
    if signer_party:
        w += " AND m.id_medida IN (SELECT id_medida FROM ae_signatures WHERE partido ILIKE ?)"
        p.append(signer_party)
    if signer_family:
        w += " AND m.id_medida IN (SELECT id_medida FROM ae_signatures WHERE familia_partidos ILIKE ?)"
        p.append(signer_family)
    if defence:
        w += " AND m.defensa = ?"
        p.append(defence)
    total = _q(f"SELECT count(*) AS n FROM ae_measures m WHERE true{w}", p)[0]["n"]
    rows = _q(f"""SELECT m.id_medida, m.legislatura, m.fecha_sesion, m.tipo, m.titulo, m.tema_principal,
                         m.tema_secundario, m.n_firmas, m.n_firmas_ilegibles, m.id_dip_primer_autor, m.primer_autor,
                         m.defensa, m.id_dip_defensor, d.nombre_completo AS defensor
                  FROM ae_measures m LEFT JOIN (SELECT id_dip, any_value(nombre_completo) AS nombre_completo
                                                FROM ae_deputies GROUP BY 1) d ON d.id_dip = m.id_dip_defensor
                  WHERE true{w} ORDER BY m.fecha_sesion, m.id_medida LIMIT {int(limit)} OFFSET {int(offset)}""", p)
    by_topic = _q(f"SELECT tema_principal AS topic, count(*) AS n FROM ae_measures m WHERE true{w} GROUP BY 1 "
                  f"ORDER BY 2 DESC", p)
    by_type = _q(f"SELECT tipo AS type, count(*) AS n FROM ae_measures m WHERE true{w} GROUP BY 1 ORDER BY 2 DESC", p)
    return {"total": total, "returned": len(rows), "offset": offset, "measures": rows,
            "by_topic": by_topic, "by_type": by_type, "datasets": _version_note(),
            "note": "Topic, title and defence were assigned with language models and human review (see the "
                    "Afinidades methodology): a classification, not something printed in the Diario."}


def get_measure(id_medida: int, context: int = 1) -> dict:
    _require()
    m = _q("SELECT * FROM ae_measures WHERE id_medida = ?", [int(id_medida)])
    if not m:
        raise LookupError(f"No measure {id_medida}.")
    m = m[0]
    sigs = _q("""SELECT orden_firma, tipo_fila, nombre_original, id_dip, nombre_completo, partido, familia_partidos,
                        ideologia, truncada, firmas_declaradas
                 FROM ae_signatures WHERE id_medida = ? ORDER BY orden_firma""", [int(id_medida)])
    out = {"measure": m, "signatures": sigs,
           "truncated_list": any(s["truncada"] for s in sigs),
           "datasets": _version_note()}
    from parlaibero_mcp import server as S
    for key, label in (("diaries_id_inicio", "read_in_session"), ("diaries_id_defensa", "defence")):
        if m.get(key):
            out[label] = S.get_intervention(f"LT{int(m[key]):07d}", context)
    if out["truncated_list"]:
        out["note"] = ("The Diario does not print every signature of this measure ('Siguen las firmas hasta N'): "
                       "its signatures, and its edges in the network, are incomplete.")
    return out


# ── the network ───────────────────────────────────────────────────────────────

def _node_attrs(period: str | None) -> dict[int, dict]:
    if period and period != "total":
        rows = _q("""SELECT id_dip, nombre_completo, partido, familia_partidos, ideologia, distrito FROM ae_deputies
                     WHERE left(legislatura, 4) = left(?, 4)""", [period])
    else:  # the latest record of each deputy
        rows = _q("""SELECT id_dip, arg_max(nombre_completo, legislatura) AS nombre_completo,
                            arg_max(partido, legislatura) AS partido, arg_max(familia_partidos, legislatura) AS familia_partidos,
                            arg_max(ideologia, legislatura) AS ideologia, arg_max(distrito, legislatura) AS distrito
                     FROM ae_deputies GROUP BY 1""")
    return {r["id_dip"]: r for r in rows}


def _weighted_edges(legislature=None, topic=None, measure_type=None, date_from=None, date_to=None,
                    measure_ids=None, include_truncated=True) -> list[dict]:
    w, p = _measure_filter(legislature, topic, measure_type, date_from, date_to, measure_ids, alias="m")
    tr = "" if include_truncated else " AND NOT e.truncada"
    return _q(f"""SELECT e.id_dip1 AS a, e.id_dip2 AS b, count(*) AS weight, bool_or(e.truncada) AS any_truncated
                  FROM ae_edges e JOIN ae_measures m USING (id_medida) WHERE true{w}{tr} GROUP BY 1, 2""", p)


def coauthorship_network(legislature=None, topic=None, measure_type=None, date_from=None, date_to=None,
                         measure_ids=None, min_weight=1, include_truncated=True, path=None, overwrite=False) -> dict:
    """The co-signature network of a set of measures: weight = measures signed together."""
    _require()
    edges = [e for e in _weighted_edges(legislature, topic, measure_type, date_from, date_to, measure_ids,
                                        include_truncated) if e["weight"] >= min_weight]
    if not edges:
        raise store.NoData("No co-signatures for these measures.")
    attrs = _node_attrs(legislature)
    nodes = sorted({e["a"] for e in edges} | {e["b"] for e in edges})
    deg, strength = Counter(), Counter()
    for e in edges:
        for x in (e["a"], e["b"]):
            deg[x] += 1
            strength[x] += e["weight"]
    comps = _components(nodes, edges)
    n, m = len(nodes), len(edges)
    fam_pairs = Counter()
    for e in edges:
        fa = (attrs.get(e["a"]) or {}).get("familia_partidos")
        fb = (attrs.get(e["b"]) or {}).get("familia_partidos")
        fam_pairs["within family" if fa and fa == fb else "across families"] += e["weight"]
    top = sorted(nodes, key=lambda x: (-strength[x], x))[:15]
    out = {"nodes": n, "edges": m, "density": round(2 * m / (n * (n - 1)), 4) if n > 1 else None,
           "components": len(comps), "largest_component": max(map(len, comps)),
           "co_signatures_within_vs_across_families": dict(fam_pairs),
           "edges_from_truncated_lists": sum(1 for e in edges if e["any_truncated"]),
           "top_by_strength": [{"id_dip": x, "name": (attrs.get(x) or {}).get("nombre_completo"),
                                "party": (attrs.get(x) or {}).get("partido"), "co_authors": deg[x],
                                "co_signatures": strength[x]} for x in top],
           "filters": {k: v for k, v in dict(legislature=legislature, topic=topic, measure_type=measure_type,
                                             date_from=date_from, date_to=date_to, min_weight=min_weight,
                                             include_truncated=include_truncated).items() if v not in (None, "")},
           "datasets": _version_note(),
           "note": "Undirected, weighted by the number of measures signed together. Some measures do not print "
                   "every signature (truncated lists): their edges are missing, so degree is a lower bound for "
                   "the deputies who signed them."}
    if path:
        out["files"] = _write_network(path, nodes, edges, attrs, deg, strength, overwrite)
    return out


def _components(nodes, edges) -> list[set]:
    parent = {x: x for x in nodes}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for e in edges:
        ra, rb = find(e["a"]), find(e["b"])
        if ra != rb:
            parent[ra] = rb
    groups = defaultdict(set)
    for x in nodes:
        groups[find(x)].add(x)
    return list(groups.values())


def _write_network(path, nodes, edges, attrs, deg, strength, overwrite) -> list[str]:
    from xml.sax.saxutils import escape
    out = Path(path).expanduser()
    if not out.is_absolute():
        out = Path.cwd() / out
    out.parent.mkdir(parents=True, exist_ok=True)
    keys = ("nombre_completo", "partido", "familia_partidos", "ideologia", "distrito")
    if out.suffix.lower() == ".graphml":
        targets = [out]
    elif out.suffix.lower() == ".csv":
        targets = [out.with_name(out.stem + "_nodes.csv"), out.with_name(out.stem + "_edges.csv")]
    else:
        raise ValueError("path must end in .graphml (Gephi, igraph, networkx) or .csv (nodes + edges files)")
    for t in targets:
        if t.exists() and not overwrite:
            raise FileExistsError(f"{t} already exists; pass overwrite=true to replace it")
    if out.suffix.lower() == ".graphml":
        lines = ['<?xml version="1.0" encoding="UTF-8"?>',
                 '<graphml xmlns="http://graphml.graphdrawing.org/xmlns">']
        for k in keys:
            lines.append(f'  <key id="{k}" for="node" attr.name="{k}" attr.type="string"/>')
        lines += ['  <key id="degree" for="node" attr.name="degree" attr.type="int"/>',
                  '  <key id="strength" for="node" attr.name="strength" attr.type="int"/>',
                  '  <key id="weight" for="edge" attr.name="weight" attr.type="int"/>',
                  '  <graph id="G" edgedefault="undirected">']
        for x in nodes:
            a = attrs.get(x) or {}
            data = "".join(f'<data key="{k}">{escape(str(a.get(k) or ""))}</data>' for k in keys)
            lines.append(f'    <node id="{x}">{data}<data key="degree">{deg[x]}</data>'
                         f'<data key="strength">{strength[x]}</data></node>')
        for e in edges:
            lines.append(f'    <edge source="{e["a"]}" target="{e["b"]}"><data key="weight">{e["weight"]}</data></edge>')
        lines += ["  </graph>", "</graphml>"]
        out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    else:
        import csv as _csv
        with open(targets[0], "w", newline="", encoding="utf-8") as fh:
            w = _csv.writer(fh)
            w.writerow(["id_dip", *keys, "degree", "strength"])
            for x in nodes:
                a = attrs.get(x) or {}
                w.writerow([x, *[a.get(k) or "" for k in keys], deg[x], strength[x]])
        with open(targets[1], "w", newline="", encoding="utf-8") as fh:
            w = _csv.writer(fh)
            w.writerow(["source", "target", "weight"])
            for e in edges:
                w.writerow([e["a"], e["b"], e["weight"]])
    return [str(t) for t in targets]


def deputy_neighbors(who, legislature=None, topic=None, top=30) -> dict:
    _require()
    d = resolve_deputy(who)
    edges = _weighted_edges(legislature, topic)
    attrs = _node_attrs(legislature)
    me = attrs.get(d["id_dip"]) or {}
    nb = Counter()
    for e in edges:
        if e["a"] == d["id_dip"]:
            nb[e["b"]] += e["weight"]
        elif e["b"] == d["id_dip"]:
            nb[e["a"]] += e["weight"]
    by_family, by_party = Counter(), Counter()
    for x, w in nb.items():
        a = attrs.get(x) or {}
        by_family[a.get("familia_partidos") or "?"] += w
        by_party[a.get("partido") or "?"] += w
    total = sum(nb.values())
    return {"deputy": {**d, "party": me.get("partido"), "family": me.get("familia_partidos")},
            "legislature": legislature or "all", "co_authors": len(nb), "co_signatures": total,
            "own_party_share": round(by_party.get(me.get("partido"), 0) / total, 3) if total and me else None,
            "own_family_share": round(by_family.get(me.get("familia_partidos"), 0) / total, 3) if total and me else None,
            "by_family": dict(by_family.most_common()), "by_party": dict(by_party.most_common()),
            "neighbors": [{"id_dip": x, "name": (attrs.get(x) or {}).get("nombre_completo"),
                           "party": (attrs.get(x) or {}).get("partido"),
                           "family": (attrs.get(x) or {}).get("familia_partidos"), "co_signatures": w}
                          for x, w in nb.most_common(top)],
            "datasets": _version_note()}


def cross_group_coauthorship(by="family", legislature=None, topic=None) -> dict:
    """Co-signatures between groups: observed against expected if partners were chosen in
    proportion to each group's activity, and the E-I index of each group."""
    _require()
    if by not in GROUP_COLUMNS:
        raise ValueError(f"by must be one of {', '.join(GROUP_COLUMNS)}")
    col = GROUP_COLUMNS[by]
    edges = _weighted_edges(legislature, topic)
    attrs = _node_attrs(legislature)
    pair = Counter()
    act = Counter()
    for e in edges:
        ga = (attrs.get(e["a"]) or {}).get(col) or "?"
        gb = (attrs.get(e["b"]) or {}).get(col) or "?"
        pair[tuple(sorted((ga, gb)))] += e["weight"]
        act[ga] += e["weight"]
        act[gb] += e["weight"]
    W = sum(pair.values())
    rows = []
    for (ga, gb), w in sorted(pair.items(), key=lambda kv: -kv[1]):
        exp = act[ga] * act[gb] / (2 * W) if ga != gb else act[ga] ** 2 / (4 * W)
        rows.append({"group_a": ga, "group_b": gb, "co_signatures": w, "expected": round(exp, 1),
                     "ratio": round(w / exp, 2) if exp else None})
    ei = {}
    for g in act:
        internal = pair.get((g, g), 0)
        external = sum(w for (a, b), w in pair.items() if (a == g) != (b == g))
        ei[g] = round((external - internal) / (external + internal), 3) if external + internal else None
    out = {"by": by, "legislature": legislature or "all", "topic": topic, "pairs": rows,
           "ei_index": dict(sorted(ei.items(), key=lambda kv: (kv[1] is None, kv[1]))),
           "datasets": _version_note(),
           "notes": ["ratio > 1: the two groups co-sign more than their activity predicts. E-I index: −1 = only "
                     "within the group, +1 = only with others.",
                     "Groups are those of the Afinidades register for that legislature ('total' uses each "
                     "deputy's latest record)."]}
    if by in ("party", "family") and not topic:
        kind = "party" if by == "party" else "family"
        period = legislature if legislature else "total"
        out["published_proximity"] = _q("""SELECT a, b, value FROM ae_proximity WHERE kind = ? AND
                                           left(period, 4) = left(?, 4) AND a < b AND value > 0 ORDER BY value DESC
                                           LIMIT 40""", [kind, period])
        out["notes"].append("published_proximity: the proximity index published by Afinidades Elegidas (see its "
                            "methodology), read as it is.")
    return out


# ── metrics and roles (published, not recomputed) ─────────────────────────────

def network_metrics(who=None, period="total", metric=None, party=None, family=None, top=20,
                    ascending=False) -> dict:
    _require()
    cols = [r["column_name"] for r in _q("SELECT column_name FROM (DESCRIBE ae_metrics)")]
    if who is not None:
        d = resolve_deputy(who)
        rows = _q("SELECT * FROM ae_metrics WHERE id_dip = ? ORDER BY period", [d["id_dip"]])
        return {"deputy": d, "metrics": rows, "datasets": _version_note(),
                "note": "Published metrics (Afinidades Elegidas), not recomputed. The thresholds and definitions "
                        "are in its methodology (get_documentation('methodology'))."}
    if not metric:
        return {"metrics_available": [c for c in cols if c not in ("id_dip", "period", "nombre_completo", "partido",
                                                                     "familia_partidos")],
                "periods": list(PERIODS)}
    if metric not in cols:
        raise ValueError(f"Unknown metric {metric!r}. Available: {', '.join(cols)}")
    w, p = " AND period = ?", [period]
    if party:
        w += " AND partido ILIKE ?"
        p.append(party)
    if family:
        w += " AND familia_partidos ILIKE ?"
        p.append(family)
    rows = _q(f"""SELECT id_dip, nombre_completo, partido, familia_partidos, "{metric}" AS value, role FROM ae_metrics
                  WHERE "{metric}" IS NOT NULL{w} ORDER BY value {'ASC' if ascending else 'DESC'}, id_dip
                  LIMIT {int(top)}""", p)
    return {"metric": metric, "period": period, "ranking": rows, "datasets": _version_note()}


def structural_roles(period="total", by="party") -> dict:
    _require()
    col = {"party": "partido", "family": "familia_partidos"}.get(by)
    if col is None:
        raise ValueError("by must be party or family")
    # the group comes from the register: in that legislature, or the latest record for 'total'
    if period == "total":
        grp = f"(SELECT arg_max({col}, legislatura) FROM ae_deputies d WHERE d.id_dip = m.id_dip)"
    else:
        grp = (f"(SELECT any_value({col}) FROM ae_deputies d WHERE d.id_dip = m.id_dip "
               f"AND left(d.legislatura, 4) = left(m.period, 4))")
    rows = _q(f"""SELECT {grp} AS grp, role, count(*) AS n FROM ae_metrics m WHERE period = ?
                  GROUP BY ALL ORDER BY 1, 3 DESC""", [period])
    table = defaultdict(dict)
    for r in rows:
        table[r["grp"] or "?"][r["role"]] = r["n"]
    leaders = _q("""SELECT role, id_dip, nombre_completo, partido FROM ae_metrics WHERE period = ?
                    AND role IN ('Líder de Cámara', 'Articulador') ORDER BY role, influence_score DESC""", [period])
    return {"period": period, "by": by, "roles": list(ROLES), "distribution": dict(table),
            "leaders_and_articulators": leaders, "datasets": _version_note(),
            "note": "Published structural roles (six-role taxonomy of Afinidades Elegidas, from influence and "
                    "transversality thresholds per period), not recomputed."}


# ── speech × network ──────────────────────────────────────────────────────────

def speech_by_network(period: str, split: str = "role", metric: str | None = None, groups: int = 3,
                      library_prefix: str | None = None, exclude_chair: bool = True) -> dict:
    """Group the deputies of a legislature by their network role (or by quantiles of a published
    metric), measure how much each group speaks, and save each group's speeches as a library so
    every text tool can compare them."""
    _require()
    if period == "total":
        raise ValueError("Pick a legislature (1931-1933, 1933-1936, 1936-1939): speech is tied to one.")
    if split == "role":
        rows = _q("SELECT id_dip, role AS grp FROM ae_metrics WHERE period = ?", [period])
    elif split == "metric":
        if not metric:
            raise ValueError("split='metric' needs metric=… (see network_metrics)")
        rows = _q(f"""SELECT id_dip, 'Q' || ntile({int(groups)}) OVER (ORDER BY "{metric}") || ' of {int(groups)} by {metric}'
                      AS grp FROM ae_metrics WHERE period = ? AND "{metric}" IS NOT NULL""", [period])
    else:
        raise ValueError("split must be role or metric")
    lt_leg = _lt_legislature(period)
    # the presiding officer is isolated in the network (the chair signs nothing) but speaks in every
    # sitting to give the floor: left in, that procedural speech decides the group it falls in
    chair = (f" AND NOT (regexp_matches(coalesce(speaker_raw, ''), '{CHAIR_RX}') AND NOT "
             f"regexp_matches(coalesce(speaker_raw, ''), '{NOT_CHAIR_RX}'))") if exclude_chair else ""
    members = defaultdict(list)
    for r in rows:
        members[r["grp"]].append(str(r["id_dip"]))
    speech = {r["id_dep"]: r for r in _q(f"""SELECT id_dep, count(*) AS turns, sum(n_words) AS words,
                                                count(DISTINCT id_session) AS sessions
                                         FROM interventions WHERE country = 'LT' AND dm_speech = 1 AND legislature = ?
                                           AND id_dep IS NOT NULL{chair} GROUP BY 1""", [lt_leg])}
    total_words = sum(r["words"] or 0 for r in speech.values())
    out, libs = [], {}
    prefix = library_prefix or f"Red {period}"
    for g, ids in sorted(members.items()):
        spoke = [speech[i] for i in ids if i in speech]
        words = sum(s["words"] or 0 for s in spoke)
        out.append({"group": g, "deputies": len(ids), "deputies_who_spoke": len(spoke),
                    "turns": sum(s["turns"] for s in spoke), "words": words,
                    "share_of_linked_words": round(words / total_words, 4) if total_words else None,
                    "words_per_deputy": round(words / len(ids)) if ids else None,
                    "median_words_per_speaker": sorted(s["words"] or 0 for s in spoke)[len(spoke) // 2] if spoke else 0})
        if spoke:
            name = f"{prefix} · {g}"
            id_list = ", ".join(f"'{i}'" for i in ids)
            libs[g] = libmod.create_from_query(
                name, f"SELECT id_int FROM interventions WHERE country = 'LT' AND dm_speech = 1 "
                      f"AND legislature = '{lt_leg}' AND id_dep IN ({id_list}){chair}",
                description=f"Speeches in {lt_leg} of the deputies whose network {split} in Afinidades Elegidas "
                            f"({period}) is: {g}.",
                definition={"network_split": split, "metric": metric, "period": period, "group": g,
                            "exclude_chair": exclude_chair},
                replace=True)["library"]
    return {"period": period, "luz_legislature": lt_leg, "split": split, "metric": metric,
            "chair_excluded": exclude_chair, "groups": out,
            "libraries": libs, "datasets": _version_note(),
            "next": "Compare the groups' language with distinctive_words(field='library', a=<library>, b=<library>) "
                    "or read them with kwic(library=…). The groups are published network positions, not "
                    "something the deputies said about themselves.",
            "notes": (["The presiding officer's turns are left out (exclude_chair): the chair signs no measures, so it "
                       "sits among the isolated deputies while speaking in every sitting."] if exclude_chair else
                      ["The presiding officer's turns are included: they inflate the turns of the group the chair "
                       "falls in (usually the isolated deputies)."]) +
                     ["Speakers who were not members of that legislature (ministers without a seat) are in no group."]}


def deputy_profile(who) -> dict:
    _require()
    d = resolve_deputy(who)
    i = str(d["id_dip"])
    reg = _q("SELECT legislatura, partido, partido_historico, familia_partidos, ideologia, distrito FROM ae_deputies "
             "WHERE id_dip = ? ORDER BY legislatura", [d["id_dip"]])
    speech = _q("""SELECT legislature, count(*) AS turns, sum(n_words) AS words, count(DISTINCT id_session) AS sessions,
                          min(date) AS first, max(date) AS last
                   FROM interventions WHERE country = 'LT' AND dm_speech = 1 AND id_dep = ? GROUP BY 1 ORDER BY 1""", [i])
    chamber = {r["legislature"]: r["w"] for r in _q("""SELECT legislature, sum(n_words) AS w FROM interventions
               WHERE country = 'LT' AND dm_speech = 1 AND id_dep IS NOT NULL GROUP BY 1""")}
    for s in speech:
        s["share_of_linked_words"] = round(s["words"] / chamber[s["legislature"]], 4) if chamber.get(s["legislature"]) else None
    measures = _q("""SELECT (SELECT count(DISTINCT id_medida) FROM ae_signatures WHERE id_dip = ?) AS signed,
                            (SELECT count(*) FROM ae_measures WHERE id_dip_primer_autor = ?) AS first_author,
                            (SELECT count(*) FROM ae_measures WHERE id_dip_defensor = ? AND defensa = 'sí') AS defended,
                            (SELECT count(*) FROM ae_measures WHERE id_dip_defensor = ? AND defensa = 'retirada')
                              AS withdrew""", [d["id_dip"]] * 4)[0]
    topics = _q("""SELECT m.tema_principal AS topic, count(DISTINCT m.id_medida) AS n FROM ae_signatures s
                   JOIN ae_measures m USING (id_medida) WHERE s.id_dip = ? GROUP BY 1 ORDER BY 2 DESC""", [d["id_dip"]])
    metrics = _q("""SELECT period, role, degree, strength, influence_score, transversality_score, betweenness_pct,
                           profile_class FROM ae_metrics WHERE id_dip = ? ORDER BY period""", [d["id_dip"]])
    return {"deputy": d, "register": reg, "speech": speech, "measures": measures, "measure_topics": topics,
            "network": metrics, "datasets": _version_note(),
            "next": "deputy_neighbors for co-authors; search_measures(signer=…) for the measures; "
                    "search_text(id_dep=…) or a library to read the speeches."}

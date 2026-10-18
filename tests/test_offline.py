"""luz-mcp on a tiny synthetic Luz y Taquígrafos + Afinidades Elegidas: no network, no downloads.
`uv run --with pytest pytest`. The real data are checked on import (ae_checks) and by the
end-to-end run described in the README."""
import csv
import json

import pytest

from luz_mcp import afinidades as ae, profile  # noqa: F401  (activates the Luz profile)
from parlaibero_mcp import analysis, library, store

LT_HEADER = ["id", "num_session", "order", "date", "speaker", "speech", "rep_id", "rep_name", "district", "party",
             "party_family", "ideology", "nwords", "legislature"]
LT_ROWS = [
    ["1", "1", "0", "1931-07-14", "SUMARIO", "Sumario. Reforma agraria.", "", "", "", "", "", "", "3", "1931-1933"],
    ["2", "1", "1", "1931-07-14", "El Sr. PRESIDENTE:", "Tiene la palabra el Sr. Uno.", "9", "Presi Dente", "Madrid",
     "PSOE", "Socialista", "I", "6", "1931-1933"],
    ["3", "1", "2", "1931-07-14", "El Sr. UNO:", "La reforma agraria es urgente; la reforma agraria ya.", "1", "Ana Uno",
     "Jaén", "PSOE", "Socialista", "I", "9", "1931-1933"],
    ["4", "1", "3", "1931-07-14", "COMENTARIOS", "Proposición de ley sobre la tierra. Firmada por Uno y Dos.", "", "", "",
     "", "", "", "10", "1931-1933"],
    ["5", "2", "1", "1931-07-20", "El Sr. DOS:", "Defiendo la proposición sobre la tierra y la reforma agraria.", "2",
     "Blas Dos", "Cádiz", "PRRS", "Republicanos", "I", "9", "1931-1933"],
    ["6", "2", "2", "1931-07-20", "El Sr. TRES:", "Nos oponemos a la reforma agraria.", "3", "Carla Tres", "León",
     "Agrarios", "Agrarios", "D", "6", "1931-1933"],
    ["7", "1", "1", "1934-01-10", "El Sr. CUATRO:", "Orden público y nada más.", "4", "Dani Cuatro", "Lugo", "CEDA",
     "Conservadores", "D", "5", "1933-1935"],
    ["8", "1", "2", "1934-01-10", "El Sr. MINISTRO:", "Habla un ministro sin escaño.", "8", "Mini Stro", "", "Indep.",
     "", "", "5", "1933-1935"],
]
AE = {
    "2REP_measures_v3.csv": [
        ["id_medida", "legislatura", "num_sesion", "fecha_sesion", "fecha_firma", "diaries_id_inicio", "orden_diaries",
         "tipo", "titulo", "tema_principal", "tema_secundario", "n_firmas", "n_firmas_ilegibles", "id_dip_primer_autor",
         "primer_autor", "primer_autor_original", "defensa", "id_dip_defensor", "defensor_es_primer_autor",
         "diaries_id_defensa", "fecha_defensa", "texto"],
        ["10", "1931-1933", "1", "1931-07-14", "", "4", "3", "proposición de ley", "Proposición de ley: la tierra",
         "agrario", "ninguno", "2", "0", "1", "Ana Uno", "UNO", "sí", "2", "False", "5", "1931-07-20", "Sobre la tierra."],
        ["11", "1933-1936", "1", "1934-01-10", "", "7", "1", "enmienda", "Enmienda: orden", "orden público", "agrario",
         "2", "1", "4", "Dani Cuatro", "CUATRO", "no identificada", "", "", "", "", "Orden."],
    ],
    "2REP_cosponsorship_v3.csv": [
        ["id_firma", "id_medida", "id_v2", "archivo", "num_sesion", "legislatura", "fecha_sesion", "fecha_firma",
         "tipo_medida", "truncada", "firmas_declaradas", "orden_firma", "tipo_fila", "nombre_original", "id_dip",
         "nombre_completo", "distrito", "partido", "partido_historico", "familia_partidos", "ideologia"],
        ["10-1", "10", "1", "x", "1", "1931-1933", "1931-07-14", "", "proposición de ley", "0", "", "1", "firma", "UNO",
         "1", "Ana Uno", "Jaén", "PSOE", "PSOE", "Socialista", "I"],
        ["10-2", "10", "2", "x", "1", "1931-1933", "1931-07-14", "", "proposición de ley", "0", "", "2", "firma", "DOS",
         "2", "Blas Dos", "Cádiz", "PRRS", "PRRS", "Republicanos de izquierda", "I"],
        ["11-1", "11", "3", "x", "1", "1933-1936", "1934-01-10", "", "enmienda", "1", "5", "1", "firma", "CUATRO", "4",
         "Dani Cuatro", "Lugo", "CEDA", "CEDA", "Conservadores", "D"],
        ["11-2", "11", "4", "x", "1", "1933-1936", "1934-01-10", "", "enmienda", "1", "5", "2", "firma", "TRES", "3",
         "Carla Tres", "León", "Agrarios", "Partido Agrario", "Agrario", "D"],
        ["11-3", "11", "5", "x", "1", "1933-1936", "1934-01-10", "", "enmienda", "1", "5", "3", "firma_ilegible", "?",
         "", "", "", "", "", "", ""],
    ],
    "2REP_coauthor_edgelist_v3.csv": [
        ["id_medida", "id_legislature", "id_dip1", "name_dip1", "id_dip2", "name_dip2", "ideo_dip1", "ideo_dip2",
         "truncada"],
        ["10", "1931-1933", "1", "Ana Uno", "2", "Blas Dos", "I", "I", "0"],
        ["11", "1933-1936", "3", "Carla Tres", "4", "Dani Cuatro", "D", "D", "1"],
    ],
    "representative_metadata_v3.csv": [
        ["nombre_completo", "legislatura", "nombre", "apellidos", "distrito", "partido", "familia_partidos", "ideologia",
         "id_dip", "partido_historico", "nombre_completo_original", "nombre_variantes"],
        ["Ana Uno", "1931-1933", "ANA", "UNO", "Jaén", "PSOE", "Socialista", "I", "1", "PSOE", "", ""],
        ["Blas Dos", "1931-1933", "BLAS", "DOS", "Cádiz", "PRRS", "Republicanos de izquierda", "I", "2", "PRRS", "", ""],
        ["Carla Tres", "1931-1933", "CARLA", "TRES", "León", "Agrarios", "Agrario", "D", "3", "Agrarios", "", ""],
        ["Carla Tres", "1933-1936", "CARLA", "TRES", "León", "Agrarios", "Agrario", "D", "3", "Agrarios", "", ""],
        ["Dani Cuatro", "1933-1936", "DANI", "CUATRO", "Lugo", "CEDA", "Conservadores", "D", "4", "CEDA", "", ""],
        ["Presi Dente", "1931-1933", "PRESI", "DENTE", "Madrid", "PSOE", "Socialista", "I", "9", "PSOE", "", ""],
    ],
    "party_dictionary_v3.csv": [["partido", "nombre_completo"], ["PSOE", "Partido Socialista Obrero Español"]],
    "topic_taxonomy_v3.csv": [["tema", "topic_en"], ["agrario", "agrarian"], ["orden público", "public order"]],
}


def _metrics():
    def m(degree, role):
        return {"degree": degree, "strength": degree, "role": role, "influence_score": 0.5, "betweenness_pct": 0.1,
                "transversality_score": 0.3, "profile_class": "x"}
    deps = {}
    for dip, name, per in [(1, "Ana Uno", {"1931-1933": m(1, "Articulador"), "total": m(1, "Articulador")}),
                           (2, "Blas Dos", {"1931-1933": m(1, "Cuadro de partido"), "total": m(1, "Cuadro de partido")}),
                           (3, "Carla Tres", {"1931-1933": m(0, "Diputado aislado"), "1933-1936": m(1, "Articulador"),
                                              "total": m(1, "Articulador")}),
                           (4, "Dani Cuatro", {"1933-1936": m(1, "Líder de Cámara"), "total": m(1, "Líder de Cámara")}),
                           (9, "Presi Dente", {"1931-1933": m(0, "Diputado aislado"), "total": m(0, "Diputado aislado")})]:
        deps[str(dip)] = {"id_dip": dip, "nombre_completo": name, "partido": {}, "familia_partidos": {}, "metrics": per}
    return {"meta": {"generated": "x", "thresholds": {}}, "deputies": deps,
            "party_proximity": {"total": {"PSOE": {"PRRS": 2.0}, "PRRS": {"PSOE": 2.0}}},
            "familia_proximity": {}, "party_weights": {}, "party_stats": {}, "party_communities": {}}


@pytest.fixture()
def home(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "HOME", tmp_path)
    monkeypatch.setattr(store, "DATA", tmp_path / "data")
    monkeypatch.setattr(store, "DB", tmp_path / "luz.duckdb")
    monkeypatch.setattr(store, "LIBDB", tmp_path / "bibliotecas.duckdb")
    monkeypatch.setattr(store, "LOG_DISABLED", True)
    lt, aed = tmp_path / "data" / "LT", tmp_path / "data" / "AE"
    lt.mkdir(parents=True)
    aed.mkdir(parents=True)
    with open(lt / "2REP_Diaries.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, delimiter=";", quoting=csv.QUOTE_ALL)
        w.writerow(LT_HEADER)
        w.writerows(LT_ROWS)
    for name, rows in AE.items():
        with open(aed / name, "w", newline="", encoding="utf-8") as fh:
            csv.writer(fh).writerows(rows)
    (aed / ae.FILES["metrics"]).write_text(json.dumps(_metrics()), encoding="utf-8")
    (aed / ae.FILES["roles"]).write_text(json.dumps({"1": {"total": "Articulador", "1931-1933": "Articulador"}}),
                                         encoding="utf-8")
    (aed / ".version").write_text("2.0")
    (lt / ".source.json").write_text(json.dumps({
        "titulo": "Luz y Taquígrafos: Parliamentary Debates", "autores": [{"nombre": "Rodrigues-Silveira, Rodrigo"}],
        "anio": 2026, "editor": "Harvard Dataverse", "doi": "10.7910/DVN/THQCMI",
        "url": "https://doi.org/10.7910/DVN/THQCMI", "version_cita": "V3", "edition": "3.0",
        "cita": "Rodrigues-Silveira, Rodrigo, 2026, \"Luz y Taquígrafos\", https://doi.org/10.7910/DVN/THQCMI, "
                "Harvard Dataverse, V3"}), encoding="utf-8")
    store.import_country("LT", lt, source="test", version="3.0", title="Luz")
    return tmp_path


def q(sql, params=None):
    return store.run_query(sql, params or [])[1]


def test_mapping_to_the_engine(home):
    rows = q("SELECT id_int, id_session, row_n, intervention_order, dm_speech, speaker_raw, id_dep, party_family, "
             "nwords_published, sex FROM interventions ORDER BY row_n")
    assert rows[0][:6] == ("LT0000001", "LT19310001", 1, 0, 0, "SUMARIO")
    assert rows[3][4] == 0 and rows[3][5] == "COMENTARIOS"          # not speech
    assert rows[2][:2] == ("LT0000003", "LT19310001") and rows[2][6:9] == ("1", "Socialista", 9)
    assert rows[6][1] == "LT19330001"                                 # session numbers restart per legislature
    assert all(r[9] is None for r in rows)                            # no sex variable


def test_register_labels_and_checks(home):
    # Luz says "Republicanos", the register "Republicanos de izquierda"; the minister has no register entry
    assert q("SELECT party_family, reg_family FROM interventions WHERE id_int = 'LT0000005'")[0] == \
        ("Republicanos", "Republicanos de izquierda")
    assert q("SELECT reg_party FROM interventions WHERE id_int = 'LT0000008'")[0][0] is None
    c = json.loads(q("SELECT report FROM ae_checks")[0][0])
    assert (c["measures"], c["signatures"], c["edges"], c["deputies"]) == (2, 5, 2, 5)
    assert c["start_rows_missing"] == c["start_rows_other_date"] == c["defence_rows_other_speaker"] == 0
    assert c["degree_differs"] == 0 and c["linked_speech_rows_without_register"] == 1


def test_wrong_file_is_refused(home, monkeypatch):
    monkeypatch.setattr(store, "csv_id_sequence_digest", lambda p: (8, "other"))
    with pytest.raises(RuntimeError, match="row numbers"):
        store.import_country("LT", home / "data" / "LT", version="3.0")


def test_measures_and_debate(home):
    r = ae.search_measures(topic="agrario")
    assert r["total"] == 2                                            # main or secondary topic
    m = ae.get_measure(10, context=0)
    assert m["read_in_session"]["turns"][0]["speaker_raw"] == "COMENTARIOS"
    assert m["defence"]["turns"][0]["id_dep"] == "2"
    assert ae.get_measure(11)["truncated_list"]
    assert ae.search_measures(signer="dos")["total"] == 1            # by name, accent- and case-insensitive


def test_network(home, tmp_path):
    n = ae.coauthorship_network(path=str(tmp_path / "red.graphml"))
    assert (n["nodes"], n["edges"], n["components"], n["edges_from_truncated_lists"]) == (4, 2, 2, 1)
    assert "<graphml" in open(n["files"][0], encoding="utf-8").read()
    nb = ae.deputy_neighbors("1", legislature="1931-1933")
    assert nb["co_authors"] == 1 and nb["neighbors"][0]["id_dip"] == 2
    cg = ae.cross_group_coauthorship(by="ideology")
    assert cg["ei_index"] == {"I": -1.0, "D": -1.0}
    assert ae.network_metrics(period="total", metric="degree", top=2)["ranking"][0]["value"] == 1
    assert ae.structural_roles(period="1931-1933", by="party")["distribution"]["PSOE"] == {"Articulador": 1,
                                                                                          "Diputado aislado": 1}


def test_speech_by_network_leaves_the_chair_out(home):
    r = ae.speech_by_network("1931-1933")
    groups = {g["group"]: g for g in r["groups"]}
    assert groups["Diputado aislado"]["turns"] == 1                   # Carla; the chair (row 2) is out
    lib = r["libraries"]["Articulador"]
    assert [x[0] for x in q("SELECT l.id_int FROM lib.library_items l JOIN lib.libraries b ON b.id = l.library_id "
                             "WHERE b.name = ?", [lib])] == ["LT0000003"]
    assert ae.speech_by_network("1931-1933", exclude_chair=False)["groups"][2]["turns"] == 2


def test_share_of_voice_uses_the_register(home):
    rows = analysis.share_of_voice(analysis.Filters(), by="reg_family", per="legislature")["rows"]
    soc = next(r for r in rows if r["period"] == "1931-1933" and r["group"] == "Socialista")
    assert soc["members_on_register"] == 2


def test_profile_and_library_export(home, tmp_path):
    p = ae.deputy_profile("Blas")
    assert p["measures"] == {"signed": 1, "first_author": 0, "defended": 1, "withdrew": 0}
    library.create("reforma", ["LT"], terms="reforma agraria")
    r = library.export("reforma", str(tmp_path / "out"))
    b = json.loads(open(r["files"][0], encoding="utf-8").read())
    assert b["corpus"] == "2REP_Diaries" and b["fuente"]["version"] == "V3"
    assert [i["speech_id"] for i in b["items"]] == [3, 5, 6]          # the row numbers of the V3 file
    assert r["files"][0].endswith("reforma.2replib")                 # one dataset: no country suffix


def test_network_tools_on_a_library(home, tmp_path):
    from luz_mcp import server as L
    library.create("palabra", ["LT"], terms="palabra, reforma agraria")
    r = L.mention_network("palabra", "speakers", min_mentions=1, output_dir=str(tmp_path / "red"))
    s = r["networks"]["LT"]
    assert s["honorifics"] is True                                     # Spanish: 'el Sr. Uno' names the deputy
    assert ("9", "1", 1) in [tuple(e) for e in s["edge_list"]]          # the chair gives Ana Uno the floor
    assert any(f.endswith(".html") for f in r["files"])
    c = L.cooccurrence_network("palabra", [{"name": "reforma", "type": "concepto", "pattern": r"reforma agraria"},
                                           {"name": "tierra", "type": "concepto", "pattern": r"\btierra\b"}],
                               min_co=1, min_npmi=-1, formats=[])
    assert c["networks"]["LT"]["N"] == 4
    assert "mention_network" in L.methods_networks()


def test_connectedness_weights_and_paths():
    # Fowler's Fig. 2: Schrock co-signs three of Akin's bills, with 92, 1 and 225 co-signatories
    w, q = ae._fowler_ties([{"sponsor": 1, "signers": [1, 2], "signatures": c + 1} for c in (92, 1, 225)])
    assert round(w[(2, 1)], 3) == 1.015 and q[(2, 1)] == 3 and (1, 2) not in w
    # a strong indirect path (2 → 3 → 1, distance 2) beats a weak direct tie (2 → 1, distance 10)
    s = ae._connectedness_scores([1, 2, 3, 4], {(2, 1): 0.1, (2, 3): 1.0, (3, 1): 1.0})
    assert s[1] == {"reached_by": 2, "sum_distance": 3.0, "sum_inverse": 1.5}
    assert s[2]["reached_by"] == 0                                    # nobody supports 2
    # when everyone reaches j, the reach-corrected score is Fowler's (n − 1)/Σd
    s = ae._connectedness_scores([1, 2, 3], {(2, 1): 1.0, (3, 1): 0.5})[1]
    assert s["reached_by"] ** 2 / (2 * s["sum_distance"]) == pytest.approx(2 / 3)


def test_connectedness_on_the_data(home, tmp_path):
    r = ae.connectedness("1931-1933", who="Ana")
    assert r["summary"]["members"] == 4 and r["summary"]["ties"] == 1   # 2 → 1 (measure 10)
    assert r["ranking"][0]["id_dip"] == 1 and r["ranking"][0]["connectedness"] == pytest.approx(1 / 3)
    assert r["deputy"]["closest_supporters"][0]["id_dip"] == 2 and r["deputy"]["rank"] == 1
    assert "correlation_with_published_metrics" in r
    # measure 11: sponsor 4, co-signed by 3 and one illegible, 'Siguen las firmas hasta 5' → c = 4
    r = ae.connectedness("1933-1936", path=str(tmp_path / "c.csv"))
    assert r["strongest_ties"][0]["weight"] == 0.25 and r["ranking"][0]["connectedness"] == 0.25
    assert r["summary"]["measures_with_truncated_lists_used"] == 1 and len(r["files"]) == 2
    assert ae.connectedness("1933-1936", ties="undirected")["summary"]["deputies_reached"] == 2
    with pytest.raises(ValueError, match="legislature"):
        ae.connectedness("total")
    with pytest.raises(LookupError, match="not a member"):
        ae.connectedness("1931-1933", who="Dani")

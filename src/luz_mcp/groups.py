"""Groups in the co-signature network of Afinidades Elegidas, computed here from the signatures:
Gould-Fernandez brokerage roles, transpartisan co-signing, dyadic homophily, block densities and
Newman's assortativity. One network per legislature; the groups are those of the register for it.

Two networks come from the same measures (and so the same filters):
    undirected   every pair of identified signatories of a measure; weight = measures signed together
                 (the published edge list of Afinidades Elegidas, rebuilt from the signatures)
    directed     each co-signatory → the first signatory of the measure; weight = measures
"""
from __future__ import annotations

import csv
import math
import operator
import random
from collections import Counter, defaultdict
from pathlib import Path

from parlaibero_mcp import store

from . import afinidades as ae

# district → historical region, as Afinidades Elegidas defines it (DISTRITO_REGION in
# scripts/revision/F_metricas.py of its code). Ceuta and Melilla are in no region there: here
# each is its own.
DISTRICT_REGION = {
    "Almería": "Andalucía", "Cádiz": "Andalucía", "Córdoba": "Andalucía", "Granada": "Andalucía",
    "Huelva": "Andalucía", "Jaén": "Andalucía", "Málaga": "Andalucía", "Sevilla": "Andalucía",
    "Huesca": "Aragón", "Teruel": "Aragón", "Zaragoza": "Aragón",
    "Oviedo": "Asturias", "Baleares": "Baleares",
    "Palmas (Las)": "Canarias", "Santa Cruz de Tenerife": "Canarias",
    "Ciudad Real": "Castilla la Nueva", "Cuenca": "Castilla la Nueva", "Guadalajara": "Castilla la Nueva",
    "Madrid": "Castilla la Nueva", "Toledo": "Castilla la Nueva",
    "Ávila": "Castilla la Vieja", "Burgos": "Castilla la Vieja", "Logroño": "Castilla la Vieja",
    "Palencia": "Castilla la Vieja", "Santander": "Castilla la Vieja", "Segovia": "Castilla la Vieja",
    "Soria": "Castilla la Vieja", "Valladolid": "Castilla la Vieja",
    "Barcelona": "Cataluña", "Gerona": "Cataluña", "Lérida": "Cataluña", "Tarragona": "Cataluña",
    "Badajoz": "Extremadura", "Cáceres": "Extremadura",
    "Coruña (La)": "Galicia", "Lugo": "Galicia", "Orense": "Galicia", "Pontevedra": "Galicia",
    "León": "León", "Salamanca": "León", "Zamora": "León",
    "Albacete": "Murcia", "Murcia": "Murcia", "Cartagena": "Murcia",
    "Navarra": "Navarra",
    "Alicante": "Valencia", "Castellón": "Valencia", "Valencia": "Valencia",
    "Álava": "Vascongadas", "Guipúzcoa": "Vascongadas", "Vizcaya": "Vascongadas",
}
# the ordinal ideology scale of Afinidades Elegidas (METHODOLOGY_v3, §7.1)
IDEOLOGY_POSITION = {"EI": 0, "I": 1, "CI": 2, "C": 3, "CD": 4, "D": 5, "ED": 6}
GROUP_KEYS = {"party": "partido", "family": "familia_partidos", "ideology": "ideologia", "district": "distrito",
              "region": "region"}
NO_LABEL = "(no label)"

GOULD = ("Gould, R. V., & Fernandez, R. M. (1989). Structures of Mediation: A Formal Approach to Brokerage in "
         "Transaction Networks. Sociological Methodology 19: 89-126. doi:10.2307/270949")
HARBRIDGE = ("Harbridge, L. (2015). Is Bipartisanship Dead? Policy Agreement and Agenda-Setting in the House of "
             "Representatives. Cambridge University Press. doi:10.1017/CBO9781139942324")
BRATTON = ("Bratton, K. A., & Rouse, S. M. (2011). Networks in the Legislative Arena: How Group Dynamics Affect "
           "Cosponsorship. Legislative Studies Quarterly 36(3): 423-460. doi:10.1111/j.1939-9162.2011.00021.x")
CLARK = ("Clark, J. H., & Caro, V. (2013). Multimember Districts and the Substantive Representation of Women: An "
         "Analysis of Legislative Cosponsorship Networks. Politics & Gender 9(1): 1-30. doi:10.1017/S1743923X12000670")
CRISP = ("Crisp, B. F., Kanthak, K., & Leijonhufvud, J. (2004). The Reputations Legislators Build: With Whom Should "
         "Representatives Collaborate? American Political Science Review 98(4): 703-716. "
         "doi:10.1017/S0003055404041437")
ALEMAN = ("Alemán, E., & Calvo, E. (2013). Explaining Policy Ties in Presidential Congresses: A Network Analysis of "
          "Bill Initiation Data. Political Studies 61(2): 356-377. doi:10.1111/j.1467-9248.2012.00964.x")
LAAKSO = ("Laakso, M., & Taagepera, R. (1979). \"Effective\" Number of Parties: A Measure with Application to West "
          "Europe. Comparative Political Studies 12(1): 3-27. doi:10.1177/001041407901200101")
NEWMAN = ("Newman, M. E. J. (2003). Mixing patterns in networks. Physical Review E 67: 026126. "
          "doi:10.1103/PhysRevE.67.026126")


# ── the network of one legislature ────────────────────────────────────────────

def _network(legislature, topic=None, measure_type=None, date_from=None, date_to=None, measure_ids=None,
             include_truncated=True, min_weight=1) -> dict:
    """Members of the legislature (with region and ideology position), the measures, and the
    undirected and directed co-signature networks built from the same measures."""
    ae._require()
    if not legislature or legislature == "total":
        raise ValueError("Pick a legislature (1931-1933, 1933-1936, 1936-1939): membership and party labels change "
                         "from one to the next.")
    measures = ae._measure_signers(legislature, topic, measure_type, date_from, date_to, measure_ids,
                                   include_truncated)
    attrs = ae._node_attrs(legislature)
    und, sup = Counter(), Counter()
    for m in measures:
        s = list(dict.fromkeys(m["signers"] or []))
        for x in range(len(s)):
            for y in range(x + 1, len(s)):
                und[(min(s[x], s[y]), max(s[x], s[y]))] += 1
        for i in s:
            if i != m["sponsor"]:
                sup[(i, m["sponsor"])] += 1
    und = {p: w for p, w in und.items() if w >= min_weight}
    sup = {p: w for p, w in sup.items() if w >= min_weight}
    for x in {x for p in list(und) + list(sup) for x in p} - set(attrs):
        attrs[x] = {"id_dip": x}
    for a in attrs.values():
        d = a.get("distrito")
        a["region"] = DISTRICT_REGION.get(d, d)
        a["ideo_pos"] = IDEOLOGY_POSITION.get(a.get("ideologia"))
    return {"legislature": legislature, "members": sorted(attrs), "attrs": attrs, "measures": measures,
            "undirected": und, "directed": sup,
            "filters": {k: v for k, v in dict(topic=topic, measure_type=measure_type, date_from=date_from,
                                              date_to=date_to, measure_ids=measure_ids,
                                              include_truncated=include_truncated, min_weight=min_weight).items()
                        if v not in (None, "")}}


def _label(net, x, by) -> str:
    return (net["attrs"].get(x) or {}).get(GROUP_KEYS[by]) or NO_LABEL


def _who(net, x) -> dict:
    a = net["attrs"].get(x) or {}
    return {"id_dip": x, "name": a.get("nombre_completo"), "party": a.get("partido"),
            "family": a.get("familia_partidos")}


def _check_by(by) -> None:
    if by not in GROUP_KEYS:
        raise ValueError(f"by must be one of {', '.join(GROUP_KEYS)}")


def _out_path(path, suffixes, overwrite) -> list[Path]:
    out = Path(path).expanduser()
    if not out.is_absolute():
        out = Path.cwd() / out
    if out.suffix.lower() != ".csv":
        raise ValueError("path must end in .csv")
    targets = [out] if not suffixes else [out.with_name(f"{out.stem}_{s}.csv") for s in suffixes]
    for t in targets:
        if t.exists() and not overwrite:
            raise FileExistsError(f"{t} already exists; pass overwrite=true to replace it")
    out.parent.mkdir(parents=True, exist_ok=True)
    return targets


def _write_rows(target: Path, rows: list[dict]) -> str:
    with open(target, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]) if rows else ["empty"])
        w.writeheader()
        w.writerows(rows)
    return str(target)


def _r(x, digits=4):
    return None if x is None else round(x, digits)


def _common(net, cites) -> dict:
    return {"filters": net["filters"], "datasets": ae._version_note(), "cite": cites}


# ── Gould-Fernandez brokerage roles ───────────────────────────────────────────

ROLES = ("coordinator", "consultant", "representative", "gatekeeper", "liaison")


def _gf_expectations(sizes: Counter, g, N: int, D: float) -> dict:
    """Expected value and variance of each raw brokerage score of an actor of group g, under Gould
    and Fernandez's null of a random network with density D (their Table 1)."""
    p, c3 = D * D * (1 - D), (D * (1 - D)) ** 3
    nj = sizes[g]
    others = [n for h, n in sizes.items() if h != g]
    c2 = lambda k: k * (k - 1) / 2  # noqa: E731
    e = {"coordinator": p * (nj - 1) * (nj - 2),
         "consultant": p * sum(n * (n - 1) for n in others),
         "representative": p * (N - nj) * (nj - 1),
         "gatekeeper": p * (N - nj) * (nj - 1),
         "liaison": p * sum(n * (N - nj - n) for n in others),
         "total": p * (N - 1) * (N - 2)}
    extra = {"coordinator": 2 * (nj - 1) * (nj - 2) * (nj - 3),
             "consultant": 2 * sum(n * (n - 1) * (n - 2) for n in others),
             "representative": 2 * ((nj - 1) * c2(N - nj) + (N - nj) * c2(nj - 1)),
             "gatekeeper": 2 * ((nj - 1) * c2(N - nj) + (N - nj) * c2(nj - 1)),
             "liaison": 4 * sum(n * c2(N - n - nj) for n in others),
             "total": 2 * (N - 1) * (N - 2) * (N - 3)}
    return {r: (e[r], e[r] * (1 - p) + extra[r] * c3) for r in e}


def _gf_counts(net, by) -> dict:
    """Open two-paths a → b → c (no tie a → c) through each broker b, by the groups of a, b and c."""
    out_nb, in_nb = defaultdict(set), defaultdict(set)
    for i, j in net["directed"]:
        out_nb[i].add(j)
        in_nb[j].add(i)
    counts = {}
    for b in net["members"]:
        if not in_nb[b] or not out_nb[b]:
            continue
        gb = _label(net, b, by)
        by_group = defaultdict(set)
        for c in out_nb[b]:
            by_group[_label(net, c, by)].add(c)
        n = Counter()
        for a in in_nb[b]:
            ga, reach = _label(net, a, by), out_nb[a]
            for h, cs in by_group.items():
                k = len(cs) - len(cs & reach) - (a in cs)
                if not k:
                    continue
                if ga == gb == h:
                    n["coordinator"] += k
                elif ga == h:
                    n["consultant"] += k
                elif ga == gb:
                    n["representative"] += k
                elif h == gb:
                    n["gatekeeper"] += k
                else:
                    n["liaison"] += k
        if n:
            counts[b] = n
    return counts


def brokerage_roles(legislature, by="party", who=None, top=10, topic=None, measure_type=None, date_from=None,
                    date_to=None, measure_ids=None, include_truncated=True, min_weight=1, path=None,
                    overwrite=False) -> dict:
    """Gould and Fernandez's (1989) five brokerage roles on the directed support network
    (co-signatory → first signatory): for each deputy, how many open two-paths a → b → c they sit
    on, by the groups of a, b and c, against the expectation of a random network."""
    _check_by(by)
    net = _network(legislature, topic, measure_type, date_from, date_to, measure_ids, include_truncated, min_weight)
    N, arcs = len(net["members"]), len(net["directed"])
    if not arcs:
        raise store.NoData("No co-signatures for these measures.")
    D = arcs / (N * (N - 1))
    sizes = Counter(_label(net, x, by) for x in net["members"])
    counts = _gf_counts(net, by)
    rows, global_obs, global_exp = {}, Counter(), Counter()
    for x in net["members"]:
        g = _label(net, x, by)
        ev = _gf_expectations(sizes, g, N, D)
        n = counts.get(x, Counter())
        total = sum(n.values())
        row = {**_who(net, x), "group": g, "group_size": sizes[g], "total": total}
        for r in ROLES:
            e, v = ev[r]
            row[r] = n[r]
            row[f"{r}_expected"] = _r(e, 3)
            row[f"{r}_z"] = _r((n[r] - e) / math.sqrt(v), 2) if v > 0 else None
            row[f"{r}_share"] = _r(n[r] / total, 3) if total else None
            row[f"{r}_expected_share"] = _r(e / ev["total"][0], 3)
            global_obs[r] += n[r]
            global_exp[r] += e
        e, v = ev["total"]
        row["total_expected"], row["total_z"] = _r(e, 3), _r((total - e) / math.sqrt(v), 2)
        rows[x] = row
    brokers = [r for r in rows.values() if r["total"]]
    top_by_role = {r: [{k: x[k] for k in ("id_dip", "name", "party", "group", r, f"{r}_expected", f"{r}_z",
                                          f"{r}_share")}
                       for x in sorted((x for x in brokers if x[r]),
                                       key=lambda x: (-(x[f"{r}_z"] or 0), -x[r], x["id_dip"]))[:top]]
                   for r in ROLES}
    by_group = defaultdict(Counter)
    for x in brokers:
        for r in ROLES:
            by_group[x["group"]][r] += x[r]
    out = {"legislature": legislature, "by": by,
           "summary": {"members": N, "arcs": arcs, "density": _r(D, 5), "brokers": len(brokers),
                       "groups": len(sizes), "small_groups": sorted(g for g, n in sizes.items() if n < 3)},
           "global": {r: {"observed": global_obs[r], "expected": _r(global_exp[r], 1),
                          "ratio": _r(global_obs[r] / global_exp[r], 3) if global_exp[r] else None} for r in ROLES},
           "by_group": {g: {**dict(c), "members": sizes[g]} for g, c in sorted(by_group.items(),
                                                                                key=lambda kv: -sizes[kv[0]])},
           "top_by_role": top_by_role}
    if who is not None:
        d = ae.resolve_deputy(who)
        if d["id_dip"] not in rows:
            raise LookupError(f"{d['name']} ({d['id_dip']}) was not a member of the {legislature} legislature.")
        out["deputy"] = rows[d["id_dip"]]
    if path:
        out["files"] = [_write_rows(_out_path(path, None, overwrite)[0], list(rows.values()))]
    out["method"] = [
        "Directed support network: a → b when a co-signed a measure whose first signatory is b. A brokerage relation "
        "is an open two-path a → b → c (a ≠ c, no tie a → c); b brokers it.",
        "Roles by the groups of a, b and c: coordinator (all three in one group), consultant or itinerant broker "
        "(a and c in one group, b in another), representative (a and b in one group, c in another), gatekeeper "
        "(b and c in one group, a in another), liaison (three different groups).",
        "Expected values and variances are Gould and Fernandez's (1989, Table 1): a random network of the same size "
        "and density, every tie independent. As they intend, z does not discount how many ties a deputy has. "
        "'<role>_share' against '<role>_expected_share' does: the role's share of the deputy's brokerage against "
        "its share if group labels were assigned at random.",
    ]
    out["notes"] = [
        "Computed here from the signatures. These are not the six structural roles published by Afinidades "
        "Elegidas (structural_roles), nor Guimerà-Amaral roles.",
        "The variances assume independent ties; co-signature is often reciprocated, so z overstates significance "
        "(Gould and Fernandez note the variance doubles in a fully symmetric network). Read z as a ranking.",
        "Only deputies who both receive support (first signatories) and give it can broker.",
        "Groups with one or two members (small_groups) cannot coordinate and inflate liaison counts; the family or "
        "ideology grouping is steadier.",
    ]
    out.update(_common(net, [GOULD]))
    return out


# ── transpartisan co-signing ──────────────────────────────────────────────────

COALITIONS = ("uni", "bi", "multi")
NEP_CUTS = (1.5, 2.5)  # NEP rounded to the nearest whole number of groups


def _nep(counts: Counter) -> float:
    """Laakso and Taagepera's effective number of groups among the signatories of a measure."""
    tot = sum(counts.values())
    return 1 / sum((v / tot) ** 2 for v in counts.values())


def _coalition(nep: float) -> str:
    return COALITIONS[0] if nep < NEP_CUTS[0] else COALITIONS[1] if nep < NEP_CUTS[1] else COALITIONS[2]


def _coalition_shares(tally: Counter, n: int) -> dict:
    return {k: _r(tally[k] / n, 3) if n else None for k in COALITIONS}


def transpartisan_cosigning(legislature=None, by="party", who=None, top=20, min_measures=5, topic=None,
                            measure_type=None, date_from=None, date_to=None, include_truncated=True, path=None,
                            overwrite=False) -> dict:
    """Co-signing across parties (or families, ideologies, regions) in a chamber of many parties:
    each measure's coalition is uni-, bi- or multipartisan by the effective number of groups among
    its signatories, and the share of co-signature dyads that cross groups (the dyadic indicator of
    Harbridge 2015) is aggregated to the deputy and to the chamber."""
    _check_by(by)
    legs = [legislature] if legislature else ["1931-1933", "1933-1936", "1936-1939"]
    chamber, deputies, by_type, by_topic = [], {}, defaultdict(Counter), defaultdict(Counter)
    for leg in legs:
        net = _network(leg, topic, measure_type, date_from, date_to, None, include_truncated)
        info = {r["id_medida"]: r for r in ae._q(
            "SELECT id_medida, tipo, tema_principal FROM ae_measures WHERE left(legislatura, 4) = left(?, 4)", [leg])}
        c, kinds = Counter(), Counter()
        span_sum = out_sum = nep_sum = 0.0
        dep = defaultdict(Counter)
        sizes, N = Counter(_label(net, x, by) for x in net["members"]), len(net["members"])
        for m in net["measures"]:
            s = [i for i in dict.fromkeys(m["signers"] or []) if _label(net, i, by) != NO_LABEL]
            g0 = _label(net, m["sponsor"], by)
            co = [i for i in s if i != m["sponsor"]]
            c["measures"] += 1
            c["unlabelled_signatures"] += m["signatures"] - len(s)
            if not co or g0 == NO_LABEL:
                continue
            c["with_co_signatories"] += 1
            nep = _nep(Counter(_label(net, i, by) for i in s))
            kind = _coalition(nep)
            kinds[kind] += 1
            nep_sum += nep
            cross = sum(_label(net, i, by) != g0 for i in co)
            out_sum += cross / len(co)
            pos = [p for p in ((net["attrs"].get(i) or {}).get("ideo_pos") for i in s) if p is not None]
            span_sum += max(pos) - min(pos) if pos else 0
            meta = info.get(m["id_medida"], {})
            for key, tally in ((meta.get("tipo"), by_type), (meta.get("tema_principal"), by_topic)):
                tally[key]["measures"] += 1
                tally[key][kind] += 1
                tally[key]["nep_x1000"] += round(nep * 1000)
            # directed dyads: each co-signature of the first signatory's measure
            c["directed_dyads"] += len(co)
            c["directed_cross"] += cross
            dep[m["sponsor"]]["first_signed"] += 1
            dep[m["sponsor"]]["first_signed_nep"] += nep
            dep[m["sponsor"]]["support_received"] += len(co)
            dep[m["sponsor"]]["support_received_cross"] += cross
            for i in s:
                dep[i][f"signed_{kind}"] += 1
                dep[i]["signed_nep"] += nep
            for i in co:
                dep[i]["co_signed"] += 1
                dep[i]["support_given"] += 1
                dep[i]["support_given_cross"] += _label(net, i, by) != g0
            # all pairs of signatories
            for x in range(len(s)):
                for y in range(x + 1, len(s)):
                    diff = _label(net, s[x], by) != _label(net, s[y], by)
                    c["pair_dyads"] += 1
                    c["pair_cross"] += diff
                    for z in (s[x], s[y]):
                        dep[z]["pairs"] += 1
                        dep[z]["pairs_cross"] += diff
        n = c["with_co_signatories"]
        chamber.append({"legislature": leg, "measures": c["measures"], "with_co_signatories": n,
                        "coalitions": _coalition_shares(kinds, n),
                        "mean_nep": _r(nep_sum / n, 2) if n else None,
                        "mean_share_from_other_groups": _r(out_sum / n, 3) if n else None,
                        "mean_ideological_span": _r(span_sum / n, 2) if n else None,
                        "directed_dyads": c["directed_dyads"],
                        "directed_cross_share": _r(c["directed_cross"] / c["directed_dyads"], 3)
                        if c["directed_dyads"] else None,
                        "pair_dyads": c["pair_dyads"],
                        "pair_cross_share": _r(c["pair_cross"] / c["pair_dyads"], 3) if c["pair_dyads"] else None,
                        "unlabelled_signatures": c["unlabelled_signatures"]})
        if legislature:
            for x, v in dep.items():
                g = _label(net, x, by)
                base = (N - sizes[g]) / (N - 1)
                share = v["pairs_cross"] / v["pairs"] if v["pairs"] else None
                signed = sum(v[f"signed_{k}"] for k in COALITIONS)
                deputies[x] = {**_who(net, x), "group": g, "group_size": sizes[g],
                               "measures_signed": signed,
                               **{f"signed_{k}": v[f"signed_{k}"] for k in COALITIONS},
                               "mean_nep_signed": _r(v["signed_nep"] / signed, 2) if signed else None,
                               "pair_cross_share": _r(share, 3),
                               "baseline_cross_share": _r(base, 3),
                               "cross_excess": _r(share - base, 3) if share is not None else None,
                               "support_given": v["support_given"],
                               "support_given_cross_share": _r(v["support_given_cross"] / v["support_given"], 3)
                               if v["support_given"] else None,
                               "first_signed": v["first_signed"],
                               "mean_nep_first_signed": _r(v["first_signed_nep"] / v["first_signed"], 2)
                               if v["first_signed"] else None,
                               "support_received_cross_share": _r(v["support_received_cross"] / v["support_received"], 3)
                               if v["support_received"] else None}

    def breakdown(tally, key):
        return [{key: k, "measures": v["measures"], "coalitions": _coalition_shares(v, v["measures"]),
                 "mean_nep": _r(v["nep_x1000"] / 1000 / v["measures"], 2)}
                for k, v in sorted(tally.items(), key=lambda kv: -kv[1]["measures"])]
    out = {"by": by, "nep_cuts": {"uni": f"< {NEP_CUTS[0]}", "bi": f"{NEP_CUTS[0]} to < {NEP_CUTS[1]}",
                                  "multi": f">= {NEP_CUTS[1]}"},
           "chamber": chamber, "by_type": breakdown(by_type, "type"), "by_topic": breakdown(by_topic, "topic")}
    if legislature:
        active = [d for d in deputies.values() if d["measures_signed"] >= min_measures
                  and d["cross_excess"] is not None and d["group_size"] >= MIN_GROUP]
        out["most_transpartisan"] = sorted(active, key=lambda d: (-d["cross_excess"], d["id_dip"]))[:top]
        out["least_transpartisan"] = sorted(active, key=lambda d: (d["cross_excess"], d["id_dip"]))[:top]
        groups = defaultdict(list)
        for d in deputies.values():
            if d["pair_cross_share"] is not None:
                groups[d["group"]].append(d)
        out["by_group"] = {g: {"deputies": len(v),
                               "mean_pair_cross_share": _r(sum(d["pair_cross_share"] for d in v) / len(v), 3),
                               "mean_nep_signed": _r(sum(d["mean_nep_signed"] for d in v) / len(v), 2)}
                           for g, v in sorted(groups.items(), key=lambda kv: -len(kv[1]))}
        if who is not None:
            d = ae.resolve_deputy(who)
            out["deputy"] = deputies.get(d["id_dip"]) or {**d, "note": "signed no measure with others here"}
        if path:
            out["files"] = [_write_rows(_out_path(path, None, overwrite)[0], list(deputies.values()))]
    elif who is not None or path:
        raise ValueError("who and path need a legislature: the deputy-level indicators are computed within one.")
    out["method"] = [
        "Measure: NEP = 1/Σ p_g², the effective number of groups among its identified signatories (Laakso and "
        "Taagepera 1979), p_g the share of them in group g. Its coalition is uni below 1.5, bi from 1.5 to below 2.5, "
        "multi from 2.5: NEP rounded to the nearest whole number of groups. One signatory from another group does not "
        "make a measure bi (6 + 1 signatories give NEP 1.32); two groups of equal weight give 2.",
        "Dyadic, aggregated: every co-signature is a dyad co-signatory → first signatory (directed), and every pair of "
        "signatories of a measure is an undirected dyad. A dyad crosses when its two deputies are in different groups "
        "of the register for that legislature. Chamber: directed_cross_share and pair_cross_share. Deputy: "
        "pair_cross_share (with by='party' it equals 1 − party_frac_partido published by Afinidades), "
        "support_given_cross_share (as co-signatory), support_received_cross_share (as first signatory).",
        "mean_share_from_other_groups: the share of a measure's co-signatories from groups other than the first "
        "signatory's, averaged. mean_ideological_span: the range of positions (EI = 0 … ED = 6) among its signatories.",
    ]
    out["notes"] = [
        "Computed here from the signatures.",
        "Harbridge (2015) studies a two-party chamber, where co-signing is either within the party or bipartisan. With "
        "many parties the question is how many groups a measure brings together; the NEP cut-off above is this "
        "project's, not hers. With by='family' (or ideology, region) NEP counts families (ideologies, regions).",
        "Illegible signatures and the unprinted ones of truncated lists have no label: they are left out of NEP and of "
        "every share, and counted in unlabelled_signatures.",
        "Measures with a single signature have no coalition and no dyad and are left out.",
        f"A deputy of a small group crosses almost by force: the rankings order deputies by cross_excess, their "
        f"pair_cross_share minus baseline_cross_share (the share of the other members outside their group, what "
        f"choosing partners at random would give), and leave out groups of fewer than {MIN_GROUP} members.",
    ]
    out["datasets"] = ae._version_note()
    out["cite"] = [HARBRIDGE, LAAKSO]
    return out


# ── dyadic homophily ──────────────────────────────────────────────────────────

ATTRIBUTES = ("party", "family", "ideology", "district", "region")
MIN_GROUP = 3  # smaller groups are left out of the deputy rankings of transpartisan_cosigning


def _solve(a: list[list[float]], b: list[float]) -> list[float] | None:
    """Gauss-Jordan with partial pivoting; None if the matrix is singular."""
    n = len(b)
    m = [row[:] + [b[i]] for i, row in enumerate(a)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(m[r][c]))
        if abs(m[p][c]) < 1e-12:
            return None
        m[c], m[p] = m[p], m[c]
        piv = m[c][c]
        m[c] = [v / piv for v in m[c]]
        for r in range(n):
            if r != c and m[r][c]:
                f = m[r][c]
                m[r] = [v - f * w for v, w in zip(m[r], m[c])]
    return [m[i][n] for i in range(n)]


def _logit(cells: list[tuple[list[float], int, int]], names: list[str]) -> dict:
    """Binomial logit by IRLS on aggregated cells (covariates, dyads, ties)."""
    k = len(names)
    beta = [0.0] * k
    info = None
    for _ in range(50):
        xtwx = [[0.0] * k for _ in range(k)]
        score = [0.0] * k
        for x, n, y in cells:
            eta = sum(b * v for b, v in zip(beta, x))
            mu = 1 / (1 + math.exp(-max(min(eta, 30), -30)))
            w = n * mu * (1 - mu)
            for r in range(k):
                score[r] += x[r] * (y - n * mu)
                for c in range(k):
                    xtwx[r][c] += x[r] * w * x[c]
        step = _solve(xtwx, score)
        if step is None:
            return {"error": "singular information matrix (a covariate has no variation, or two are collinear)"}
        beta = [b + s for b, s in zip(beta, step)]
        info = xtwx
        if max(abs(s) for s in step) < 1e-8:
            break
    cov = [_solve(info, [1.0 if r == c else 0.0 for r in range(k)]) for c in range(k)]
    rows = []
    for i, name in enumerate(names):
        se = math.sqrt(cov[i][i]) if cov[i] and cov[i][i] > 0 else None
        rows.append({"term": name, "coef": _r(beta[i]), "se_naive": _r(se), "odds_ratio": _r(math.exp(beta[i]), 3)
                     if abs(beta[i]) < 30 else None, "separation": abs(beta[i]) > 15})
    return {"terms": rows}


def homophily(legislature, ties="undirected", min_weight=1, permutations=200, seed=1, topic=None,
              measure_type=None, date_from=None, date_to=None, measure_ids=None, include_truncated=True, path=None,
              overwrite=False) -> dict:
    """Dyadic homophily: the probability of a co-signature tie between two deputies given that they
    share party, family, ideology, district or region, with QAP permutation tests, and a dyadic
    logit of the tie on all of them at once, controlling for how active both deputies are. Only
    deputies who signed at least one of the measures can be tied, so only they enter."""
    if ties not in ("directed", "undirected"):
        raise ValueError("ties must be directed or undirected")
    net = _network(legislature, topic, measure_type, date_from, date_to, measure_ids, include_truncated, min_weight)
    directed = ties == "directed"
    tie_w = net["directed"] if directed else net["undirected"]
    if not tie_w:
        raise store.NoData("No co-signatures for these measures.")
    activity = Counter()
    for m in net["measures"]:
        for i in set(m["signers"] or []):
            activity[i] += 1
    # a deputy who signed none of the measures cannot be tied: their dyads are structural zeros, which
    # add nothing but certain non-ties and, when there are many (1936-1939), separate the logit
    members = [x for x in net["members"] if activity[x]]
    idx = {x: k for k, x in enumerate(members)}
    N = len(members)
    labels = {a: [(net["attrs"][x].get(GROUP_KEYS[a]) or None) for x in members] for a in ATTRIBUTES}
    pos = [net["attrs"][x].get("ideo_pos") for x in members]
    A = [idx[i] for i, _ in tie_w]
    B = [idx[j] for _, j in tie_w]
    dyads = N * (N - 1) if directed else N * (N - 1) // 2
    # univariate: same vs different, QAP p-value by permuting which deputy carries which attributes
    rng = random.Random(seed)
    perms = []
    for _ in range(permutations):
        p = list(range(N))
        rng.shuffle(p)
        perms.append(p)
    uni = {}
    for a in ATTRIBUTES:
        lab = labels[a]
        groups = Counter(v for v in lab if v is not None)
        same_dyads = sum(n * (n - 1) for n in groups.values()) // (1 if directed else 2)
        known = sum(groups.values())
        known_dyads = known * (known - 1) // (1 if directed else 2)
        diff_dyads = known_dyads - same_dyads
        same_ties = sum(1 for i, j in zip(A, B) if lab[i] is not None and lab[i] == lab[j])
        known_ties = sum(1 for i, j in zip(A, B) if lab[i] is not None and lab[j] is not None)
        diff_ties = known_ties - same_ties
        hits, gaps = 0, None in lab
        for p in perms:
            pl = [lab[k] for k in p]
            s = sum(map(operator.eq, map(pl.__getitem__, A), map(pl.__getitem__, B)))
            if gaps:  # two deputies without the attribute are not 'the same'
                s -= sum(1 for i, j in zip(A, B) if pl[i] is None and pl[j] is None)
            hits += s >= same_ties
        p_same = same_ties / same_dyads if same_dyads else None
        p_diff = diff_ties / diff_dyads if diff_dyads else None
        odds = (p_same / (1 - p_same)) / (p_diff / (1 - p_diff)) if p_same and p_diff and p_same < 1 and p_diff < 1 \
            else None
        uni[a] = {"groups": len(groups), "same_dyads": same_dyads, "same_ties": same_ties, "p_tie_same": _r(p_same, 4),
                  "different_dyads": diff_dyads, "different_ties": diff_ties, "p_tie_different": _r(p_diff, 4),
                  "relative_risk": _r(p_same / p_diff, 3) if p_same is not None and p_diff else None,
                  "odds_ratio": _r(odds, 3),
                  "qap_p": _r((hits + 1) / (permutations + 1), 4) if permutations else None}
    # multivariate: cells of (same party, family, district, region, ideology distance, activity classes)
    vals = sorted(activity[x] for x in members)
    q1, q2 = vals[N // 3], vals[2 * N // 3]  # cut by value: equal activity, same tercile
    tercile = {x: 0 if activity[x] <= q1 else 1 if activity[x] <= q2 else 2 for x in members}
    names_t = ("low", "mid", "high")
    cells = Counter()
    tie_set = set(tie_w)
    rows_out = []
    for u in range(N):
        for v in range(N) if directed else range(u + 1, N):
            if u == v:
                continue
            x, y = members[u], members[v]
            same = tuple(int(labels[a][u] is not None and labels[a][u] == labels[a][v])
                         for a in ("party", "family", "district", "region"))
            dist = abs(pos[u] - pos[v]) if pos[u] is not None and pos[v] is not None else None
            cls = (tercile[x], tercile[y]) if directed else tuple(sorted((tercile[x], tercile[y])))
            tied = int(((x, y) if directed else (min(x, y), max(x, y))) in tie_set)
            if dist is not None:
                cells[(same, dist, cls, tied)] += 1
            if path:
                rows_out.append({"i": x, "j": y, "tie": tied, "weight": tie_w.get((x, y) if directed else
                                                                                   (min(x, y), max(x, y)), 0),
                                 "same_party": same[0], "same_family": same[1],
                                 "same_ideology": int(dist == 0), "same_district": same[2], "same_region": same[3],
                                 "ideology_distance": "" if dist is None else dist,
                                 "activity_i": activity[x], "activity_j": activity[y]})
    agg = defaultdict(lambda: [0, 0])
    for (same, dist, cls, tied), n in cells.items():
        agg[(same, dist, cls)][0] += n
        agg[(same, dist, cls)][1] += n * tied
    classes = sorted({cls for (_, _, cls) in agg})  # only the activity pairs that occur
    cls_names = [f"activity {names_t[a]}-{names_t[b]}" for a, b in classes[1:]]
    names = ["intercept", "same_party", "same_family", "same_district", "same_region", "ideology_distance"] + cls_names
    data = [([1.0, *map(float, same), float(dist)] + [float(cls == c) for c in classes[1:]], n, y)
            for (same, dist, cls), (n, y) in agg.items()]
    out = {"legislature": legislature, "ties": ties,
           "summary": {"members": len(net["members"]), "deputies_who_signed": N, "dyads": dyads, "ties": len(tie_w),
                       "density": _r(len(tie_w) / dyads, 5), "permutations": permutations},
           "univariate": uni, "qap_p_floor": _r(1 / (permutations + 1), 4) if permutations else None,
           "logit": {**_logit(data, names),
                     "reference_activity": f"activity {names_t[classes[0][0]]}-{names_t[classes[0][1]]}",
                     "activity_cuts": {"low": f"≤ {q1} measures", "mid": f"≤ {q2}", "high": f"> {q2}"}}}
    if path:
        out["files"] = [_write_rows(_out_path(path, None, overwrite)[0], rows_out)]
    out["method"] = [
        ("Directed dyads (co-signatory → first signatory)" if directed else "Undirected dyads") + " among the members "
        "of the legislature who signed at least one of the measures (deputies_who_signed): one who signed none cannot "
        "be tied, and their dyads would only add certain non-ties. A tie is at least min_weight measures signed "
        "together.",
        "univariate: P(tie | same group) and P(tie | different groups), their ratio and odds ratio. qap_p: the share "
        "of random reassignments of the deputies' attributes (the network kept as it is, so each deputy's activity "
        "too) with at least as many same-group ties as observed, (hits + 1)/(permutations + 1). A qap_p equal to "
        "qap_p_floor means no permutation reached the observed count: p is at most that.",
        "logit: the tie on same party, same family, same district, same region and ideological distance (EI = 0 … "
        "ED = 6) together, with fixed effects for the activity terciles of the two deputies (measures signed, cut "
        "by value: activity_cuts). Party is nested in family and district in region: each coefficient is the "
        "increment over the broader one.",
    ]
    out["notes"] = [
        "Computed here from the signatures.",
        "The data have no gender, race or committee variable, so homophily by those cannot be estimated here.",
        "Dyads are not independent: the logit's standard errors are naive and too small. Use qap_p, or export the "
        "dyads (path) and fit an ERGM, as Bratton and Rouse (2011) do.",
        "Region is the historical region Afinidades Elegidas assigns to each district; Ceuta and Melilla are each "
        "their own.",
    ]
    out.update(_common(net, [BRATTON, CLARK, CRISP]))
    return out


# ── block densities ───────────────────────────────────────────────────────────

def block_density(legislature, by="family", ties="undirected", weighted=False, min_weight=1, topic=None,
                  measure_type=None, date_from=None, date_to=None, measure_ids=None, include_truncated=True,
                  path=None, overwrite=False) -> dict:
    """Density of co-signature ties within and between parties, families, ideologies or regions
    (the blockmodel image, as in Alemán and Calvo 2013): ties over possible dyads, over every member
    of the legislature."""
    _check_by(by)
    if ties not in ("directed", "undirected"):
        raise ValueError("ties must be directed or undirected")
    net = _network(legislature, topic, measure_type, date_from, date_to, measure_ids, include_truncated, min_weight)
    directed = ties == "directed"
    tie_w = net["directed"] if directed else net["undirected"]
    if not tie_w:
        raise store.NoData("No co-signatures for these measures.")
    sizes = Counter(_label(net, x, by) for x in net["members"])
    order = sorted(sizes, key=lambda g: (-sizes[g], g))
    cnt, wsum = Counter(), Counter()
    for (i, j), w in tie_w.items():
        gi, gj = _label(net, i, by), _label(net, j, by)
        key = (gi, gj) if directed else tuple(sorted((gi, gj)))
        cnt[key] += 1
        wsum[key] += w

    def possible(g, h):
        if g == h:
            return sizes[g] * (sizes[g] - 1) // (1 if directed else 2)
        return sizes[g] * sizes[h]
    N = len(net["members"])
    overall = len(tie_w) / (N * (N - 1) // (1 if directed else 2))
    matrix, image, cells = {}, {}, []
    for g in order:
        matrix[g], image[g] = {}, {}
        for h in order:
            key = (g, h) if directed else tuple(sorted((g, h)))
            pos = possible(g, h)
            d = cnt[key] / pos if pos else None
            dw = wsum[key] / pos if pos else None
            val = dw if weighted else d
            matrix[g][h] = _r(val, 4)
            image[g][h] = None if d is None else int(d >= overall)
            if directed or order.index(g) <= order.index(h):
                cells.append({"group_a": g, "group_b": h, "members_a": sizes[g], "members_b": sizes[h],
                              "ties": cnt[key], "possible": pos, "density": _r(d, 5), "weighted_density": _r(dw, 5),
                              "image": image[g][h]})
    within_t = sum(c["ties"] for c in cells if c["group_a"] == c["group_b"])
    within_p = sum(c["possible"] for c in cells if c["group_a"] == c["group_b"])
    between_t = sum(c["ties"] for c in cells if c["group_a"] != c["group_b"])
    between_p = sum(c["possible"] for c in cells if c["group_a"] != c["group_b"])
    out = {"legislature": legislature, "by": by, "ties": ties, "weighted": weighted,
           "summary": {"members": N, "groups": len(order), "ties": len(tie_w), "overall_density": _r(overall, 5),
                       "within_density": _r(within_t / within_p, 5) if within_p else None,
                       "between_density": _r(between_t / between_p, 5) if between_p else None,
                       "within_to_between": _r((within_t / within_p) / (between_t / between_p), 2)
                       if within_p and between_t else None},
           "groups": [{"group": g, "members": sizes[g]} for g in order],
           "density": matrix, "image": image, "image_threshold": _r(overall, 5),
           "densest_between_groups": sorted((c for c in cells if c["group_a"] != c["group_b"] and c["density"]),
                                            key=lambda c: -c["density"])[:10]}
    if path:
        out["files"] = [_write_rows(_out_path(path, None, overwrite)[0], cells)]
    out["method"] = [
        ("Directed ties (co-signatory → first signatory): density from group g to h = ties / (n_g·n_h), within g "
         "ties / (n_g·(n_g − 1)).") if directed else
        "Undirected ties: density between g and h = ties / (n_g·n_h), within g = ties / (n_g·(n_g − 1)/2).",
        "Every member of the legislature counts in n_g, isolated ones included. Within-group density is undefined "
        "(None) for a group of one. weighted=true divides measures signed together instead of ties: the mean "
        "co-signatures per dyad.",
        "image: 1 where the density reaches the density of the whole network (image_threshold), the usual α "
        "criterion of blockmodels. It is always built on the share of dyads tied, also with weighted=true.",
    ]
    out["notes"] = [
        "Computed here from the signatures.",
        "cross_group_coauthorship answers a different question: co-signatures (weighted) against what each group's "
        "activity predicts. Here the denominator is the possible dyads, so a large group with many inactive members "
        "has a low density.",
        "Densities of small groups rest on few dyads.",
    ]
    out.update(_common(net, [ALEMAN]))
    return out


# ── Newman's assortativity ────────────────────────────────────────────────────

def _newman_r(trace: float, s: float, t: float) -> float | None:
    """r = (Σ e_gg − Σ a_g·b_g) / (1 − Σ a_g·b_g), from raw totals: trace = Σ C_gg, s = Σ R_g·K_g, t = Σ C."""
    if not t:
        return None
    ab = s / (t * t)
    return (trace / t - ab) / (1 - ab) if ab < 1 else None


def _assortativity(edges: list[tuple[str, str, float]], directed: bool) -> dict:
    """Newman's (2003) r for ties (group of i, group of j, weight), each undirected tie counted in
    both directions, with the jackknife standard error over the ties (his eq. 4)."""
    C, R, K = Counter(), Counter(), Counter()
    for g, h, w in edges if directed else edges + [(h, g, w) for g, h, w in edges]:
        C[(g, h)] += w
        R[g] += w
        K[h] += w
    T = sum(R.values())
    trace = sum(v for (g, h), v in C.items() if g == h)
    S = sum(R[g] * K[g] for g in R)
    r = _newman_r(trace, S, T)
    var = None
    if r is not None:
        var = 0.0
        for g, h, w in edges:
            R2, K2 = Counter({x: R[x] for x in (g, h)}), Counter({x: K[x] for x in (g, h)})
            R2[g] -= w
            K2[h] -= w
            tr, t = trace - (w if g == h else 0), T - w
            if not directed:
                R2[h] -= w
                K2[g] -= w
                tr -= w if g == h else 0
                t -= w
            s = S - sum(R[x] * K[x] for x in {g, h}) + sum(R2[x] * K2[x] for x in {g, h})
            ri = _newman_r(tr, s, t)
            if ri is not None:
                var += (ri - r) ** 2
    ab = S / (T * T) if T else None
    return {"r": r, "se": math.sqrt(var) if var is not None else None,
            "r_min": -ab / (1 - ab) if ab is not None and ab < 1 else None, "C": C, "R": R, "K": K, "T": T}


def assortativity(legislature, by="party", ties="undirected", weighted=False, min_weight=1, topic=None,
                  measure_type=None, date_from=None, date_to=None, measure_ids=None, include_truncated=True) -> dict:
    """Newman's (2003) nominal assortativity of the co-signature network by party, family, ideology,
    district or region: how much more ties stay within groups than random mixing predicts, from
    −1 to 1, with a jackknife standard error; and the scalar assortativity of ideological position."""
    _check_by(by)
    if ties not in ("directed", "undirected"):
        raise ValueError("ties must be directed or undirected")
    net = _network(legislature, topic, measure_type, date_from, date_to, measure_ids, include_truncated, min_weight)
    directed = ties == "directed"
    tie_w = net["directed"] if directed else net["undirected"]
    if not tie_w:
        raise store.NoData("No co-signatures for these measures.")
    edges = [(_label(net, i, by), _label(net, j, by), float(w) if weighted else 1.0) for (i, j), w in tie_w.items()]
    dropped = sum(1 for g, h, _ in edges if NO_LABEL in (g, h))
    edges = [e for e in edges if NO_LABEL not in e[:2]]
    a = _assortativity(edges, directed)
    C, R, K, T = a["C"], a["R"], a["K"], a["T"]
    groups = sorted(R, key=lambda g: -R[g])
    per_group = [{"group": g, "share_of_tie_ends": _r(R[g] / T, 4), "within_share": _r(C[(g, g)] / T, 4),
                  "expected_within_share": _r(R[g] * K[g] / (T * T), 4),
                  "ratio": _r((C[(g, g)] / T) / (R[g] * K[g] / (T * T)), 2) if R[g] and K[g] else None}
                 for g in groups]
    out = {"legislature": legislature, "by": by, "ties": ties, "weighted": weighted,
           "r": _r(a["r"]), "se_jackknife": _r(a["se"]), "r_min": _r(a["r_min"]),
           "summary": {"members": len(net["members"]), "ties": len(tie_w), "ties_used": len(edges),
                       "ties_without_label": dropped, "groups": len(groups)},
           "by_group": per_group}
    # ideological position as a number: Pearson correlation across the ends of the ties
    ends = [((net["attrs"][i].get("ideo_pos")), (net["attrs"][j].get("ideo_pos")), float(w) if weighted else 1.0)
            for (i, j), w in tie_w.items()]
    ends = [e for e in ends if None not in e[:2]]
    if not directed:
        ends += [(y, x, w) for x, y, w in ends]
    W = sum(w for *_, w in ends)
    if W:
        mx = sum(x * w for x, _, w in ends) / W
        my = sum(y * w for _, y, w in ends) / W
        sxy = sum((x - mx) * (y - my) * w for x, y, w in ends)
        sxx = sum((x - mx) ** 2 * w for x, _, w in ends)
        syy = sum((y - my) ** 2 * w for _, y, w in ends)
        out["ideology_scalar_r"] = _r(sxy / math.sqrt(sxx * syy)) if sxx and syy else None
    out["method"] = [
        "e_gh = share of tie ends from group g to group h (each undirected tie counted in both directions), "
        "a_g and b_h its row and column sums: r = (Σ e_gg − Σ a_g·b_g) / (1 − Σ a_g·b_g). r = 1 when every tie stays "
        "within its group, 0 under random mixing, r_min under complete disassortative mixing.",
        "se_jackknife: Newman's (2003) jackknife, σ² = Σ_i (r_i − r)² with r_i computed without tie i.",
        "by_group: within_share against expected_within_share (= a_g·b_g) tells which groups drive r.",
        "ideology_scalar_r: the same idea for the ordinal position (EI = 0 … ED = 6), a Pearson correlation of the "
        "positions at the two ends of each tie. It does not depend on by.",
    ]
    out["notes"] = ["Computed here from the signatures.",
                    "weighted=true counts each tie as many times as measures signed together."]
    out.update(_common(net, [NEWMAN]))
    return out

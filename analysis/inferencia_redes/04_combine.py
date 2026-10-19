"""Pool the MRQAP chunks and put the three inferences side by side, per legislature and covariate:

    naive    the dyadic logit (glm, members who signed at least one measure): p assumes independent dyads
    mrqap    the same coefficients, p from Dekker's double semi-partialling (chunks pooled)
    ergm     the dyad-independent ERGM (MPLE), and the two-mode ERGM (deputies × measures, both degree
             sequences fixed), whose b1nodematch terms are the homophily of co-signing, without and with
             repeated collaboration (gwb1dsp). The one-mode ERGM
             with gwesp did not converge (results/ergm_gwesp_stopped.txt) and is not in the table.

Writes results/mrqap.csv (pooled) and results/summary.csv; prints the homophily rows.
Run from the repository root: python3 analysis/inferencia_redes/04_combine.py
"""
import csv
import glob
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
RES = HERE / "results"
LEGS = ("1931-1933", "1933-1936", "1936-1939")
HOMOPHILY = {"same_party": "nodematch.party", "same_family": "nodematch.family", "same_district": "nodematch.district",
             "same_region": "nodematch.region", "ideology_distance": "absdiff.ideo_pos", "same_ideology": None}
TWO_MODE = {"same_party": "b1nodematch.party", "same_family": "b1nodematch.family",
            "same_district": "b1nodematch.district", "same_region": "b1nodematch.region",
            "same_ideology": "b1nodematch.ideology"}


def read(path):
    with open(path, encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def pooled_mrqap() -> dict:
    acc = defaultdict(lambda: {"reps": 0, "hits": 0.0, "coef": None, "chunks": 0})
    for f in sorted(glob.glob(str(RES / "mrqap_*_s*.csv"))):
        for r in read(f):
            a = acc[(r["legislature"], r["term"])]
            reps = int(r["reps"])
            a["reps"] += reps
            a["hits"] += float(r["p_mrqap"]) * reps
            a["coef"] = float(r["coef"])
            a["chunks"] += 1
    rows = [{"legislature": leg, "term": term, "coef": round(a["coef"], 4), "p_mrqap": round(a["hits"] / a["reps"], 4),
             "reps": a["reps"], "chunks": a["chunks"]} for (leg, term), a in sorted(acc.items())]
    if rows:
        with open(RES / "mrqap.csv", "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
    return {(r["legislature"], r["term"]): r for r in rows}


def main() -> None:
    glm = {(r["legislature"], r["term"]): r for r in read(RES / "glm.csv") if r["spec"] == "active"}
    mrqap = pooled_mrqap()
    ergm = {}
    for f in glob.glob(str(RES / "ergm_*.csv")):
        for r in read(f):
            ergm[(r["model"], r["legislature"], r["term"])] = r
    out = []
    for leg in LEGS:
        for term, eterm in HOMOPHILY.items():
            g, m = glm.get((leg, term)), mrqap.get((leg, term))
            ei, eg = ergm.get(("indep", leg, eterm)), ergm.get(("bipartite", leg, TWO_MODE.get(term)))
            ed = ergm.get(("bipartite_dsp", leg, TWO_MODE.get(term)))
            out.append({"legislature": leg, "term": term,
                        "logit_coef": g and round(float(g["coef"]), 3), "logit_se": g and round(float(g["se"]), 3),
                        "logit_p": g and float(g["p"]),
                        "mrqap_p": m and m["p_mrqap"], "mrqap_reps": m and m["reps"],
                        "ergm_indep_coef": ei and round(float(ei["coef"]), 3),
                        "ergm2_coef": eg and round(float(eg["coef"]), 3),
                        "ergm2_se": eg and round(float(eg["se"]), 3),
                        "ergm2_p": eg and float(eg["p"]),
                        "ergm2_dsp_coef": ed and round(float(ed["coef"]), 3),
                        "ergm2_dsp_se": ed and round(float(ed["se"]), 3),
                        "ergm2_dsp_p": ed and float(ed["p"])})
    with open(RES / "summary.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
    for r in out:
        print(r)


if __name__ == "__main__":
    main()

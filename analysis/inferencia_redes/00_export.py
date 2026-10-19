"""Export, for each legislature, what the R inference needs, built by luz-mcp itself so that R works
on exactly the dyads the tools use:

    data/dyads_<leg>.csv       every pair of members: tie, weight, shared attributes, activity
                               (homophily(path=...), undirected co-signature network)
    data/nodes_<leg>.csv       members with party, family, district, region, ideology position,
                               activity (measures signed) and activity tercile
    data/signatures_<leg>.csv  deputy × measure (identified signatures), for a two-mode model
    results/tool_<leg>.json    the tool's own univariate table and dyadic logit, to compare with R

Run from the repository root: .venv/bin/python analysis/inferencia_redes/00_export.py
"""
import csv
import json
from collections import Counter
from pathlib import Path

from luz_mcp import groups as G, profile  # noqa: F401  (activates the Luz profile)

HERE = Path(__file__).resolve().parent
LEGS = ("1931-1933", "1933-1936", "1936-1939")


def main() -> None:
    for leg in LEGS:
        h = G.homophily(leg, permutations=1000, path=str(HERE / "data" / f"dyads_{leg}.csv"), overwrite=True)
        (HERE / "results" / f"tool_{leg}.json").write_text(
            json.dumps({k: h[k] for k in ("summary", "univariate", "qap_p_floor", "logit")}, ensure_ascii=False,
                       indent=1), encoding="utf-8")
        net = G._network(leg)
        activity = Counter(i for m in net["measures"] for i in set(m["signers"] or []))
        cuts = h["logit"]["activity_cuts"]
        q1, q2 = int(cuts["low"].split()[1]), int(cuts["mid"].split()[1])
        with open(HERE / "data" / f"nodes_{leg}.csv", "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["id_dip", "party", "family", "ideology", "ideo_pos", "district", "region", "activity",
                        "activity_tercile"])
            for x in net["members"]:
                a = net["attrs"][x]
                act = activity[x]
                w.writerow([x, a.get("partido"), a.get("familia_partidos"), a.get("ideologia"), a.get("ideo_pos"),
                            a.get("distrito"), a.get("region"), act,
                            "low" if act <= q1 else "mid" if act <= q2 else "high"])
        with open(HERE / "data" / f"signatures_{leg}.csv", "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["id_dip", "id_medida", "first_signatory"])
            for m in net["measures"]:
                for i in dict.fromkeys(m["signers"] or []):
                    w.writerow([i, m["id_medida"], int(i == m["sponsor"])])
        print(leg, h["summary"], cuts)


if __name__ == "__main__":
    main()

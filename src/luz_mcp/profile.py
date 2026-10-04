"""The Luz y Taquígrafos collection, as a profile of the parlaibero-mcp engine.

Luz y Taquígrafos (doi:10.7910/DVN/THQCMI) is one semicolon-separated file, `2REP_Diaries.csv`, with
14 columns of its own. This module says how they map to the engine's canonical columns and what is
checked on every import. Afinidades Elegidas (doi:10.7910/DVN/CGOCUS) is not a speech corpus: its
tables are loaded by afinidades.py.
"""
from __future__ import annotations

from pathlib import Path

from parlaibero_mcp import profile as engine_profile

DOI_LT = "10.7910/DVN/THQCMI"
DOI_AE = "10.7910/DVN/CGOCUS"
LT = "LT"

COLUMNS = {
    # one session = (legislature, num_session): num_session starts again in each legislature
    "id_session": "'LT' || left(legislature, 4) || lpad(num_session, 4, '0')",
    "id_int": "'LT' || lpad(id, 7, '0')",
    "legislature": "legislature",
    "legislative_session": "NULL",
    "session_number": "num_session",
    "date": "date",
    "session_type": "NULL",
    "intervention_order": '"order"',
    "speaker_raw": "speaker",
    "id_dep": "nullif(trim(rep_id), '')",
    "speaker_name": "nullif(trim(rep_name), '')",
    "sex": "NULL",
    "party": "nullif(trim(party), '')",
    "district": "nullif(trim(district), '')",
    # the session summary and what the Diario prints that nobody says (documents read out, votes,
    # narration) are rows of their own, not speech
    "dm_speech": "CASE WHEN speaker IN ('SUMARIO', 'COMENTARIOS') THEN 0 ELSE 1 END",
    "text": "speech",
}

EXTRA = {
    "party_family": ("VARCHAR", "nullif(trim(party_family), '')",
                     "Political family as published in Luz y Taquígrafos"),
    "ideology": ("VARCHAR", "nullif(trim(ideology), '')",
                 "Ideology code as published in Luz y Taquígrafos (EI, I, CI, C, CD, D, ED)"),
    "nwords_published": ("INTEGER", "TRY_CAST(nwords AS INTEGER)",
                         "Word count as published (n_words is the engine's own count)"),
    # the speaker's labels in the Afinidades Elegidas register for that legislature: the same labels
    # as the register of members, so voice and seats can be compared (filled by afinidades.py)
    "reg_party": ("VARCHAR", "NULL", "Party of the speaker in the Afinidades Elegidas register (that legislature)"),
    "reg_family": ("VARCHAR", "NULL", "Political family in the Afinidades Elegidas register"),
    "reg_ideology": ("VARCHAR", "NULL", "Ideology in the Afinidades Elegidas register"),
}


def _after_import(con, code: str, folder: Path) -> None:
    """Checks on the published file, then the Afinidades tables if they are on disk."""
    bad = con.execute("SELECT count(*) FROM interventions WHERE country = 'LT' "
                      "AND row_n <> CAST(substr(id_int, 3) AS BIGINT)").fetchone()[0]
    if bad:
        raise RuntimeError(f"{bad} rows whose id is not their record number: this is not the published file.")
    many = con.execute("SELECT count(*) FROM (SELECT id_session FROM interventions WHERE country = 'LT' "
                       "GROUP BY 1 HAVING count(DISTINCT date) > 1)").fetchone()[0]
    if many:
        raise RuntimeError(f"{many} sessions with more than one date: the session key (legislature, num_session) "
                           f"does not hold in this file.")
    from . import afinidades
    ae = folder.parent / "AE"
    if (ae / afinidades.FILES["measures"]).exists():
        afinidades.load(con, ae)


LUZ = engine_profile.Profile(
    name="luz", title="Luz y Taquígrafos",
    datasets={LT: ("Luz y Taquígrafos", "Luz y Taquígrafos", DOI_LT)},
    collection_url=f"https://doi.org/{DOI_LT}",
    home_env="LUZ_HOME", default_home="~/.luz",
    interventions_file=lambda code: "2REP_Diaries.csv",
    deputies_file=lambda code: None,
    delimiter=";",
    column_sql=COLUMNS,
    extra_columns=EXTRA,
    row_key_csv="id",
    row_key_sql="CAST(CAST(substr(id_int, 3) AS BIGINT) AS VARCHAR)",
    has_sex=False,
    group_columns=("party", "party_family", "ideology", "reg_party", "reg_family", "reg_ideology"),
    # the explorer's own name for the corpus, whichever version of the CSV it loaded (measured: its
    # engine builds V3 and round-trips a library written here); the version travels in `fuente`
    explorer_corpus=lambda code: "2REP_Diaries",
    explorer_name="Luz y Taquígrafos Explorer",
    explorer_url="https://rodrodr.github.io/luz_explorer",
    after_import=_after_import,
    package="luz-mcp",
    repository="https://github.com/rodrodr/luz-tools",
)

engine_profile.activate(LUZ)

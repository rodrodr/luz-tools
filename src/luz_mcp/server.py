"""MCP server for Luz y Taquígrafos (plenary debates of the Spanish Second Republic) and Afinidades
Elegidas (its co-sponsorship networks), built on the parlaibero-mcp engine."""
from typing import Annotated, Literal

import anyio
import anyio.from_thread
from mcp.types import ToolAnnotations
from pydantic import Field

from . import profile  # noqa: F401  (activates the Luz profile before the engine is used)
from . import __version__, afinidades as ae, data
from parlaibero_mcp import analysis, library as libmod, server as S, store
from parlaibero_mcp.server import Server, Tools, make_before

INSTRUCTIONS = """\
Luz y Taquígrafos: the plenary debates of the Spanish Congress of Deputies under the Second Republic
(1931-1939, plus five sessions in exile in 1945), one row per intervention, linked to the deputies.
Afinidades Elegidas: the collectively signed measures of the same chamber (bills, amendments, motions,
interpellations…), their signatures, the co-authorship network and its published network metrics.
Two datasets in Harvard Dataverse (CC BY 4.0): doi:10.7910/DVN/THQCMI and doi:10.7910/DVN/CGOCUS.

How to work with it:
1. `download_data` once (about 210 MB). `coverage` shows the base by year or legislature.
2. Speech: `ngram_viewer`, `term_counter`, `term_frequency`, `distinctive_words`, `share_of_voice`,
   `kwic`, `collocations`, `search_text`, `get_intervention`, `get_session`; libraries
   (`library_create` …) to work on a subset; `query_sql` for anything else (schema: `describe_data`).
3. Measures and network: `search_measures`, `get_measure` (with the debate where it was read and
   defended), `coauthorship_network`, `deputy_neighbors`, `cross_group_coauthorship`,
   `network_metrics`, `structural_roles`, `deputy_profile`, and `speech_by_network`, which saves the
   speeches of each network role as a library so the text tools can compare them.
4. There is NO sex variable in either dataset: nothing can be broken down by sex.
5. speaker = SUMARIO (session summary, order 0) and COMENTARIOS (documents read out, votes, the
   Diario's narration) are not speech: dm_speech = 0. Filter dm_speech = 1 to study what was said.
6. Two sets of party labels: `party`, `party_family`, `ideology` as published in Luz y Taquígrafos,
   and `reg_party`, `reg_family`, `reg_ideology` from the Afinidades register (revised). Compare
   voice with seats (share_of_voice) only with the reg_* labels, which the register of members shares.
7. The legislature labels differ: Luz says 1933-1935, Afinidades 1933-1936 (the same legislature).
8. Network metrics and roles are the published ones, not recomputed. Topic, title and defence of
   each measure were assigned with language models and human review. Some signature lists are
   truncated in the Diario, so their edges are missing.
9. Row identifiers are stable within a version (Luz V3 renumbered every row). Cite each dataset
   with its version (`how_to_cite`).
"""

LOGGED = {"query_sql", "search_text", "term_frequency", "ngram_viewer", "term_counter", "share_of_voice",
          "distinctive_words", "kwic", "collocations", "coverage", "export_result", "get_session",
          "get_intervention", "library_create", "library_edit", "library_combine", "library_describe",
          "library_delete", "library_rebuild", "library_export", "library_import", "search_measures",
          "get_measure", "coauthorship_network", "deputy_neighbors", "cross_group_coauthorship",
          "network_metrics", "structural_roles", "speech_by_network", "deputy_profile"}

_server = Server(name="luz", instructions=INSTRUCTIONS)
mcp = Tools(_server, make_before(LOGGED, "luz-mcp"))

READ = ToolAnnotations(readOnlyHint=True, openWorldHint=False)
REMOTE_READ = ToolAnnotations(readOnlyHint=True, openWorldHint=True)
WRITE_LOCAL = ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=False)

DateFrom = Annotated[str | None, Field(description="YYYY or YYYY-MM-DD")]
DateTo = Annotated[str | None, Field(description="YYYY or YYYY-MM-DD (inclusive)")]
Party = Annotated[str | None, Field(description="Party as published in Luz y Taquígrafos (ILIKE pattern: 'PSOE', "
                                                "'%Radical%')")]
Family = Annotated[str | None, Field(description="Political family as published in Luz y Taquígrafos (ILIKE), "
                                                 "e.g. 'Socialista', 'Republicanos'")]
Ideology = Annotated[str | None, Field(description="Ideology code as published: EI, I, CI, C, CD, D, ED")]
SpeechOnly = Annotated[bool, Field(description="Only rows with dm_speech = 1 (recommended)")]
ExcludeChair = Annotated[bool, Field(description="Leave out the presiding officer's turns")]
MaxTurnWords = Annotated[int | None, Field(ge=100, description="Leave out turns longer than this many words")]
Library = Annotated[str | None, Field(description="Name of a library (see library_describe): only its interventions")]
Terms = Annotated[str, Field(description="Comma-separated series; '+' sums variants; '*' ends a prefix. Whole words, "
                                         "case- and accent-insensitive.")]
Deputy = Annotated[str, Field(description="id_dip (= id_dep of the speeches) or part of the name")]
Legislature = Annotated[Literal["1931-1933", "1933-1936", "1936-1939"] | None, Field(
    description="Legislature (Afinidades labels; 1933-1936 is Luz's 1933-1935)")]
Period = Annotated[Literal["1931-1933", "1933-1936", "1936-1939", "total"], Field(
    description="A legislature, or the whole Republic ('total')")]
Topic = Annotated[str | None, Field(description="One of the 13 topics (main or secondary), e.g. 'agrario', "
                                                "'religión', 'orden público' — see describe_data")]


def _F(date_from=None, date_to=None, party=None, party_family=None, ideology=None, id_dep=None, speech_only=True,
       exclude_chair=False, max_turn_words=None, library=None) -> analysis.Filters:
    lib_id = libmod.resolve(library)[0] if library else None
    return analysis.Filters(None, date_from, date_to, party, None, id_dep, speech_only, exclude_chair,
                            max_turn_words, lib_id, library or None,
                            {"party_family": party_family, "ideology": ideology})


# ── the data ──────────────────────────────────────────────────────────────────

@mcp.tool(annotations=REMOTE_READ)
def list_datasets() -> dict:
    """The two datasets: DOI, published version, and what is downloaded locally."""
    return data.list_datasets()


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True,
                                      openWorldHint=True))
async def download_data(ctx: S.Context, force: Annotated[bool, Field(description="Download again even if current")] = False
                        ) -> dict:
    """Download both datasets from Harvard Dataverse (MD5-verified, about 210 MB) and load them.
    Files already current are skipped. Takes about a minute."""
    def progress(name, done, total):
        try:
            anyio.from_thread.run(ctx.report_progress, done, total, f"{name}: {done / 2**20:.0f} MB")
        except Exception:
            pass
    return await anyio.to_thread.run_sync(lambda: data.download_all(force, progress))


@mcp.tool(annotations=REMOTE_READ)
def get_documentation(
    document: Annotated[Literal[tuple(data.DOCUMENTS)], Field(  # type: ignore[valid-type]
        description="luz_readme · luz_changelog (V3) · afinidades_readme · afinidades_codebook (every variable) · "
                    "afinidades_methodology (network, metrics, roles, topics) · afinidades_changelog · "
                    "afinidades_reproducibility")] = "luz_readme",
    language: Annotated[Literal["en", "es"], Field(description="For the changelog of Luz")] = "en",
) -> str:
    """A documentation file deposited with the datasets (works before downloading)."""
    return data.read_document(document, language)


@mcp.tool(annotations=REMOTE_READ)
def how_to_cite(dataset: Annotated[Literal["luz", "afinidades"], Field(description="Which dataset")] = "luz") -> dict:
    """Formatted citation (latest published version) and DOI of a dataset."""
    return data.citation(dataset)


@mcp.tool(annotations=READ)
def describe_data() -> dict:
    """Tables of the local database, their columns, and example queries."""
    return data.describe()


# ── speech (the parlaibero-mcp engine) ────────────────────────────────────────

@mcp.tool(annotations=READ)
def query_sql(sql: Annotated[str, Field(description="DuckDB SQL over the tables in describe_data")],
              max_rows: Annotated[int, Field(ge=1, le=5000)] = 200,
              max_cell_chars: Annotated[int, Field(ge=50, le=100000)] = 1000,
              timeout_s: Annotated[int, Field(ge=1, le=600)] = 120) -> dict:
    """Run a read-only SQL query (DuckDB). The connection cannot write, read other files or reach the network."""
    return S.query_sql(sql, max_rows, max_cell_chars, timeout_s)


@mcp.tool(annotations=READ)
def search_text(
    pattern: Annotated[str, Field(description="Word or phrase (or RE2 regex if regex=true)")],
    regex: bool = False,
    whole_word: bool = False,
    date_from: DateFrom = None, date_to: DateTo = None,
    party: Party = None, party_family: Family = None, ideology: Ideology = None,
    id_dep: Annotated[str | None, Field(description="A deputy's id (id_dip)")] = None,
    speech_only: SpeechOnly = True,
    library: Library = None,
    limit: Annotated[int, Field(ge=1, le=200)] = 20,
    offset: Annotated[int, Field(ge=0)] = 0,
) -> dict:
    """Find interventions containing a word, phrase or regex, newest first, with a snippet and the
    total number of matches. Plain searches ignore case and accents."""
    return analysis.search_text(pattern, _F(date_from, date_to, party, party_family, ideology, id_dep, speech_only,
                                            library=library), regex, whole_word, limit, offset)


@mcp.tool(annotations=READ)
def get_intervention(id_int: Annotated[str, Field(description="Intervention id, e.g. LT0075580 (LT + the row "
                                                              "number of 2REP_Diaries.csv V3)")],
                     context: Annotated[int, Field(ge=0, le=20)] = 0) -> dict:
    """Full text and metadata of one intervention, optionally with the turns around it."""
    return S.get_intervention(id_int, context)


@mcp.tool(annotations=READ)
def get_session(id_session: Annotated[str, Field(description="Session id: LT + first year of the legislature + "
                                                             "session number, e.g. LT19310001")],
                include_text: bool = False, max_rows: Annotated[int, Field(ge=1, le=2000)] = 300) -> dict:
    """Metadata and the ordered list of turns of a session."""
    return S.get_session(id_session, include_text, max_rows)


@mcp.tool(annotations=WRITE_LOCAL)
def ngram_viewer(
    terms: Terms,
    measure: Annotated[Literal["per_million", "count", "interventions_pct"], Field(
        description="per_million words, raw count, or % of interventions")] = "per_million",
    smoothing: Annotated[int, Field(ge=0, le=5)] = 0,
    date_from: DateFrom = None, date_to: DateTo = None,
    party: Party = None, party_family: Family = None, ideology: Ideology = None,
    speech_only: SpeechOnly = True, exclude_chair: ExcludeChair = False, max_turn_words: MaxTurnWords = None,
    library: Library = None,
    chart_path: Annotated[str | None, Field(description="'.svg' or '.html' chart (at most 8 series)")] = None,
    title: str | None = None,
    language: Literal["es", "en", "pt"] = "es",
    overwrite: bool = False,
) -> dict:
    """Yearly frequency of words or phrases (Google Books Ngram-style), with the base behind every
    point and low-base years flagged (the exile years are). Optionally writes an SVG or HTML chart."""
    return analysis.ngram_viewer(terms, _F(date_from, date_to, party, party_family, ideology, None, speech_only,
                                           exclude_chair, max_turn_words, library),
                                 False, measure, smoothing, chart_path, title, language, overwrite)


@mcp.tool(annotations=READ)
def term_counter(terms: Terms, date_from: DateFrom = None, date_to: DateTo = None, party: Party = None,
                 party_family: Family = None, ideology: Ideology = None, speech_only: SpeechOnly = True,
                 exclude_chair: ExcludeChair = False, max_turn_words: MaxTurnWords = None,
                 library: Library = None) -> dict:
    """Occurrences, interventions, sessions and speakers of one or more terms, by party, and the
    first and last use."""
    return analysis.term_counter(terms, _F(date_from, date_to, party, party_family, ideology, None, speech_only,
                                           exclude_chair, max_turn_words, library))


@mcp.tool(annotations=READ)
def term_frequency(
    pattern: Annotated[str, Field(description="Word or phrase; '+' sums variants, '*' ends a prefix")],
    by: Annotated[Literal["year", "legislature", "party", "party_family", "ideology", "reg_party", "reg_family",
                          "reg_ideology", "speaker", "session"], Field(description="Grouping")] = "year",
    date_from: DateFrom = None, date_to: DateTo = None, party: Party = None, party_family: Family = None,
    ideology: Ideology = None, speech_only: SpeechOnly = True, exclude_chair: ExcludeChair = False,
    max_turn_words: MaxTurnWords = None, library: Library = None,
    max_rows: Annotated[int, Field(ge=1, le=2000)] = 300,
) -> dict:
    """How often a term is used, grouped by year, legislature, party, family, ideology, speaker or
    session (by='session' shows where it concentrates)."""
    return analysis.term_frequency(pattern, _F(date_from, date_to, party, party_family, ideology, None, speech_only,
                                               exclude_chair, max_turn_words, library), by, max_rows)


@mcp.tool(annotations=READ)
def share_of_voice(
    by: Annotated[Literal["reg_party", "reg_family", "reg_ideology"], Field(
        description="Group, with the labels of the Afinidades register (the ones the list of members uses)")]
        = "reg_family",
    per: Literal["legislature", "year", "all"] = "legislature",
    unit: Literal["words", "turns"] = "words",
    date_from: DateFrom = None, date_to: DateTo = None,
    exclude_chair: ExcludeChair = False, max_turn_words: MaxTurnWords = None, library: Library = None,
) -> dict:
    """How much each group speaks against its weight among the members of the chamber (the
    Afinidades register): share of words or turns, of speakers, of members, and the ratio."""
    return analysis.share_of_voice(_F(date_from, date_to, exclude_chair=exclude_chair,
                                      max_turn_words=max_turn_words, library=library), by, per, unit)


@mcp.tool(annotations=READ)
def distinctive_words(
    field: Annotated[Literal["party", "party_family", "ideology", "reg_party", "reg_family", "reg_ideology",
                             "period", "id_dep", "library"], Field(description="What separates the groups")],
    a: Annotated[str, Field(description="Group A: a label, a period '1931-1933', an id_dep or a library name")],
    b: Annotated[str | None, Field(description="Group B; omit for 'everyone else'")] = None,
    date_from: DateFrom = None, date_to: DateTo = None,
    exclude_chair: ExcludeChair = False, max_turn_words: MaxTurnWords = None, library: Library = None,
    top: Annotated[int, Field(ge=5, le=200)] = 30, min_count: Annotated[int, Field(ge=1)] = 20,
) -> dict:
    """Words that most distinguish group A from group B (weighted log-odds, Monroe et al. 2008): one
    family or party against another, one period against another, a library against the rest."""
    return analysis.distinctive_words(_F(date_from, date_to, exclude_chair=exclude_chair,
                                         max_turn_words=max_turn_words, library=library), field, a, b, top, min_count)


@mcp.tool(annotations=READ)
def kwic(pattern: Annotated[str, Field(description="Word or phrase ('*' ends a prefix), or RE2 regex")],
         regex: bool = False, whole_word: bool = True, date_from: DateFrom = None, date_to: DateTo = None,
         party: Party = None, party_family: Family = None, ideology: Ideology = None, library: Library = None,
         n: Annotated[int, Field(ge=1, le=500)] = 40, width: Annotated[int, Field(ge=20, le=300)] = 70,
         order: Literal["random", "newest", "oldest"] = "random", seed: int = 1) -> dict:
    """Keyword in context: concordance lines from a sample of the interventions that use the term."""
    return analysis.kwic(pattern, _F(date_from, date_to, party, party_family, ideology, library=library), regex,
                         whole_word, n, width, order, seed)


@mcp.tool(annotations=READ)
def collocations(pattern: Annotated[str, Field(description="Word or phrase ('*' ends a prefix)")],
                 date_from: DateFrom = None, date_to: DateTo = None, party: Party = None,
                 party_family: Family = None, ideology: Ideology = None, exclude_chair: ExcludeChair = False,
                 library: Library = None, window: Annotated[int, Field(ge=1, le=20)] = 5,
                 top: Annotated[int, Field(ge=5, le=200)] = 30, min_count: Annotated[int, Field(ge=2)] = 5,
                 sample: Annotated[int, Field(ge=100, le=50000)] = 5000, exclude_stopwords: bool = True) -> dict:
    """Words that keep company with a term (Dunning log-likelihood within ±window tokens)."""
    return analysis.collocations(pattern, _F(date_from, date_to, party, party_family, ideology,
                                             exclude_chair=exclude_chair, library=library),
                                 window, top, min_count, sample, exclude_stopwords)


@mcp.tool(annotations=READ)
def coverage(by: Literal["year", "legislature"] = "year", date_from: DateFrom = None, date_to: DateTo = None,
             library: Library = None) -> dict:
    """The base before reading a trend: sessions, rows, speech words and linked share per year or
    legislature, missing years and low-base periods."""
    return analysis.coverage(_F(date_from, date_to, library=library), by)


@mcp.tool(annotations=WRITE_LOCAL)
def export_result(sql: Annotated[str, Field(description="One SELECT over the tables in describe_data")],
                  path: Annotated[str, Field(description="Output .csv or .parquet")],
                  format: Literal["csv", "parquet"] | None = None, overwrite: bool = False) -> dict:
    """Save the full result of a query to CSV or Parquet."""
    return analysis.export_result(sql, path, format, overwrite)


@mcp.tool(annotations=WRITE_LOCAL)
def query_log(last: Annotated[int, Field(ge=1, le=5000)] = 50,
              methods_path: Annotated[str | None, Field(description="Also write a Markdown methods note")] = None,
              overwrite: bool = False) -> dict:
    """The analyses run so far (tool, parameters, dataset versions), for the methods section."""
    return analysis.query_log(last, methods_path, overwrite)


# ── libraries ─────────────────────────────────────────────────────────────────

@mcp.tool(annotations=WRITE_LOCAL)
def library_create(
    name: Annotated[str, Field(description="Library name")],
    terms: Annotated[str | None, Field(description="An intervention enters if it uses ANY of these (comma or '+', "
                                                   "'*' prefix)")] = None,
    regex: bool = False,
    min_occurrences: Annotated[int, Field(ge=1, le=100, description="2-3 keeps those that discuss the topic")] = 1,
    date_from: DateFrom = None, date_to: DateTo = None,
    party: Party = None,
    id_dep: Annotated[str | None, Field(description="A deputy's id")] = None,
    speech_only: SpeechOnly = True, exclude_chair: ExcludeChair = False, max_turn_words: MaxTurnWords = None,
    description: str = "", color: str = "indigo", extend: bool = False,
) -> dict:
    """Create a library: a named, saved subset of interventions (a debate, a topic, a period, a
    party), with its definition and the data version. Then pass library=<name> to any tool. For the
    speeches of a network role, use speech_by_network."""
    return libmod.create(name, ["LT"], terms, regex, min_occurrences, date_from, date_to, party, None, id_dep,
                         speech_only, exclude_chair, max_turn_words, None, 0, 0, None, None, description, color,
                         extend)


for _fn in (S.library_edit, S.library_combine, S.library_describe, S.library_delete, S.library_rebuild):
    mcp.tool(annotations=READ if _fn is S.library_describe else
             ToolAnnotations(readOnlyHint=False, destructiveHint=_fn in (S.library_edit, S.library_delete),
                             openWorldHint=False))(_fn)


@mcp.tool(annotations=WRITE_LOCAL)
def library_export(name: Annotated[str, Field(description="Library name")],
                   folder: Annotated[str, Field(description="Destination folder")],
                   table_format: Literal["csv", "parquet"] | None = None, overwrite: bool = False) -> dict:
    """Write a library for the Luz y Taquígrafos Explorer as a .2replib (row numbers of Luz V3) plus
    an index, and optionally as CSV/Parquet with metadata, notes and tags. ⚠ In the explorer, load
    the V3 file from Dataverse before importing it: the explorer also accepts V2, where the same
    row numbers are other interventions."""
    r = libmod.export(name, folder, table_format, overwrite)
    r["warning"] = ("These files use the row numbers of Luz y Taquígrafos V3 (2REP_Diaries.csv of Dataverse version "
                    "3, 121,700 rows). Import them in the explorer only with that file loaded: it also accepts the "
                    "V2 file (107,551 rows), and there the same numbers point to other interventions.")
    return r


@mcp.tool(annotations=WRITE_LOCAL)
def library_import(paths: Annotated[list[str], Field(description=".2replib files, an index, or a folder")],
                   name: str | None = None, force: bool = False) -> dict:
    """Bring a library made in the Luz y Taquígrafos Explorer (on V3) into the MCP. Every item is
    checked against the data (row → intervention → date and speaker)."""
    return libmod.import_files(paths, name, force)


# ── Afinidades Elegidas: measures and signatures ──────────────────────────────

@mcp.tool(annotations=READ)
def search_measures(
    text: Annotated[str | None, Field(description="Word or phrase in the title or text")] = None,
    topic: Topic = None,
    measure_type: Annotated[str | None, Field(description="Type (ILIKE), e.g. 'proposición de ley', 'enmienda', "
                                                          "'interpelación'")] = None,
    legislature: Legislature = None, date_from: DateFrom = None, date_to: DateTo = None,
    signer: Annotated[str | None, Field(description="A deputy who signed it (id or name)")] = None,
    first_author: Annotated[str | None, Field(description="Its first signatory (id or name)")] = None,
    signer_party: Annotated[str | None, Field(description="Party of any signatory (Afinidades acronym)")] = None,
    signer_family: Annotated[str | None, Field(description="Family of any signatory")] = None,
    defence: Annotated[Literal["sí", "retirada", "no identificada"] | None, Field(
        description="Defended on the floor, withdrawn, or none identified")] = None,
    limit: Annotated[int, Field(ge=1, le=500)] = 20, offset: Annotated[int, Field(ge=0)] = 0,
) -> dict:
    """Find collectively signed measures (Afinidades Elegidas) by topic, type, date, signatory, party
    or text, with their title, topic, number of signatures and defence, plus counts by topic and type."""
    return ae.search_measures(text, topic, measure_type, legislature, date_from, date_to, signer, first_author,
                              signer_party, signer_family, defence, limit, offset)


@mcp.tool(annotations=READ)
def get_measure(id_medida: Annotated[int, Field(description="Measure id")],
                context: Annotated[int, Field(ge=0, le=10, description="Turns around the debate rows")] = 1) -> dict:
    """A measure in full: its text, every signature (illegible ones and truncated lists marked), and
    the debate in Luz y Taquígrafos where it was read and where it was defended or withdrawn."""
    return ae.get_measure(id_medida, context)


# ── the network ───────────────────────────────────────────────────────────────

@mcp.tool(annotations=WRITE_LOCAL)
def coauthorship_network(
    legislature: Legislature = None, topic: Topic = None,
    measure_type: Annotated[str | None, Field(description="Type of measure (ILIKE)")] = None,
    date_from: DateFrom = None, date_to: DateTo = None,
    measure_ids: Annotated[list[int] | None, Field(description="Only these measures")] = None,
    min_weight: Annotated[int, Field(ge=1, description="Keep pairs who co-signed at least this many")] = 1,
    include_truncated: Annotated[bool, Field(description="Include measures whose signature list is truncated")] = True,
    path: Annotated[str | None, Field(description="Write the network: '.graphml' (Gephi, igraph, networkx) or "
                                                  "'.csv' (nodes and edges files)")] = None,
    overwrite: bool = False,
) -> dict:
    """The co-signature network of a legislature, a topic or a set of measures: size, density,
    components, co-signatures within and across families, the most connected deputies, and
    optionally the network as a file."""
    return ae.coauthorship_network(legislature, topic, measure_type, date_from, date_to, measure_ids, min_weight,
                                   include_truncated, path, overwrite)


@mcp.tool(annotations=READ)
def deputy_neighbors(who: Deputy, legislature: Legislature = None, topic: Topic = None,
                     top: Annotated[int, Field(ge=1, le=500)] = 30) -> dict:
    """A deputy's ego network: co-authors with the number of measures signed together, and how much
    of it stays within their party and family."""
    return ae.deputy_neighbors(who, legislature, topic, top)


@mcp.tool(annotations=READ)
def cross_group_coauthorship(by: Literal["family", "party", "ideology"] = "family",
                             legislature: Legislature = None, topic: Topic = None) -> dict:
    """Co-signatures between parties, families or ideologies: observed against expected and the E-I
    index of each group, plus the published proximity index."""
    return ae.cross_group_coauthorship(by, legislature, topic)


@mcp.tool(annotations=READ)
def network_metrics(
    who: Annotated[str | None, Field(description="A deputy (id or name): all their metrics by period")] = None,
    period: Period = "total",
    metric: Annotated[str | None, Field(description="Rank deputies by this metric (omit to list the metrics)")] = None,
    party: Annotated[str | None, Field(description="Afinidades party acronym (ILIKE)")] = None,
    family: Annotated[str | None, Field(description="Afinidades family (ILIKE)")] = None,
    top: Annotated[int, Field(ge=1, le=1000)] = 20, ascending: bool = False,
) -> dict:
    """The published network metrics (centralities, Guimerà-Amaral, ego networks, profiles): one
    deputy's, or a ranking. Not recomputed."""
    return ae.network_metrics(who, period, metric, party, family, top, ascending)


@mcp.tool(annotations=READ)
def structural_roles(period: Period = "total", by: Literal["party", "family"] = "party") -> dict:
    """How the six published structural roles (isolated … leader of the chamber) are distributed by
    party or family, and who the leaders and articulators are."""
    return ae.structural_roles(period, by)


# ── speech × network ──────────────────────────────────────────────────────────

@mcp.tool(annotations=WRITE_LOCAL)
def speech_by_network(
    period: Annotated[Literal["1931-1933", "1933-1936", "1936-1939"], Field(description="Legislature")],
    split: Annotated[Literal["role", "metric"], Field(description="Group deputies by structural role, or by "
                                                                  "quantiles of a metric")] = "role",
    metric: Annotated[str | None, Field(description="With split='metric', e.g. 'betweenness_pct', "
                                                    "'transversality_score'")] = None,
    groups: Annotated[int, Field(ge=2, le=10, description="Number of quantile groups")] = 3,
    library_prefix: Annotated[str | None, Field(description="Prefix of the libraries it creates")] = None,
    exclude_chair: Annotated[bool, Field(description="Leave out the presiding officer's procedural turns "
                                                     "(recommended)")] = True,
) -> dict:
    """Cross speech and network position: how much each group of deputies (by network role, or by
    quantiles of a metric) speaks in that legislature, and their speeches saved as one library per
    group — then compare them with distinctive_words(field='library'), kwic or ngram_viewer."""
    return ae.speech_by_network(period, split, metric, groups, library_prefix, exclude_chair)


@mcp.tool(annotations=READ)
def deputy_profile(who: Deputy) -> dict:
    """Everything about one deputy: register by legislature, how much and when they spoke, the
    measures they signed, led and defended, their topics, and their network position and role."""
    return ae.deputy_profile(who)


@_server.resource("luz://about", mime_type="text/markdown")
def about() -> str:
    """What these datasets are and how this server works."""
    return f"# luz-mcp {__version__}\n\n{INSTRUCTIONS}\n\nLocal data: `{store.HOME}`\n"


def main() -> None:
    _server.run()

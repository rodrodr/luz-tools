"""Getting the two datasets: download (MD5-verified), import, documentation and citation."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from parlaibero_mcp import dataverse, store

from . import afinidades
from .profile import DOI_AE, DOI_LT, LT

DATASETS = {"luz": ("Luz y Taquígrafos", DOI_LT, "LT"), "afinidades": ("Afinidades Elegidas", DOI_AE, "AE")}
# key → (dataset folder, file name; {lang} for the translated ones)
DOCUMENTS = {
    "luz_readme": ("LT", "Luz_y_Taquigrafos_README.txt"),
    "luz_changelog": ("LT", "changelog_{lang}_10_2026.txt"),
    "afinidades_readme": ("AE", "README_v3.md"),
    "afinidades_codebook": ("AE", "CODEBOOK_v3.md"),
    "afinidades_methodology": ("AE", "METHODOLOGY_v3.md"),
    "afinidades_changelog": ("AE", "CHANGELOG_v3.md"),
    "afinidades_reproducibility": ("AE", "REPRODUCIBILITY_GUIDE_v3.md"),
}


def list_datasets() -> dict:
    loaded = store.loaded()

    def one(key):
        title, doi, folder = DATASETS[key]
        item = {"dataset": key, "title": title, "doi": doi, "url": f"https://doi.org/{doi}"}
        try:
            s = dataverse.summary(doi)
            item.update(published_title=s["title"], published_version=s["version"],
                        download_mb=round(sum(f["size"] or 0 for f in s["files"]) / 2**20))
        except Exception as e:
            item["remote_error"] = str(e)
        v = store.country_dir(folder) / ".version"
        item["downloaded_version"] = v.read_text().strip() if v.exists() else None
        if key == "luz":
            item["loaded"] = loaded.get(LT)
        else:
            try:
                item["loaded"] = afinidades._q("SELECT version, imported_at FROM ae_dataset")[0]
            except Exception:
                item["loaded"] = None
        return item

    with ThreadPoolExecutor(max_workers=2) as ex:
        items = list(ex.map(one, DATASETS))
    return {"datasets": items, "data_home": str(store.HOME)}


def _download_files(doi: str, folder: str, force: bool, progress=None) -> tuple[str, list[str]]:
    info = dataverse.summary(doi)
    d = store.country_dir(folder)
    d.mkdir(parents=True, exist_ok=True)
    stamp = d / ".version"
    current = stamp.read_text().strip() if stamp.exists() else None
    got = []
    for f in info["files"]:
        dest = d / f["filename"]
        if dest.exists() and not force and current == info["version"] and \
                (f["size"] is None or dest.stat().st_size == f["size"]):
            continue
        cb = (lambda done, total, name=f["filename"]: progress(name, done, total)) if progress else None
        dataverse.download(f["id"], dest, f["md5"], cb)
        got.append(f["filename"])
    stamp.write_text(info["version"])
    return info["version"], got


def download_all(force: bool = False, progress=None) -> dict:
    """Afinidades first (files only), then Luz: importing Luz loads the Afinidades tables too, and
    links each intervention to the register."""
    ae_version, ae_files = _download_files(DOI_AE, "AE", force, progress)
    r = store.download_country(LT, force, progress)
    with store.connect(read_only=False) as con:
        checks = con.execute("SELECT report FROM ae_checks").fetchone()
    import json
    return {"luz_y_taquigrafos": {k: r[k] for k in ("rows", "speech_rows", "sessions", "date_min", "date_max",
                                                     "version", "downloaded_files")},
            "afinidades_elegidas": {"version": ae_version, "downloaded_files": ae_files,
                                    "checks": json.loads(checks[0]) if checks else None}}


def reload_afinidades() -> dict:
    """Load the Afinidades tables again from the files on disk (after replacing them by hand)."""
    with store.connect(read_only=False) as con:
        return afinidades.load(con, store.country_dir("AE"))


def read_document(document: str, language: str = "en") -> str:
    if document not in DOCUMENTS:
        raise ValueError(f"Unknown document {document!r}. Use one of: {', '.join(DOCUMENTS)}")
    folder, name = DOCUMENTS[document]
    name = name.format(lang="es" if language.lower().startswith("es") else "en")
    local = store.country_dir(folder) / name
    if local.exists():
        return local.read_text(encoding="utf-8")
    doi = DOI_LT if folder == "LT" else DOI_AE
    f = next((f for f in dataverse.summary(doi)["files"] if f["filename"] == name), None)
    if f is None:
        raise FileNotFoundError(f"{name} is not part of the published dataset")
    return dataverse.fetch_text(f["id"])


def citation(dataset: str) -> dict:
    title, doi, _ = DATASETS[dataset]
    return {"dataset": title, "doi": doi, "citation": dataverse.citation(doi), "license": "CC BY 4.0",
            "note": "Cite each dataset you use with its version: row identifiers are only stable within a version."}


def describe() -> dict:
    return {
        "tables": {
            "interventions": "Luz y Taquígrafos, one row per intervention: country ('LT'), id_session "
                             "(LT + first year of the legislature + session number), id_int (LT + row number of "
                             "2REP_Diaries.csv V3), legislature (Luz labels: 1931-1933, 1933-1935, 1936-1939), "
                             "session_number, date, intervention_order (0 = SUMARIO), speaker_raw, id_dep "
                             "(= id_dip of Afinidades), speaker_name, party, district, dm_speech (0 for SUMARIO "
                             "and COMENTARIOS), text, n_words, row_n, party_family, ideology (as published), "
                             "nwords_published, reg_party, reg_family, reg_ideology (the speaker's labels in the "
                             "Afinidades register for that legislature). sex is always empty: there is no such "
                             "variable.",
            "deputies": "The Afinidades register as members of the chamber: id_dep, speaker_name, party, "
                        "parliamentary_group (historical party name), district, legislature, start_date, "
                        "end_date (first and last sitting of the legislature), party_family, ideology.",
            "ae_measures": "1 560 measures: id_medida, legislatura, num_sesion, fecha_sesion, fecha_firma, "
                           "diaries_id_inicio (Luz row_n where its text begins), tipo, titulo, tema_principal, "
                           "tema_secundario, n_firmas, n_firmas_ilegibles, id_dip_primer_autor, primer_autor, "
                           "defensa (sí / retirada / no identificada), id_dip_defensor, diaries_id_defensa (Luz "
                           "row_n of the defence), fecha_defensa, texto.",
            "ae_signatures": "One row per signature: id_medida, orden_firma, tipo_fila (firma / firma_ilegible), "
                             "nombre_original, id_dip, partido, familia_partidos, ideologia, truncada.",
            "ae_edges": "Published edge list: id_medida, legislatura, id_dip1 < id_dip2, names, ideologies, truncada.",
            "ae_deputies": "Register: id_dip, legislatura, nombre_completo, partido, partido_historico, "
                           "familia_partidos, ideologia, distrito, nombre_variantes.",
            "ae_metrics": "Published metrics per id_dip and period (a legislature or 'total'): degree, strength, "
                          "closeness, betweenness_pct, eigenvector, z_score, p_coeff, role, influence_score, "
                          "transversality_score, ego and profile measures…",
            "ae_proximity": "Published proximities: kind (party, family, party_weight), period, a, b, value.",
            "ae_party_stats · ae_communities · ae_roles": "Published per-party statistics, communities and roles.",
            "ae_parties · ae_topics": "Dictionaries of parties and of the 13 topics.",
            "ae_checks": "The checks run when the data were loaded (JSON).",
            "lib.libraries · lib.library_items · lib.library_parts": "The user's libraries.",
        },
        "loaded": store.loaded(),
        "examples": [
            "SELECT legislature, count(*) turns, sum(n_words) words FROM interventions WHERE dm_speech = 1 "
            "GROUP BY 1 ORDER BY 1",
            "SELECT tema_principal, count(*) FROM ae_measures GROUP BY 1 ORDER BY 2 DESC",
            "SELECT m.titulo, i.date, i.speaker_raw, left(i.text, 300) FROM ae_measures m JOIN interventions i "
            "ON i.row_n = m.diaries_id_defensa WHERE m.tema_principal = 'agrario' LIMIT 10",
        ],
        "tips": "Never SELECT text without LIMIT. Join measures to speech with interventions.row_n = "
                "ae_measures.diaries_id_inicio (or diaries_id_defensa), and deputies with id_dep = "
                "CAST(id_dip AS VARCHAR).",
    }

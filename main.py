import os
import re
import json
import time
import requests
from datetime import datetime

from db import database as db
from export.export_csv import export_all

from scrapers.dataverse_no_scraper import DataverseNOScraper
from scrapers.icpsr_scraper import ICPSRScraper
from src.license_utils import normalize_license


DB_PATH = "23514826-seeding.db"
SCHEMA_PATH = "db/schema.sql"

DOWNLOADS_ROOT = "downloads"
DATAVERSE_DIR = os.path.join(DOWNLOADS_ROOT, "dataverse-no")
ICPSR_DIR = os.path.join(DOWNLOADS_ROOT, "ICPSR")
EXPORT_DIR = "export_out"


# -------------------------
# Helpers
# -------------------------
def now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def safe_name(s: str) -> str:
    s = (s or "unknown").strip()
    s = s.replace("https://", "").replace("http://", "")
    s = re.sub(r'[<>:"/\\|?*]', "_", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:150]


def file_type_from_name(filename: str) -> str:
    if not filename or "." not in filename:
        return ""
    return filename.split(".")[-1].lower()


def download_file(url: str, out_path: str, timeout: int = 120):
    """
    Returns: (status, local_path, size_bytes)
    status must match DOWNLOAD_RESULT enum:
      SUCCEEDED / FAILED_SERVER_UNRESPONSIVE / FAILED_LOGIN_REQUIRED / FAILED_TOO_LARGE
    """
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    try:
        with requests.get(url, stream=True, timeout=timeout) as r:
            if r.status_code in (401, 403):
                return "FAILED_LOGIN_REQUIRED", None, None
            r.raise_for_status()
            size = 0
            with open(out_path, "wb") as f:
                for chunk in r.iter_content(1024 * 256):
                    if chunk:
                        f.write(chunk)
                        size += len(chunk)
        return "SUCCEEDED", os.path.abspath(out_path), size
    except Exception:
        return "FAILED_SERVER_UNRESPONSIVE", None, None


def write_icpsr_links(doi: str, landing_url: str, title: str) -> str:
    folder = safe_name(doi) if doi else safe_name(title)
    out_dir = os.path.join(ICPSR_DIR, folder)
    os.makedirs(out_dir, exist_ok=True)

    path = os.path.join(out_dir, "links.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"Title: {title}\n")
        f.write(f"DOI: {doi}\n")
        f.write(f"Landing: {landing_url}\n")

    return os.path.abspath(path)


# -------------------------
# Main
# -------------------------
def main():
    # Load configs
    with open("config/data_sources.json", "r", encoding="utf-8") as f:
        sources = json.load(f)["repositories"]

    os.makedirs(DATAVERSE_DIR, exist_ok=True)
    os.makedirs(ICPSR_DIR, exist_ok=True)

    # Init DB
    conn = db.connect(DB_PATH)
    db.init_db(conn, SCHEMA_PATH)

    # Use exact repo IDs and URLs from your sheet
    db.seed_repositories(conn, [
        (6, "dataverse-no", "https://dataverse.no/dataverse.xhtml"),
        (15, "icpsr", "https://icpsr.umich.edu/"),
    ])
    dv_repo_id = 6
    ic_repo_id = 15

    dv_cfg = sources["dataverse_no"]
    ic_cfg = sources["icpsr"]

    # ============================================================
    # Repo 6: DataverseNO
    # ============================================================
    dv_scraper = DataverseNOScraper(
        base_url="https://dataverse.no",
        config_path="config/qda_extensions.json",
        smart_queries_path="config/smart_queries.json"
    )

    # Your example search: .../root/?q=qdpx
    qda_query = "qdpx OR nvpx OR nvp OR atlasproj OR mqda OR mx24 OR NVivo OR MaxQDA OR ATLAS.ti"
    qual_query = "qualitative OR interview OR transcript OR focus group OR coding OR codebook OR thematic analysis"

    print(f"\n=== DataverseNO (QDA_MODE): {qda_query} ===")
    dv_qda = dv_scraper.search(query=qda_query, max_results=200, download_mode="QDA_MODE", max_datasets=60)

    print(f"\n=== DataverseNO (QUAL_MODE): {qual_query} ===")
    dv_qual = dv_scraper.search(query=qual_query, max_results=200, download_mode="QUAL_MODE", max_datasets=60)

    all_dv = dv_qda + dv_qual
    print(f"[DataverseNO] Collected {len(all_dv)} file records")

    for meta in all_dv:
        doi = meta.get("doi", "") or ""
        project_url = meta.get("source_url", "") or ""
        title = meta.get("project_title", "") or doi or "Dataverse dataset"
        description = meta.get("project_description", "") or ""

        # folder must be safe: use DOI or source_id (never full URL)
        source_id = (meta.get("source_id") or "").strip()
        folder = safe_name(doi or source_id or "dataverse_project")
        out_dir = os.path.join(DATAVERSE_DIR, folder)
        os.makedirs(out_dir, exist_ok=True)

        # license normalization to match sheet enum
        lic = normalize_license(meta.get("license_type", ""))

        # Insert project
        project_id = db.insert_project(conn, {
            "query_string": meta.get("query_string", qda_query),
            "repository_id": dv_repo_id,
            "repository_url": "https://dataverse.no/dataverse.xhtml",
            "project_url": project_url,
            "version": "",
            "type": "OTHER_PROJECT",
            "title": title,
            "description": description,
            "language": "",
            "doi": doi,                  # DOI string (or empty if unknown)
            "upload_date": "",
            "download_date": now_iso(),
            "download_repository_folder": "dataverse-no",
            "download_project_folder": folder,
            "download_version_folder": "",
            "download_method": "API-CALL",
        })

        # Download file
        url = meta.get("download_url", "") or ""
        filename = meta.get("filename", "file.bin") or "file.bin"
        out_path = os.path.join(out_dir, safe_name(filename))

        if url:
            status, local_path, size_bytes = download_file(url, out_path)
        else:
            status, local_path, size_bytes = "FAILED_SERVER_UNRESPONSIVE", None, None

        # Insert file
        db.insert_file(conn, {
            "project_id": project_id,
            "file_name": filename,
            "file_type": file_type_from_name(filename),
            "status": status,
            "download_url": url,
            "local_path": local_path,
            "size_bytes": size_bytes,
            "sha256": None
        })

        # Insert aux tables
        db.insert_keywords(conn, project_id, meta.get("keywords", ""))
        db.insert_person_roles(conn, project_id, meta.get("authors", ""), default_role="AUTHOR")
        db.insert_license(conn, project_id, lic)

    print("✅ DataverseNO done.")

    # ============================================================
    # Repo 15: ICPSR (DataCite)
    # ============================================================
    ic_scraper = ICPSRScraper(config_path="config/qda_extensions.json")

    # Your example search: .../search/studies?q=interview
    ic_queries = [
        "interview",
        "qualitative interview",
        "interview transcripts",
        "focus group",
        "thematic analysis",
    ]

    total_ic = 0
    for q in ic_queries:
        print(f"\n=== ICPSR(DataCite): {q} ===")
        results = ic_scraper.search(query=q, max_results=40)

        for meta in results:
            doi = meta.get("doi", "") or ""
            landing = meta.get("download_url", "") or ""
            title = meta.get("project_title", "") or doi or "ICPSR study"
            description = meta.get("project_description", "") or ""

            folder = safe_name(doi or title)
            links_path = write_icpsr_links(doi, landing, title)

            lic = normalize_license(meta.get("license_type", ""))

            project_id = db.insert_project(conn, {
                "query_string": q,
                "repository_id": ic_repo_id,
                "repository_url": "https://icpsr.umich.edu/",
                "project_url": landing,
                "version": "",
                "type": "OTHER_PROJECT",
                "title": title,
                "description": description,
                "language": "",
                "doi": doi,
                "upload_date": "",
                "download_date": now_iso(),
                "download_repository_folder": "ICPSR",
                "download_project_folder": folder,
                "download_version_folder": "",
                "download_method": "API-CALL",
            })

            # Store links.txt as file
            db.insert_file(conn, {
                "project_id": project_id,
                "file_name": "links.txt",
                "file_type": "txt",
                "status": "SUCCEEDED",
                "download_url": landing,
                "local_path": links_path,
                "size_bytes": None,
                "sha256": None
            })

            db.insert_keywords(conn, project_id, meta.get("keywords", ""))
            db.insert_person_roles(conn, project_id, meta.get("authors", ""), default_role="AUTHOR")
            db.insert_license(conn, project_id, lic)

            total_ic += 1

        time.sleep(0.2)

    print(f"✅ ICPSR done. Inserted {total_ic} records.")

    conn.close()

    export_all(DB_PATH, out_dir=EXPORT_DIR)

    print("\nDONE")
    print("DB:", DB_PATH)
    print("Downloads:", DOWNLOADS_ROOT)
    print("CSV:", EXPORT_DIR)


if __name__ == "__main__":
    main()
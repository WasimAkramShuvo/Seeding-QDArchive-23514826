# Seeding QDArchive — Part 1: Data Acquisition (Repo 6 + 15)

Student ID: **23514826**  
Course: **Seeding QDArchive (SQ26)**  
Part: **1 — Data Acquisition Pipeline**

This repository implements the **Part 1** pipeline:

✅ Find qualitative/QDA-related research projects  
✅ Download files (where available) / store links (where needed)  
✅ Store structured metadata in a **SQLite database**  
✅ Export all metadata tables to **CSV**

Assigned repositories:
- **Repo 6:** DataverseNO — https://dataverse.no/dataverse.xhtml  
- **Repo 15:** ICPSR — https://icpsr.umich.edu/

---

## Overview

### Repo 6 — DataverseNO (downloads files)
The pipeline searches and downloads datasets from **DataverseNO** using two query modes:
- **QDA_MODE**: searches for QDA/CAQDAS-related signals (e.g., `qdpx`, `nvpx`, `atlasproj`, `mx24`, etc.)
- **QUAL_MODE**: searches for qualitative signals (e.g., `interview`, `transcript`, `focus group`, etc.)

For each dataset:
- metadata is inserted into the SQLite DB
- files are downloaded into `downloads/dataverse-no/<dataset-folder>/`
- file download status is recorded in the DB

### Repo 15 — ICPSR (links.txt per record)
ICPSR web pages are sometimes blocked/JS-heavy, so discovery is implemented via **DataCite** (client-id `gesis.icpsr`).
For each discovered record:
- a folder is created under `downloads/ICPSR/<record-folder>/`
- a `links.txt` file is stored (Title, DOI, Landing URL)
- the record is inserted into the SQLite DB as a project + file entry

> License fields may be missing for some ICPSR records; in that case the pipeline stores `UNKNOWN`.

---

## Project Structure

```text
Seeding-QDArchive-23514826/
├─ config/
│  ├─ data_sources.json        # Repository list + base URLs
│  ├─ qda_extensions.json      # QDA file extensions + software mapping
│  └─ smart_queries.json       # Query presets used in search
│
├─ db/
│  ├─ schema.sql               # SQLite schema
│  └─ database.py              # DB helper functions (insert helpers)
│
├─ downloads/                  # Downloaded data (NOT committed to GitHub)
│  ├─ dataverse-no/
│  │  └─ <dataset-folder>/
│  │     └─ <downloaded files...>
│  └─ ICPSR/
│     └─ <record-folder>/
│        └─ links.txt
│
├─ export/
│  └─ export_csv.py            # Export all DB tables to CSV
│
├─ export_out/                 # CSV outputs (optional to commit)
│  ├─ repositories.csv
│  ├─ projects.csv
│  ├─ files.csv
│  ├─ keywords.csv
│  ├─ person_role.csv
│  └─ licenses.csv
│
├─ pipeline/
│  └─ downloader.py            # File downloader (handles statuses)
│
├─ scrapers/
│  ├─ __init__.py
│  ├─ base_scraper.py          # Base scraper class + shared helpers
│  ├─ dataverse_no_scraper.py  # Repo 6: DataverseNO (API)
│  └─ icpsr_scraper.py         # Repo 15: ICPSR (DataCite discovery + links.txt)
│
├─ src/
│  ├─ license_utils.py         # License parsing helpers / normalization
│  └─ search_utils.py          # Search helpers (queries, safe folder names, etc.)
│
├─ .gitignore                  # Ignores downloads/ and cache files
├─ 23514826-seeding.db         # Main deliverable: metadata DB
├─ main.py                     # Entry point: runs the pipeline
└─ requirements.txt            # Python dependencies
```
---

## Setup & Run

### 1) Create and activate a virtual environment (recommended)

**Windows PowerShell**

```bash
python -m venv .venv
.\.venv\Scripts\activate
```
### 2) Install dependencies

```bash
pip install -r requirements.txt
```
### 3) Run the pipeline

```bash
python main.py
```
### The run will:

- update/create 23514826-seeding.db
- write downloaded files + ICPSR links.txt folders into downloads/
- export database tables to CSV in export_out/

## Outputs
### Downloads folder
- DataverseNO: downloads/dataverse-no/<dataset-folder>/...
- ICPSR: downloads/ICPSR/<record-folder>/links.txt

### Example `links.txt`:
```bash
Title: <title>
DOI: <doi>
Landing: <url>
```

## SQLite database

- 23514826-seeding.db (in repo root)

### Why `downloads/` is not pushed to GitHub

Downloaded files can be large, so the repo uses .gitignore to exclude:

- `downloads/`
- Python cache (`__pycache__`, `*.pyc`)

## Downloads link (FAUbox)

Downloaded files are not committed to GitHub (too large).  
You can access the full `downloads/` folder here:

- FAUbox: <https://faubox.rrze.uni-erlangen.de/getlink/fi8si2zYWRfJfUi17TjhjH/>
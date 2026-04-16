import sqlite3
from datetime import datetime
from typing import Any, Dict, Optional, Iterable, Tuple


# -----------------------
# Helpers
# -----------------------
def now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def init_db(conn: sqlite3.Connection, schema_path: str) -> None:
    with open(schema_path, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.commit()


# -----------------------
# Repositories
# -----------------------
def seed_repositories(conn: sqlite3.Connection, rows: Iterable[Tuple[int, str, str]]) -> None:
    """
    rows: [(id, name, url), ...]
    Example:
      [(6,'dataverse-no','https://dataverse.no'), (15,'icpsr','https://icpsr.umich.edu')]
    """
    conn.executemany(
        "INSERT OR IGNORE INTO repositories(id, name, url) VALUES(?,?,?)",
        list(rows)
    )
    conn.commit()


# -----------------------
# Projects
# -----------------------
def insert_project(conn: sqlite3.Connection, row: Dict[str, Any]) -> int:
    """
    Insert one project row (no upsert to keep it simple & aligned with sheet).
    Return project_id.
    """
    cur = conn.execute(
        """
        INSERT INTO projects(
          query_string, repository_id, repository_url, project_url,
          version, type, title, description, language, doi,
          upload_date, download_date,
          download_repository_folder, download_project_folder, download_version_folder,
          download_method
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            row.get("query_string"),
            row["repository_id"],
            row.get("repository_url"),
            row.get("project_url"),

            row.get("version"),
            row.get("type"),  # QDA_PROJECT/QD_PROJECT/OTHER_PROJECT/NOT_A_PROJECT

            row.get("title"),
            row.get("description"),
            row.get("language"),
            row.get("doi"),

            row.get("upload_date"),
            row.get("download_date"),

            row.get("download_repository_folder"),
            row.get("download_project_folder"),
            row.get("download_version_folder"),

            row.get("download_method"),  # SCRAPING / API-CALL
        )
    )
    conn.commit()
    return int(cur.lastrowid)


# -----------------------
# Files
# -----------------------
def insert_file(conn: sqlite3.Connection, row: Dict[str, Any]) -> int:
    """
    row: project_id, file_name, file_type, status
    """
    cur = conn.execute(
        """
        INSERT INTO files(
          project_id, file_name, file_type, status,
          download_url, local_path, size_bytes, sha256
        ) VALUES (?,?,?,?,?,?,?,?)
        """,
        (
            row["project_id"],
            row.get("file_name"),
            row.get("file_type"),
            row.get("status"),

            row.get("download_url"),
            row.get("local_path"),
            row.get("size_bytes"),
            row.get("sha256"),
        )
    )
    conn.commit()
    return int(cur.lastrowid)


# -----------------------
# Keywords / People / License
# -----------------------
def insert_keywords(conn: sqlite3.Connection, project_id: int, keywords: str) -> None:
    """
    keywords: semicolon separated string
    """
    if not keywords:
        return
    rows = [(project_id, k.strip()) for k in keywords.split(";") if k.strip()]
    conn.executemany("INSERT INTO keywords(project_id, keyword) VALUES(?,?)", rows)
    conn.commit()


def insert_person_roles(conn: sqlite3.Connection, project_id: int, authors: str, default_role: str = "AUTHOR") -> None:
    """
    authors: semicolon separated string
    """
    if not authors:
        return
    rows = [(project_id, p.strip(), default_role) for p in authors.split(";") if p.strip()]
    conn.executemany("INSERT INTO person_role(project_id, name, role) VALUES(?,?,?)", rows)
    conn.commit()


def insert_license(conn: sqlite3.Connection, project_id: int, lic: str) -> None:
    """
    Always insert something.
    If empty -> UNKNOWN (allowed by sheet as "we'll fix later")
    """
    if not lic or not str(lic).strip():
        lic = "UNKNOWN"
    conn.execute("INSERT INTO licenses(project_id, license) VALUES(?,?)", (project_id, lic))
    conn.commit()
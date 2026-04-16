PRAGMA foreign_keys=ON;

-- -----------------------
-- ENUM-like constraints
-- -----------------------
-- SQLite doesn't have enums, so we use TEXT + CHECK constraints.
-- If you want "accept anything", remove CHECK clauses.

CREATE TABLE IF NOT EXISTS repositories (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  url TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS projects (
  id INTEGER PRIMARY KEY AUTOINCREMENT,

  query_string TEXT,
  repository_id INTEGER NOT NULL,
  repository_url TEXT,
  project_url TEXT,

  version TEXT,
  type TEXT CHECK(type IN ('QDA_PROJECT','QD_PROJECT','OTHER_PROJECT','NOT_A_PROJECT')),

  title TEXT,
  description TEXT,
  language TEXT,     -- BCP47 (store as text, validate later)
  doi TEXT,          -- DOI URL

  upload_date TEXT,  -- DATE (YYYY-MM-DD)
  download_date TEXT, -- TIMESTAMP (ISO string)

  download_repository_folder TEXT,
  download_project_folder TEXT,
  download_version_folder TEXT,
  download_method TEXT CHECK(download_method IN ('SCRAPING','API-CALL')),

  FOREIGN KEY(repository_id) REFERENCES repositories(id)
);

CREATE TABLE IF NOT EXISTS files (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id INTEGER NOT NULL,

  file_name TEXT,
  file_type TEXT,  -- extension lowercase, no dot
  status TEXT CHECK(status IN (
    'SUCCEEDED',
    'FAILED_SERVER_UNRESPONSIVE',
    'FAILED_LOGIN_REQUIRED',
    'FAILED_TOO_LARGE'
  )),

  -- optional helpers (not in sheet, but helpful)
  download_url TEXT,
  local_path TEXT,
  size_bytes INTEGER,
  sha256 TEXT,

  FOREIGN KEY(project_id) REFERENCES projects(id)
);

CREATE TABLE IF NOT EXISTS keywords (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id INTEGER NOT NULL,
  keyword TEXT,
  FOREIGN KEY(project_id) REFERENCES projects(id)
);

CREATE TABLE IF NOT EXISTS person_role (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id INTEGER NOT NULL,
  name TEXT,
  role TEXT CHECK(role IN ('UPLOADER','AUTHOR','OWNER','OTHER','UNKNOWN')),
  FOREIGN KEY(project_id) REFERENCES projects(id)
);

CREATE TABLE IF NOT EXISTS licenses (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id INTEGER NOT NULL,
  license TEXT,
  FOREIGN KEY(project_id) REFERENCES projects(id)
);

-- Helpful indexes
CREATE INDEX IF NOT EXISTS idx_projects_repo ON projects(repository_id);
CREATE INDEX IF NOT EXISTS idx_files_project ON files(project_id);
import os
import sqlite3
import csv

TABLES = ["repositories", "projects", "files", "keywords", "person_role", "licenses"]

def export_all(db_path: str, out_dir: str = "export_out") -> None:
    os.makedirs(out_dir, exist_ok=True)
    conn = sqlite3.connect(db_path)
    for t in TABLES:
        cur = conn.execute(f"SELECT * FROM {t}")
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()
        with open(os.path.join(out_dir, f"{t}.csv"), "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(cols)
            w.writerows(rows)
    conn.close()
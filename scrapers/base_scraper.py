import json
import os
from typing import Dict, Any, Optional


class BaseScraper:
    def __init__(self, config_path: str, smart_queries_path: Optional[str] = None):
        self.config_path = config_path
        self.smart_queries_path = smart_queries_path
        self.results = []

        self.qda_config = self._load_json(config_path) if config_path else {}
        self.smart_queries = self._load_json(smart_queries_path) if smart_queries_path else {}

        # collect all extensions from qda_extensions.json
        self.all_extensions = set()
        try:
            all_ext = self.qda_config.get("all_extensions", [])
            for e in all_ext:
                self.all_extensions.add(e.lower().lstrip("."))
        except Exception:
            pass

    def _load_json(self, path: Optional[str]) -> Dict[str, Any]:
        if not path or not os.path.exists(path):
            return {}
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def clear_results(self) -> None:
        self.results = []

    def file_extension(self, filename: str) -> str:
        if not filename or "." not in filename:
            return ""
        return filename.split(".")[-1].lower()

    def is_qda_file(self, filename: str) -> bool:
        ext = self.file_extension(filename).lower().lstrip(".")
        return ext in self.all_extensions

    def get_qda_software(self, filename: str) -> str:
        ext = self.file_extension(filename).lower()
        # very light mapping (optional)
        if ext in ("qdpx", "qdc"):
            return "REFI-QDA"
        if ext in ("nvpx", "nvp"):
            return "NVivo"
        if ext in ("atlasproj", "hpr7"):
            return "ATLAS.ti"
        if ext in ("mx24", "mx23", "mx22", "mx20", "mqda", "mqd"):
            return "MaxQDA"
        return ""

    def normalize_metadata(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        # ✅ IMPORTANT: keep license_type
        return {
            "query_string": raw.get("query_string", ""),

            "filename": raw.get("filename", ""),
            "file_extension": raw.get("file_extension", ""),
            "file_size": raw.get("file_size"),
            "download_url": raw.get("download_url", ""),

            "source_repository": raw.get("source_repository", ""),
            "source_url": raw.get("source_url", ""),
            "source_id": raw.get("source_id", ""),

            "license_type": raw.get("license_type", ""),

            "project_title": raw.get("project_title", ""),
            "project_description": raw.get("project_description", ""),
            "authors": raw.get("authors", ""),
            "publication_date": raw.get("publication_date", ""),
            "keywords": raw.get("keywords", ""),
            "doi": raw.get("doi", ""),

            "qda_software": raw.get("qda_software", ""),
            "is_qda_file": bool(raw.get("is_qda_file", False)),
        }
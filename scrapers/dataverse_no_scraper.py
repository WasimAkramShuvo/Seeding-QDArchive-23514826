import time
import requests
from typing import List, Dict, Any, Optional

from .base_scraper import BaseScraper


class DataverseNOScraper(BaseScraper):
    def __init__(
        self,
        base_url: str = "https://dataverse.no",
        config_path: str = "config/qda_extensions.json",
        smart_queries_path: str = "config/smart_queries.json",
    ):
        super().__init__(config_path, smart_queries_path)
        self.base_url = base_url.rstrip("/")
        self.api_base = f"{self.base_url}/api"
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "QDA-Archive-Bot/1.0"})

    def search(
        self,
        query: Optional[str] = None,
        max_results: int = 200,
        download_mode: str = "QDA_MODE",
        max_datasets: int = 80
    ) -> List[Dict[str, Any]]:
        self.clear_results()
        term = query or "qualitative"

        dataset_ids = self._search_datasets(term, max_datasets=max_datasets)

        total = 0
        for dsid in dataset_ids:
            if total >= max_results:
                break

            if download_mode == "QDA_MODE":
                metas = self._get_dataset_files_if_qda_present(dsid, query_string=term)
            else:
                metas = self._get_dataset_files_all(dsid, query_string=term)

            for m in metas:
                self.results.append(m)
                total += 1
                if total >= max_results:
                    break

            time.sleep(0.2)

        return self.results

    # -------------------- API helpers --------------------
    def _search_datasets(self, term: str, max_datasets: int = 80) -> List[str]:
        out = []
        start = 0
        per_page = 25

        while len(out) < max_datasets:
            resp = self.session.get(
                f"{self.api_base}/search",
                params={"q": term, "type": "dataset", "start": start, "per_page": per_page},
                timeout=60
            )
            resp.raise_for_status()
            data = resp.json()
            items = (data.get("data") or {}).get("items") or []
            if not items:
                break

            for it in items:
                gid = it.get("global_id") or it.get("globalId") or it.get("entity_id")
                if gid:
                    out.append(gid)
                if len(out) >= max_datasets:
                    break

            start += per_page
            time.sleep(0.15)

        # unique keep order
        seen, uniq = set(), []
        for x in out:
            if x not in seen:
                uniq.append(x)
                seen.add(x)
        return uniq

    def _get_dataset(self, dataset_pid: str) -> Dict[str, Any]:
        resp = self.session.get(
            f"{self.api_base}/datasets/:persistentId/",
            params={"persistentId": dataset_pid},
            timeout=60
        )
        resp.raise_for_status()
        j = resp.json()
        if j.get("status") != "OK":
            return {}
        return j.get("data") or {}

    # -------------------- extraction --------------------
    def _extract_persistent_id(self, dataset: Dict[str, Any]) -> str:
        latest = dataset.get("latestVersion") or {}
        pid = (
            dataset.get("persistentId")
            or dataset.get("globalId")
            or dataset.get("global_id")
            or latest.get("datasetPersistentId")
            or dataset.get("persistentUrl")
            or ""
        )
        if "doi.org/" in pid:
            pid = pid.split("doi.org/")[-1]
        return pid

    def _extract_license(self, dataset: Dict[str, Any]) -> str:
        """
        IMPORTANT:
        Dataverse often stores license in latestVersion.license (dict) – same as other student's code.
        If missing, fallback to termsOfUse.
        """
        latest = dataset.get("latestVersion") or {}

        lic_obj = latest.get("license")
        if isinstance(lic_obj, dict):
            # typical keys: name, uri
            name = (lic_obj.get("name") or "").strip()
            uri = (lic_obj.get("uri") or "").strip()
            if name:
                return name
            if uri:
                return uri

        # fallback: terms of use
        terms = (dataset.get("termsOfUse") or "").strip()
        if terms:
            return terms

        terms2 = (latest.get("termsOfUse") or "").strip()
        if terms2:
            return terms2

        return "UNKNOWN"

    def _extract_citation(self, dataset: Dict[str, Any]) -> Dict[str, str]:
        latest = dataset.get("latestVersion") or {}
        fields = (((latest.get("metadataBlocks") or {}).get("citation") or {}).get("fields")) or []

        title, desc, authors, keywords = "", "", "", ""

        for f in fields:
            if f.get("typeName") == "title":
                title = f.get("value", "") or ""

        for f in fields:
            if f.get("typeName") == "dsDescription":
                v = f.get("value", [])
                if v:
                    desc = v[0].get("dsDescriptionValue", {}).get("value", "") or ""

        for f in fields:
            if f.get("typeName") == "author":
                v = f.get("value", [])
                authors = "; ".join(a.get("authorName", {}).get("value", "") for a in v if a.get("authorName"))
                break

        for f in fields:
            if f.get("typeName") == "keyword":
                v = f.get("value", [])
                keywords = "; ".join(k.get("keywordValue", {}).get("value", "") for k in v if k.get("keywordValue"))
                break

        return {"title": title, "desc": desc, "authors": authors, "keywords": keywords}

    def _get_dataset_files_if_qda_present(self, dataset_pid: str, query_string: str) -> List[Dict[str, Any]]:
        dataset = self._get_dataset(dataset_pid)
        if not dataset:
            return []
        latest = dataset.get("latestVersion") or {}
        files = latest.get("files") or []

        has_qda = any(self.is_qda_file((fi.get("dataFile") or {}).get("filename", "")) for fi in files)
        if not has_qda:
            return []
        return [self._build_file_metadata(fi, dataset, query_string) for fi in files]

    def _get_dataset_files_all(self, dataset_pid: str, query_string: str) -> List[Dict[str, Any]]:
        dataset = self._get_dataset(dataset_pid)
        if not dataset:
            return []
        latest = dataset.get("latestVersion") or {}
        files = latest.get("files") or []
        return [self._build_file_metadata(fi, dataset, query_string) for fi in files]

    def _build_file_metadata(self, fi: Dict[str, Any], dataset: Dict[str, Any], query_string: str) -> Dict[str, Any]:
        latest = dataset.get("latestVersion") or {}

        doi = self._extract_persistent_id(dataset)
        cit = self._extract_citation(dataset)
        lic = self._extract_license(dataset)

        df = fi.get("dataFile") or {}
        filename = df.get("filename", "")
        file_id = df.get("id")
        ext = self.file_extension(filename)

        download_url = f"{self.api_base}/access/datafile/{file_id}" if file_id else ""
        source_url = f"{self.base_url}/dataset.xhtml?persistentId={doi}" if doi else ""

        return self.normalize_metadata({
            "query_string": query_string,
            "filename": filename,
            "file_extension": ext,
            "file_size": df.get("filesize"),
            "download_url": download_url,

            "source_repository": "dataverse-no",
            "source_url": source_url,
            "source_id": str(file_id) if file_id else doi,

            "license_type": lic,

            "project_title": cit["title"],
            "project_description": cit["desc"],
            "authors": cit["authors"],
            "publication_date": latest.get("releaseTime", "") or "",
            "keywords": cit["keywords"],

            "doi": doi,
            "qda_software": self.get_qda_software(filename),
            "is_qda_file": self.is_qda_file(filename),
        })
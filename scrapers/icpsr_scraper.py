import time
import requests
from typing import List, Dict, Any, Optional

from .base_scraper import BaseScraper


class ICPSRScraper(BaseScraper):
    """
    ICPSR scraper via DataCite API (reliable).
    Uses client-id=gesis.icpsr, resource-type=dataset.
    Extracts license from rightsList if present.
    """

    DATACITE_URL = "https://api.datacite.org/dois"
    CLIENT_ID = "gesis.icpsr"
    PAGE_SIZE = 50

    def __init__(self, config_path: str = "config/qda_extensions.json"):
        super().__init__(config_path, "config/smart_queries.json")
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "QDA-Archive-Bot/1.0 (Research Data Collection)",
            "Accept": "application/json"
        })

    def search(self, query: Optional[str] = None, max_results: int = 200) -> List[Dict[str, Any]]:
        self.clear_results()

        q = query or "qualitative"
        page = 1

        while len(self.results) < max_results:
            params = {
                "client-id": self.CLIENT_ID,
                "query": q,
                "page[size]": self.PAGE_SIZE,
                "page[number]": page,
                "resource-type-id": "dataset",
            }

            try:
                resp = self.session.get(self.DATACITE_URL, params=params, timeout=60)
                resp.raise_for_status()
                data = resp.json()

                items = data.get("data", [])
                if not items:
                    break

                for item in items:
                    if len(self.results) >= max_results:
                        break
                    self.results.append(self._build_metadata(item, q))

                if not data.get("links", {}).get("next"):
                    break

                page += 1
                time.sleep(0.25)

            except requests.RequestException as e:
                print(f"[ICPSR/DataCite] Error: {e}")
                break

        return self.results

    def _build_metadata(self, item: Dict[str, Any], query_string: str) -> Dict[str, Any]:
        attrs = item.get("attributes", {})
        doi = attrs.get("doi", "")
        landing_url = attrs.get("url", f"https://doi.org/{doi}" if doi else "")

        titles = attrs.get("titles", [])
        title = titles[0].get("title", "") if titles else ""

        creators = attrs.get("creators", [])
        authors = "; ".join(
            c.get("name", "") or f"{c.get('givenName','')} {c.get('familyName','')}".strip()
            for c in creators
            if (c.get("name") or c.get("givenName") or c.get("familyName"))
        )

        subjects = attrs.get("subjects", [])
        keywords = "; ".join(s.get("subject", "") for s in subjects if s.get("subject"))

        descriptions = attrs.get("descriptions", [])
        description = descriptions[0].get("description", "") if descriptions else ""

        rights = attrs.get("rightsList", [])
        license_name = rights[0].get("rights", "") if rights else ""
        license_url = rights[0].get("rightsUri", "") if rights else ""

        license_type = license_name or license_url or "UNKNOWN"

        pub_year = str(attrs.get("publicationYear", "") or "")

        return self.normalize_metadata({
            "query_string": query_string,

            "filename": "links.txt",
            "file_extension": "txt",
            "file_size": None,
            "download_url": landing_url,

            "source_repository": "icpsr",
            "source_url": landing_url,
            "source_id": doi or landing_url,

            "license_type": license_type,

            "project_title": title,
            "project_description": description,
            "authors": authors,
            "publication_date": pub_year,
            "keywords": keywords,
            "doi": doi,
            "qda_software": "",
            "is_qda_file": False
        })
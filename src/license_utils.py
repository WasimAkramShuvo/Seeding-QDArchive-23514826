import re

CANON = {
    "CC BY": ["cc by", "cc-by", "creativecommons attribution", "creativecommons.org/licenses/by"],
    "CC BY-SA": ["cc by-sa", "cc-by-sa", "creativecommons.org/licenses/by-sa"],
    "CC BY-NC": ["cc by-nc", "cc-by-nc", "creativecommons.org/licenses/by-nc"],
    "CC BY-ND": ["cc by-nd", "cc-by-nd", "creativecommons.org/licenses/by-nd"],
    "CC BY-NC-ND": ["cc by-nc-nd", "cc-by-nc-nd", "creativecommons.org/licenses/by-nc-nd"],
    "CC0": ["cc0", "public domain dedication", "creativecommons.org/publicdomain/zero"],
    "ODbL": ["odbl", "open database license"],
    "ODbL-1.0": ["odbl-1.0"],
    "ODC-By": ["odc-by", "opendatacommons attribution"],
    "ODC-By-1.0": ["odc-by-1.0"],
    "PDDL": ["pddl", "opendatacommons.org/licenses/pddl"],
}

def normalize_license(raw: str) -> str:
    if not raw or not str(raw).strip():
        return "UNKNOWN"

    s = str(raw).strip()
    low = s.lower()

    # remove version numbers like "4.0"
    low = re.sub(r"\b\d+(\.\d+)?\b", "", low).strip()

    for canon, patterns in CANON.items():
        for p in patterns:
            if p in low:
                return canon

    # keep original string if not recognized (allowed by sheet)
    return s
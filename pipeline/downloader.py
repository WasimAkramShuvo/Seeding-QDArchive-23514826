import os
import hashlib
import requests

SUCCEEDED = "SUCCEEDED"
FAILED_SERVER_UNRESPONSIVE = "FAILED_SERVER_UNRESPONSIVE"
FAILED_LOGIN_REQUIRED = "FAILED_LOGIN_REQUIRED"
FAILED_TOO_LARGE = "FAILED_TOO_LARGE"

def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)

def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def download(session: requests.Session, url: str, out_path: str, max_bytes: int = 1_500_000_000, timeout: int = 120):
    ensure_dir(os.path.dirname(out_path))
    tmp = out_path + ".part"
    try:
        with session.get(url, stream=True, timeout=timeout, allow_redirects=True) as r:
            if r.status_code in (401, 403):
                return FAILED_LOGIN_REQUIRED, None, None, None, f"HTTP {r.status_code}"
            if r.status_code >= 500:
                return FAILED_SERVER_UNRESPONSIVE, None, None, None, f"HTTP {r.status_code}"
            r.raise_for_status()

            total = 0
            with open(tmp, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024 * 256):
                    if not chunk:
                        continue
                    total += len(chunk)
                    if total > max_bytes:
                        try:
                            f.close()
                            os.remove(tmp)
                        except Exception:
                            pass
                        return FAILED_TOO_LARGE, None, total, None, "File too large"
                    f.write(chunk)

        os.replace(tmp, out_path)
        sha = sha256_file(out_path)
        return SUCCEEDED, os.path.abspath(out_path), total, sha, None

    except Exception as e:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass
        return FAILED_SERVER_UNRESPONSIVE, None, None, None, str(e)
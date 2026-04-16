"""Shared helpers for repository search scripts."""

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Union


DEFAULT_CONFIG_DIR = Path(__file__).resolve().parent.parent / 'config'


def _resolve_config_dir(config_dir: Optional[Union[str, Path]] = None) -> Path:
    """Resolve the repository config directory."""
    return Path(config_dir) if config_dir is not None else DEFAULT_CONFIG_DIR


def _unique_nonempty(values: Iterable[Any]) -> List[str]:
    """Return unique, non-empty string values while preserving order."""
    unique_values = []
    seen = set()

    for value in values:
        normalized = str(value).strip() if value is not None else ''
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        unique_values.append(normalized)

    return unique_values


def load_qda_extensions(config_dir: Optional[Union[str, Path]] = None) -> List[str]:
    """Load QDA file extensions from config and strip leading dots."""
    resolved_config_dir = _resolve_config_dir(config_dir)
    with open(resolved_config_dir / 'qda_extensions.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    raw_extensions = data.get('all_extensions')
    if not isinstance(raw_extensions, list):
        raw_extensions = []
        for info in data.get('qda_software', {}).values():
            if isinstance(info, dict):
                raw_extensions.extend(info.get('extensions', []))

    return _unique_nonempty(str(ext).lstrip('.') for ext in raw_extensions)


def load_smart_queries(
    config_dir: Optional[Union[str, Path]] = None,
    include_multilingual: bool = True,
) -> List[str]:
    """Load smart queries from config, including nested multilingual terms."""
    resolved_config_dir = _resolve_config_dir(config_dir)
    with open(resolved_config_dir / 'smart_queries.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    queries = []
    for content in data.values():
        if isinstance(content, dict) and isinstance(content.get('queries'), list):
            queries.extend(content['queries'])

    if include_multilingual:
        multilingual_terms = data.get('multilingual_terms', {})
        if isinstance(multilingual_terms, dict):
            for language, terms in multilingual_terms.items():
                if language == 'description':
                    continue
                if isinstance(terms, list):
                    queries.extend(terms)

    return _unique_nonempty(queries)


def load_all_queries(
    config_dir: Optional[Union[str, Path]] = None,
    include_multilingual: bool = True,
) -> List[str]:
    """Load all search queries used by repository scripts."""
    return _unique_nonempty(
        [
            *load_qda_extensions(config_dir=config_dir),
            *load_smart_queries(
                config_dir=config_dir,
                include_multilingual=include_multilingual,
            ),
        ]
    )


def get_result_identity(result: Dict[str, Any]) -> str:
    """Return a stable file-level identity for a search result."""
    source_repository = result.get('source_repository') or ''
    download_url = result.get('download_url') or ''
    source_id = result.get('source_id') or ''
    filename = result.get('filename') or ''
    source_url = result.get('source_url') or ''

    if download_url:
        return f"{source_repository}|download|{download_url}"
    if source_id and filename:
        return f"{source_repository}|source|{source_id}|{filename}"
    if source_url and filename:
        return f"{source_repository}|page|{source_url}|{filename}"
    return f"{source_repository}|fallback|{source_id or source_url or filename}"


def save_results(db, results: Iterable[Dict[str, Any]], log_prefix: str = "[SAVE]", max_error_logs: int = 5) -> int:
    """Save results to the database and report insert failures visibly."""
    saved = 0
    duplicate_count = 0
    error_count = 0

    for result in results:
        try:
            file_id = db.insert_file(result)
            if file_id is None:
                duplicate_count += 1
            else:
                saved += 1
        except Exception as e:
            error_count += 1
            if error_count <= max_error_logs:
                print(f"{log_prefix} Insert failed for {result.get('filename', '<unknown>')}: {e}")

    if duplicate_count:
        print(f"{log_prefix} Duplicate rows skipped: {duplicate_count}")

    if error_count > max_error_logs:
        print(f"{log_prefix} Additional insert errors suppressed: {error_count - max_error_logs}")

    return saved
"""Small shared helpers."""

import re


def slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "untitled"


def safe_filename(filename: str) -> str:
    """Strip directories and unsafe characters from an uploaded filename."""
    name = filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    return re.sub(r"[^A-Za-z0-9._-]", "_", name)

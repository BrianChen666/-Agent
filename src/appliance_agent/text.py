from __future__ import annotations

import re
from collections.abc import Iterable


FAULT_CODE_RE = re.compile(r"(?<![A-Za-z])(E\d{1,2}|F\d{1,2}|PF|LE|CL)(?![A-Za-z0-9])", re.I)
MODEL_RE = re.compile(r"(?<![A-Za-z0-9])(X100|X200|W80)(?![A-Za-z0-9])", re.I)


def normalize_code(value: str | None) -> str | None:
    if not value:
        return None
    return value.upper()


def extract_fault_code(text: str) -> str | None:
    match = FAULT_CODE_RE.search(text)
    return match.group(1).upper() if match else None


def extract_model(text: str) -> str | None:
    match = MODEL_RE.search(text)
    return match.group(1).upper() if match else None


def slugify(text: str) -> str:
    ascii_text = re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-").lower()
    return ascii_text or str(abs(hash(text)) % 100000)


def tokenize(text: str) -> list[str]:
    text = text.upper()
    raw_tokens = re.findall(r"[A-Z]+\d*|\d+|[\u4e00-\u9fff]+", text)
    tokens: list[str] = []
    for token in raw_tokens:
        tokens.append(token)
        if re.fullmatch(r"[\u4e00-\u9fff]+", token):
            tokens.extend(token[i : i + 2] for i in range(max(len(token) - 1, 0)))
            tokens.extend(token[i : i + 3] for i in range(max(len(token) - 2, 0)))
    return [token for token in tokens if token]


def unique_preserve_order(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result

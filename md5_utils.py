"""Utility helpers for computing and mutating MD5 digests."""
from __future__ import annotations

import hashlib
import random
import string
from pathlib import Path

CHUNK_SIZE = 1024 * 1024


def compute_md5(path: Path) -> str:
    """Compute the MD5 hash of a file."""
    md5 = hashlib.md5()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(CHUNK_SIZE)
            if not chunk:
                break
            md5.update(chunk)
    return md5.hexdigest()


def mutate_file(path: Path) -> None:
    """Mutate a file slightly so that its MD5 changes."""
    token = "\n#" + "".join(
        random.choices(string.ascii_letters + string.digits, k=16)
    ) + "\n"
    with path.open("ab") as handle:
        handle.write(token.encode("utf-8"))

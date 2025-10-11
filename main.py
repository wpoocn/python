"""MD5 modification utility with optional PySide6 GUI."""
from __future__ import annotations

from pathlib import Path
from typing import List

from md5_utils import compute_md5, mutate_file

__all__ = ["compute_md5", "mutate_file", "add_files", "main"]


def add_files(paths: List[str]) -> List[Path]:
    """Resolve a list of file paths, skipping duplicates and non-files."""
    resolved: list[Path] = []
    seen: set[str] = set()
    for raw_path in paths:
        path = Path(raw_path).resolve()
        if not path.is_file():
            continue
        str_path = str(path)
        if str_path in seen:
            continue
        seen.add(str_path)
        resolved.append(path)
    return resolved


def main() -> None:
    """Launch the PySide6 GUI if the dependency is available."""
    from md5_gui import run_app

    run_app()


if __name__ == "__main__":
    main()

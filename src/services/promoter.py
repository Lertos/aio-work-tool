"""Copy/move files for the Promoter tab (replaces the ``cmd.exe /c copy|move`` calls).

Two path styles, same as the Java version:

* FILE_NAMES_SEPARATE - origins and destinations are folders; every file name
  is copied from every origin folder to every destination folder.
* FILE_NAMES_IN_PATHS - origins are full file paths; a destination is either
  a folder (keep the file name) or a full target file path.

Differences from Java:

* Existing destination files are overwritten (promoting means replacing).
* MOVE to several destinations works: the file is copied to all but the last
  destination, then moved there. Previously ``move`` ran once per destination
  and every run after the first failed because the source was already gone.
* Every failure is collected and reported instead of silently ignored.
"""
from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path

from ..model.items import PathType, PromoteItem, PromoteType


@dataclass
class PromoteResult:
    promoted: list[tuple[Path, Path]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def plan(item: PromoteItem) -> list[tuple[Path, Path]]:
    """Every (source file, target file) pair the promotion will touch, in order."""
    pairs: list[tuple[Path, Path]] = []
    if item.path_type is PathType.FILE_NAMES_SEPARATE:
        for origin in item.origin_paths:
            for name in item.file_names:
                for dest in item.destination_paths:
                    pairs.append((Path(origin) / name, Path(dest) / name))
    else:
        for origin in item.origin_paths:
            src = Path(origin)
            for dest in item.destination_paths:
                target = Path(dest)
                pairs.append((src, target / src.name if target.is_dir() else target))
    return pairs


def validate(item: PromoteItem) -> list[str]:
    """Problems that would stop the promotion; empty list means OK to run."""
    problems: list[str] = []
    if not item.origin_paths:
        problems.append("No origin paths given")
    if not item.destination_paths:
        problems.append("No destination paths given")

    if item.path_type is PathType.FILE_NAMES_SEPARATE:
        if not item.file_names:
            problems.append("No file names given")
        for origin in item.origin_paths:
            if not Path(origin).is_dir():
                problems.append(f"Origin folder does not exist: {origin}")
                continue
            for name in item.file_names:
                if not (Path(origin) / name).is_file():
                    problems.append(f"Origin file does not exist: {Path(origin) / name}")
        for dest in item.destination_paths:
            if not Path(dest).is_dir():
                problems.append(f"Destination folder does not exist: {dest}")
    else:
        for origin in item.origin_paths:
            if not Path(origin).is_file():
                problems.append(f"Origin file does not exist: {origin}")
        for dest in item.destination_paths:
            path = Path(dest)
            if not (path.is_dir() or path.parent.is_dir()):
                problems.append(f"Destination folder does not exist: {path.parent}")
    return problems


def promote(item: PromoteItem) -> PromoteResult:
    result = PromoteResult()
    pairs = plan(item)
    last_use = {src: i for i, (src, _) in enumerate(pairs)}  # where each source is used last
    for i, (src, dst) in enumerate(pairs):
        try:
            if src.resolve() == dst.resolve():
                raise OSError("source and destination are the same file")
            shutil.copy2(src, dst)
            if item.promote_type is PromoteType.MOVE and last_use[src] == i:
                src.unlink()
            result.promoted.append((src, dst))
        except OSError as exc:
            result.errors.append(f"{src} -> {dst}: {exc.strerror or exc}")
    return result

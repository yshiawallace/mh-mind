from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class WordDoc:
    title: str
    body: str
    path: Path
    modified: datetime


def load_docs(folder_paths: list[Path]) -> list[WordDoc]:
    raise NotImplementedError

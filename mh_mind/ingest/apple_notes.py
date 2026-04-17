from dataclasses import dataclass
from datetime import datetime


@dataclass
class AppleNote:
    title: str
    body: str
    folder: str
    created: datetime
    modified: datetime


def export_notes() -> list[AppleNote]:
    raise NotImplementedError

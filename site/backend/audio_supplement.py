"""Load reviewed public audio listings without changing official-only links."""
import json
from pathlib import Path

from models import AudioSupplement, WorkDetail


def apply_audio_supplements(works: list[WorkDetail], path: Path) -> list[WorkDetail]:
    supplements = [AudioSupplement.model_validate(item) for item in json.loads(path.read_text(encoding="utf-8"))]
    indexed = {item.work_id: item for item in supplements}
    if len(indexed) != len(supplements) or indexed.keys() - {work.id for work in works}:
        raise ValueError("Duplicate or unknown work in public audio supplements")
    result = []
    for work in works:
        extra = indexed.get(work.id)
        if not extra:
            result.append(work)
            continue
        records = [*work.records, *(record for record in extra.records if record.id not in {r.id for r in work.records})]
        earliest = min((r for r in records if r.date), key=lambda r: (r.date, r.id), default=None)
        result.append(work.model_copy(update={"records": records, "earliest_record": earliest,
            "audio_sources": extra.sources,
            "checked_on": max([work.checked_on, *(source.checked_on for source in extra.sources),
                               *(record.checked_on for record in extra.records)]),
            "has_official_listening": work.has_official_listening or any(source.origin == "official" for source in extra.sources)}))
    return result

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
        hidden_urls = {source.url for source in extra.sources if source.origin == "unofficial"}
        records = [record for record in [*work.records, *(record for record in extra.records if record.id not in {r.id for r in work.records})]
                   if record.source_url not in hidden_urls]
        earliest = min((r for r in records if r.date), key=lambda r: (r.date, r.id), default=None)
        result.append(work.model_copy(update={"records": records, "earliest_record": earliest,
            "audio_sources": [source for source in extra.sources if source.origin == "official"],
            "has_unofficial_audio": work.has_unofficial_audio or bool(hidden_urls),
            "checked_on": max([work.checked_on, *(source.checked_on for source in extra.sources),
                               *(record.checked_on for record in extra.records)]),
            "has_official_listening": work.has_official_listening or any(source.origin == "official" for source in extra.sources)}))
    return result

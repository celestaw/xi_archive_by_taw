"""Reviewed publication prose; raw collection workflow notes never get exported."""
from models import PublicModel


class TrackAnnotation(PublicModel):
    work_id: str | None
    title: str
    disc: int | None
    track_number: int | None
    evidence: str
    note: str


class CollectionAnnotation(PublicModel):
    note: str
    tracks: list[TrackAnnotation]


class CollectionAnnotations(PublicModel):
    schema_version: int
    entries: dict[str, CollectionAnnotation]


def track_key(track):
    return tuple(track[key] for key in ("work_id", "title", "disc", "track_number"))


def apply_collection_annotations(collections, annotations):
    approved = CollectionAnnotations.model_validate(annotations)
    if approved.schema_version != 1 or set(approved.entries) != {collection["id"] for collection in collections}:
        raise ValueError("Collection publication annotations need review")
    output = []
    for collection in collections:
        note = approved.entries[collection["id"]]
        rows = {track_key(row.model_dump()): row for row in note.tracks}
        if len(rows) != len(note.tracks) or set(rows) != {track_key(track) for track in collection["tracks"]}:
            raise ValueError("Track publication annotations need review")
        tracks = []
        for track in collection["tracks"]:
            annotation = rows[track_key(track)]
            tracks.append({**track, "evidence": annotation.evidence, "note": annotation.note})
        output.append({**collection, "note": note.note, "tracks": tracks})
    return output

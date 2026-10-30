"""Exact work memberships and directional remix links for the work page."""
from models import CollectionDetail, CollectionSummary, WorkCollection, WorkContext, WorkDetail, WorkRemix


# Official album tracks without their own catalogue ID. Keep the original-work
# mapping explicit: guest remixes must not become recordings of the original.
GUEST_REMIX_ORIGINALS = {
    ("quietus-ray", "Parousia (Blacklolita Remix)"): "XI-034",
    ("quietus-ray", "Halcyon (lapix Remix)"): "XI-026",
    ("ad-piano-remixes-season-1", "天衣無縫 (EmoCo Remix)"): "XI-039",
    ("storm-and-impulse", "Halcyon (現役JK Remix)"): "XI-026",
}


def work_context(work: WorkDetail, collections: list[CollectionDetail], by_id: dict[str, WorkDetail]) -> WorkContext:
    result = WorkContext(albums=[], games=[], remixes=[])
    for collection in collections:
        tracks = [track for track in collection.tracks if track.work_id == work.id]
        if tracks:
            membership = WorkCollection(
                collection=CollectionSummary.model_validate(collection.model_dump(include=CollectionSummary.model_fields.keys())),
                tracks=tracks,
            )
            (result.albums if collection.kind == "album" else result.games).append(membership)
        if collection.kind == "album":
            for track in collection.tracks:
                if GUEST_REMIX_ORIGINALS.get((collection.id, track.title)) == work.id:
                    result.remixes.append(WorkRemix(
                        title=track.title, work_id=track.work_id, credited_name=track.credited_name,
                        evidence_status=track.evidence, source_url=track.source_url,
                        album_id=collection.id, album_title=collection.title,
                    ))
    for relationship in work.relationships:
        # Reverse edges point to the original; long versions and remasters are
        # separate relationships and must never be labelled as remixes.
        if relationship.kind != "他者による編曲・リミックス（関連する版）":
            continue
        remix = by_id[relationship.work_id]
        result.remixes.append(WorkRemix(
            title=relationship.title, work_id=relationship.work_id,
            credited_name=remix.credited_name, evidence_status=relationship.evidence_status,
        ))
    result.albums.sort(key=lambda item: (
        not item.collection.release_records or item.collection.release_records[0].date is None,
        (item.collection.release_records[0].date if item.collection.release_records else None) or "9999",
        item.collection.id,
    ))
    result.games.sort(key=lambda item: item.collection.title.casefold())
    return result

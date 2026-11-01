"""Allowlist export: keep raw research, provenance internals and local paths private."""
import json
import re
import sys
from pathlib import Path

SITE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SITE / "backend"))
from models import ArchiveMeta, Genre, Pronunciation, PublicCatalogue, PublicModel, PublicSource, WorkDetail, PublicationRecord, ListeningLink
from public_text import public_url
sys.path.insert(0, str(SITE.parent / "xi_chronology/scripts"))
from review_attribution import build_reviews, load_research


class PublicAnnotation(PublicModel):
    comment: str


def public_sources(sources):
    """Project citations explicitly; investigation and input-list data stay local."""
    result = []
    seen = set()
    for source in sources:
        if source["kind"] not in {"primary", "secondary"} or not source.get("url"):
            continue
        key = (source["kind"], source["url"], source.get("credit"))
        if key in seen:
            continue
        seen.add(key)
        result.append(PublicSource(kind=source["kind"], label=source["label"], url=source["url"],
                                  credit=source.get("credit"), checked_on=source["checked_on"]))
    return result


def record(event):
    return PublicationRecord(
        id=event["event_id"], date=event["date"], precision=event["date_precision"],
        kind=event["date_type"], medium=event["medium"], source_url=public_url(event["source_url"]),
        evidence=event["evidence_summary"], checked_on=event["checked_on"],
        version=event["recording_version"],
        true_first_publication_confirmed=event["true_first_publication_confirmed"],
    ).model_dump()


def link_comment(text, current_id, works):
    """Resolve unique catalogue names; preserve explicit editorial links and prose."""
    candidates = {}
    for work in works:
        for name in [work["title"], *(a["title"] for a in work["aliases"])]:
            candidates.setdefault(name, set()).add(work["id"])
    targets = {name: next(iter(ids)) for name, ids in candidates.items()
               if len(ids) == 1 and current_id not in ids and len(name) >= 3}
    if not targets:
        return text
    names = re.compile(r"(?<![A-Za-z0-9])(" + "|".join(
        re.escape(name) for name in sorted(targets, key=len, reverse=True)
    ) + r")(?![A-Za-z0-9])")
    # An existing Markdown link is one indivisible token, including its label.
    parts = re.split(r"(\[[^\n]*?\]\([^\s)]+\))", text)
    return "".join(part if index % 2 else names.sub(
        lambda match: f"[{match[0]}](/works/{targets[match[0]]})", part
    ) for index, part in enumerate(parts))


def build_payload(research, events, reviews, additions, genres, pronunciations, annotations):
    """Only reviewed public prose and the public schema can cross this boundary."""
    work_ids = {work["id"] for work in research["works"]}
    if annotations.keys() - work_ids:
        raise ValueError("Unknown work IDs in public annotations")
    notes = {work_id: PublicAnnotation.model_validate(value) for work_id, value in annotations.items()}
    for pronunciation in pronunciations.values():
        public_url(pronunciation["source_url"])
        Pronunciation.model_validate(pronunciation)
    unknown_pronunciations = pronunciations.keys() - {work["id"] for work in research["works"]}
    if unknown_pronunciations:
        raise ValueError(f"Unknown work IDs in pronunciation data: {sorted(unknown_pronunciations)}")
    for genre in genres.values():
        public_url(genre["source_url"])
        Genre.model_validate(genre)
    unknown_genres = genres.keys() - {work["id"] for work in research["works"]}
    if unknown_genres:
        raise ValueError(f"Unknown work IDs in genre data: {sorted(unknown_genres)}")
    titles = {w["id"]: w["title"] for w in research["works"]}
    exported = []
    for work in research["works"]:
        extra = additions.get(work["id"], {})
        comment = notes[work["id"]].comment if work["id"] in notes else ""
        records = [record(e) for e in events if e["work_id"] == work["id"] and e["is_publication_record"]]
        records += [PublicationRecord.model_validate(e).model_dump() for e in extra.get("records", [])]
        dated_records = sorted((r for r in records if r["date"]), key=lambda r: (r["date"], r["id"]))
        earliest = dated_records[0] if dated_records else None
        item = WorkDetail(
            id=work["id"], title=work["title"], credited_name=extra.get("credited_name", work["credited_name"]), role=extra.get("role", work["role"]),
            attribution="credited" if reviews[work["id"]]["verdict"] == "primary_credit" else "unverified",
            sources=public_sources(reviews[work["id"]]["sources"]),
            aliases=[{"title": a["title"], "kind": a["alias_type"], "evidence_status": a["verification_status"]} for a in work["aliases"]],
            earliest_record=earliest,
            has_official_listening=bool(work["official_listening"] or extra.get("listening")), is_variant=bool(work["relationships"] or work.get("relationships_external")),
            genre=genres.get(work["id"]),
            pronunciation=pronunciations.get(work["id"]),
            comment=link_comment(comment, work["id"], research["works"]),
            records=records,
            creation_records=[record(e) for e in events if e["work_id"] == work["id"] and not e["is_publication_record"]],
            listening=[{"url": public_url(link["url"]), "label": link["label"], "version": link["recording_version"], "official_basis": link["official_basis"], "officialness_source_url": public_url(link["officialness_source_url"]), "availability": link["availability"]} for link in work["official_listening"]],
            relationships=[{"work_id": r["parent_id"], "title": titles[r["parent_id"]], "kind": r["type"], "evidence_status": r["status"]} for r in work["relationships"]],
            checked_on=extra.get("checked_on", work["checked_on"]),
        )
        for listening in extra.get("listening", []):
            public_url(listening["url"])
            public_url(listening["officialness_source_url"])
            item.listening.append(ListeningLink.model_validate(listening))
        exported.append(item.model_dump(exclude={"pronunciation"} if item.pronunciation is None else set()))
    exported_by_id = {w["id"]: w for w in exported}
    for work in research["works"]:
        for relation in work["relationships"]:
            exported_by_id[relation["parent_id"]]["relationships"].append({
                "work_id": work["id"], "title": work["title"],
                "kind": relation["type"] + "（関連する版）", "evidence_status": relation["status"],
            })
    dated = [w for w in exported if w["earliest_record"] and w["earliest_record"]["date"]]
    meta = ArchiveMeta(
        checked_on=max(w["checked_on"] for w in exported), total_entries=len(exported),
        credited_entries=sum(w["attribution"] == "credited" for w in exported),
        dated_entries=len(dated), undated_entries=len(exported) - len(dated),
        years=sorted({int(w["earliest_record"]["date"][:4]) for w in dated}),
        mediums=sorted({r["medium"] for w in exported for r in w["records"]}),
        date_notice="掲載日は確認できた最も早い公開記録です。作曲日・真の初公開日とは限りません。日付未確認・帰属未確認の候補と別バージョンを含みます。",
    )
    return PublicCatalogue(meta=meta, works=exported)


def build():
    source = SITE.parent / "xi_chronology/data"
    read = lambda name: json.loads((source / name).read_text(encoding="utf-8"))
    research = load_research()
    events = read("publication_events.json")
    annotations = read("public_annotations.json")
    if set(annotations) != {"schema_version", "entries"} or annotations["schema_version"] != 1:
        raise ValueError("Unsupported public annotations format")
    payload = build_payload(research, events, build_reviews(research, events), read("research_additions.json"),
                            read("work_genres.json")["entries"], read("work_pronunciations.json")["entries"],
                            annotations["entries"])
    public = payload.model_dump()
    for work in public["works"]:
        if work["pronunciation"] is None:
            del work["pronunciation"]
    output = SITE / "backend/data/catalogue.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(public, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Exported {len(payload.works)} public entries; {payload.meta.dated_entries} dated records")


if __name__ == "__main__":
    build()

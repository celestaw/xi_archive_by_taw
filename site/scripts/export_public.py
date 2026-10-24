"""Allowlist export: keep raw research, provenance internals and local paths private."""
import json
import sys
from pathlib import Path
from urllib.parse import urlparse

SITE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SITE / "backend"))
from models import ArchiveMeta, WorkDetail, PublicationRecord
sys.path.insert(0, str(SITE.parent / "xi_chronology/scripts"))
from review_attribution import build_reviews


def public_url(value):
    if urlparse(value).scheme not in {"https", "http"} or not urlparse(value).netloc:
        raise ValueError(f"Not a public HTTP URL: {value}")
    return value


def record(event):
    return PublicationRecord(
        id=event["event_id"], date=event["date"], precision=event["date_precision"],
        kind=event["date_type"], medium=event["medium"], source_url=public_url(event["source_url"]),
        evidence=event["evidence_summary"], checked_on=event["checked_on"],
        version=event["recording_version"],
        true_first_publication_confirmed=event["true_first_publication_confirmed"],
    ).model_dump()


def build():
    source = SITE.parent / "xi_chronology/data"
    research = json.loads((source / "works.json").read_text(encoding="utf-8"))
    events = json.loads((source / "publication_events.json").read_text(encoding="utf-8"))
    reviews = build_reviews(research, events)
    additions_path = source / "research_additions.json"
    additions = json.loads(additions_path.read_text(encoding="utf-8")) if additions_path.exists() else {}
    for review in reviews.values():
        for evidence in review["inclusion"] + review["sources"]:
            if evidence["url"] is not None:
                public_url(evidence["url"])
    titles = {w["id"]: w["title"] for w in research["works"]}
    exported = []
    for work in research["works"]:
        extra = additions.get(work["id"], {})
        records = [record(e) for e in events if e["work_id"] == work["id"] and e["is_publication_record"]]
        records += [PublicationRecord.model_validate(e).model_dump() for e in extra.get("records", [])]
        dated_records = sorted((r for r in records if r["date"]), key=lambda r: (r["date"], r["id"]))
        earliest = dated_records[0] if dated_records else None
        issues = list(work["issues"])
        if earliest:
            issues = [x for x in issues if x != "日付未確認。曲を削除せず保留。"]
        if reviews[work["id"]]["verdict"] == "primary_credit":
            issues = [x for x in issues if x != "既存表の候補URLは探索用。一次資料による帰属・初公開日の確認が必要。"]
        item = WorkDetail(
            id=work["id"], title=work["title"], credited_name=extra.get("credited_name", work["credited_name"]), role=extra.get("role", work["role"]),
            attribution="credited" if reviews[work["id"]]["verdict"] == "primary_credit" else "unverified",
            attribution_basis=reviews[work["id"]],
            aliases=[{"title": a["title"], "kind": a["alias_type"], "evidence_status": a["verification_status"]} for a in work["aliases"]],
            earliest_record=earliest,
            has_official_listening=bool(work["official_listening"] or extra.get("listening")), is_variant=bool(work["relationships"]),
            comment=extra.get("comment", work["comment"]),
            records=records,
            creation_records=[record(e) for e in events if e["work_id"] == work["id"] and not e["is_publication_record"]],
            listening=[{"url": public_url(link["url"]), "label": link["label"], "version": link["recording_version"], "official_basis": link["official_basis"], "officialness_source_url": public_url(link["officialness_source_url"]), "availability": link["availability"]} for link in work["official_listening"]],
            relationships=[{"work_id": r["parent_id"], "title": titles[r["parent_id"]], "kind": r["type"], "evidence_status": r["status"]} for r in work["relationships"]],
            issues=issues + extra.get("issues", []), checked_on=extra.get("checked_on", work["checked_on"]),
        )
        for listening in extra.get("listening", []):
            public_url(listening["url"])
            public_url(listening["officialness_source_url"])
            item.listening.append(listening)
        if item.listening:
            item.issues = [x for x in item.issues if x != "掲載できる公式試聴先が未確認。非公式転載は採用していない。"]
        exported.append(item.model_dump())
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
    output = SITE / "backend/data/catalogue.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"meta": meta.model_dump(), "works": exported}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Exported {len(exported)} entries; {len(dated)} dated records")


if __name__ == "__main__":
    build()

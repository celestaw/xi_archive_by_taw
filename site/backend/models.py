"""Public contract. Research-only fields never enter these models."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class PublicModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PublicationRecord(PublicModel):
    id: str
    date: str | None = Field(description="YYYY / YYYY-MM / YYYY-MM-DD. 不明はnull。保存日時ではない。")
    precision: Literal["year", "month", "day"] | None
    kind: str
    medium: str
    source_url: str
    evidence: str
    version: str
    checked_on: str
    true_first_publication_confirmed: bool

    @model_validator(mode="after")
    def date_precision_matches(self):
        import re
        from datetime import date
        if self.date is None:
            if self.precision is not None:
                raise ValueError("A null date must have null precision")
        else:
            patterns = {"year": r"\d{4}", "month": r"\d{4}-\d{2}", "day": r"\d{4}-\d{2}-\d{2}"}
            if self.precision not in patterns or not re.fullmatch(patterns[self.precision], self.date):
                raise ValueError("Date and precision disagree")
            date.fromisoformat(self.date + {"year": "-01-01", "month": "-01", "day": ""}[self.precision])
        return self


class Alias(PublicModel):
    title: str
    kind: str
    evidence_status: str


class ListeningLink(PublicModel):
    url: str
    label: str
    version: str
    official_basis: str
    officialness_source_url: str
    availability: str


class Relationship(PublicModel):
    work_id: str
    title: str
    kind: str
    evidence_status: str


class AttributionSource(PublicModel):
    kind: Literal["primary", "secondary", "lead", "input"]
    label: str
    url: str | None
    locator: str
    credit: str | None
    summary: str
    identity_note: str
    checked_on: str


class AttributionBasis(PublicModel):
    verdict: Literal["primary_credit", "unverified"]
    summary: str
    inclusion: list[AttributionSource]
    sources: list[AttributionSource]
    limitations: list[str]
    reviewed_on: str


class WorkSummary(PublicModel):
    id: str
    title: str
    aliases: list[Alias]
    credited_name: str
    role: str
    attribution: Literal["credited", "unverified"]
    earliest_record: PublicationRecord | None
    has_official_listening: bool
    is_variant: bool


class WorkDetail(WorkSummary):
    attribution_basis: AttributionBasis
    comment: str
    records: list[PublicationRecord]
    creation_records: list[PublicationRecord] = Field(description="作曲・リマスター年などの制作記録。公開履歴や年表の並べ替えには使わない。")
    listening: list[ListeningLink]
    relationships: list[Relationship]
    issues: list[str]
    checked_on: str


class WorkList(PublicModel):
    items: list[WorkSummary]
    total: int
    limit: int
    offset: int


class CollectionSummary(PublicModel):
    id: str
    kind: Literal["album", "game"]
    title: str
    category: str
    entry_count: int
    source_url: str
    release_records: list[PublicationRecord]
    checked_on: str


class CollectionTrack(PublicModel):
    work_id: str | None
    title: str
    credited_name: str
    role: str
    attribution: Literal["credited", "unverified"]
    disc: int | None
    track_number: int | None
    source_url: str
    evidence: str
    checked_on: str
    listening: ListeningLink | None
    note: str
    listing_kind: Literal["収録", "BMS登録", "公式許諾曲", "追加告知", "大会向け提供", "収録候補"] = "収録"
    edition: str = ""
    source_kind: Literal["primary", "primary_reproduction", "secondary"] = "primary"
    source_label: str = ""


class CollectionDetail(CollectionSummary):
    tracks: list[CollectionTrack]
    note: str


class CollectionList(PublicModel):
    items: list[CollectionSummary]


class ArchiveMeta(PublicModel):
    schema_version: Literal[1] = 1
    checked_on: str
    total_entries: int
    credited_entries: int
    dated_entries: int
    undated_entries: int
    years: list[int]
    mediums: list[str]
    date_notice: str


class Health(PublicModel):
    status: Literal["ok"] = "ok"
    api_version: Literal["v1"] = "v1"


class ErrorBody(PublicModel):
    code: Literal["not_found", "invalid_request", "internal_error"]
    message: str


class ApiError(PublicModel):
    error: ErrorBody

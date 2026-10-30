"""Public contract. Research-only fields never enter these models."""
from typing import Annotated, Literal
from pydantic import AfterValidator, BaseModel, ConfigDict, Field, field_validator, model_validator
from public_text import check_public_text, public_url

PublicUrl = Annotated[str, AfterValidator(public_url)]


class PublicModel(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

    @field_validator("*", mode="before")
    @classmethod
    def public_text_only(cls, value):
        return check_public_text(value)


class PublicationRecord(PublicModel):
    id: str
    date: str | None = Field(description="YYYY / YYYY-MM / YYYY-MM-DD. 不明はnull。保存日時ではない。")
    precision: Literal["year", "month", "day"] | None
    kind: str
    medium: str
    source_url: PublicUrl
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
    url: PublicUrl
    label: str
    version: str
    official_basis: str
    officialness_source_url: PublicUrl
    availability: str


class Relationship(PublicModel):
    work_id: str
    title: str
    kind: str
    evidence_status: str


class PublicSource(PublicModel):
    """Public citation only; no input locators, identity investigation or workflow."""
    kind: Literal["primary", "secondary"]
    label: str
    url: PublicUrl
    credit: str | None
    checked_on: str


class Genre(PublicModel):
    label: str
    medium: str = Field(description="ジャンル表記を確認した媒体。移植先独自のジャンルとは限らない。")
    source_url: PublicUrl
    checked_on: str


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
    genre: Genre | None = None


class Pronunciation(PublicModel):
    reading: str = Field(min_length=1)
    basis: Literal["author_suggestion", "author_confirmed"] = Field(description="作者の読み方案と、作者が確定した読みを区別する。推測読みは含めない。")
    source_url: PublicUrl
    source_date: str | None = Field(default=None, description="読みを示した本人投稿の日付。確認できた場合のみYYYY-MM-DDで保持。")
    checked_on: str


class WorkDetail(WorkSummary):
    sources: list[PublicSource]
    comment: str
    records: list[PublicationRecord]
    creation_records: list[PublicationRecord] = Field(description="作曲・リマスター年などの制作記録。公開履歴や年表の並べ替えには使わない。")
    listening: list[ListeningLink]
    relationships: list[Relationship]
    checked_on: str
    pronunciation: Pronunciation | None = None


class WorkList(PublicModel):
    items: list[WorkSummary]
    total: int
    limit: int
    offset: int


class TimelineEntry(PublicModel):
    id: str
    title: str
    aliases: list[Alias]
    attribution: Literal["credited", "unverified"]
    is_variant: bool
    preview: PublicationRecord | None
    release: PublicationRecord | None
    reference: PublicationRecord | None
    connect_preview: bool = Field(description="プレビューの期間全体が本公開の期間より前と確認できる場合のみtrue。")


class TimelineList(PublicModel):
    items: list[TimelineEntry]
    checked_on: str


class CollectionSummary(PublicModel):
    id: str
    kind: Literal["album", "game"]
    title: str
    category: str
    entry_count: int
    source_url: PublicUrl
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
    source_url: PublicUrl
    evidence: str
    checked_on: str
    listening: ListeningLink | None
    note: str
    listing_kind: Literal["収録", "BMS登録", "公式許諾曲", "追加告知", "大会向け提供", "収録候補"] = "収録"
    edition: str = ""
    source_kind: Literal["primary", "primary_reproduction", "secondary"] = "primary"
    source_label: str = ""
    genre: Genre | None = None


class CollectionDetail(CollectionSummary):
    tracks: list[CollectionTrack]
    note: str


class CollectionList(PublicModel):
    items: list[CollectionSummary]


class WorkCollection(PublicModel):
    collection: CollectionSummary
    tracks: list[CollectionTrack]


class WorkRemix(PublicModel):
    title: str
    work_id: str | None
    credited_name: str
    evidence_status: str
    source_url: PublicUrl | None = None
    album_id: str | None = None
    album_title: str | None = None


class WorkContext(PublicModel):
    albums: list[WorkCollection]
    games: list[WorkCollection]
    remixes: list[WorkRemix]


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


class PublicCatalogue(PublicModel):
    meta: ArchiveMeta
    works: list[WorkDetail]


class PublicCollections(PublicModel):
    collections: list[CollectionDetail]

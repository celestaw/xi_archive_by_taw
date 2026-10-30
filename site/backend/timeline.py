"""Select dated publication milestones without inferring missing releases."""
from calendar import monthrange
from datetime import date

from models import PublicationRecord, TimelineEntry, WorkDetail

# Match the event itself, rather than words inside a qualification such as
# 「アルバム発売日（先行クロスフェードあり）」.
PREVIEW_PREFIXES = ("PV公開日", "クロスフェード公開日", "プレビュー公開日", "試聴公開日")
RELEASE_PREFIXES = (
    "muzie登録日", "旧muzie掲載日付", "BMS作品登録日", "アルバム発売日",
    "アルバム頒布日", "アルバム先行頒布日", "アルバム一般頒布日", "配信発売日",
    "本人動画公開日（公開版", "公式動画公開日", "ゲーム楽曲実装日", "ゲームイベント解禁開始日",
)


def date_bounds(record: PublicationRecord) -> tuple[date, date]:
    parts = [int(part) for part in record.date.split("-")]
    year = parts[0]
    if len(parts) == 1:
        return date(year, 1, 1), date(year, 12, 31)
    month = parts[1]
    if len(parts) == 2:
        return date(year, month, 1), date(year, month, monthrange(year, month)[1])
    day = date(year, month, parts[2])
    return day, day


def timeline_entry(work: WorkDetail) -> TimelineEntry:
    dated = sorted((record for record in work.records if record.date), key=lambda record: (record.date, record.id))
    preview = next((record for record in dated if record.kind.startswith(PREVIEW_PREFIXES)), None)
    release = next((record for record in dated if record.kind.startswith(RELEASE_PREFIXES)), None)
    # Gameplay, introductions and unspecified versions remain visible without
    # promoting their upload date to a full release date.
    reference = next((record for record in dated if not record.kind.startswith(PREVIEW_PREFIXES + RELEASE_PREFIXES)), None)
    known_dates = [record.date for record in (preview, release) if record]
    if reference and known_dates and reference.date >= min(known_dates):
        reference = None
    connect = bool(preview and release and date_bounds(preview)[1] < date_bounds(release)[0])
    return TimelineEntry(
        id=work.id, title=work.title, aliases=work.aliases,
        attribution=work.attribution, is_variant=work.is_variant,
        preview=preview, release=release, reference=reference, connect_preview=connect,
    )

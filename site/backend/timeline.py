"""Select dated publication milestones without inferring missing releases."""
from calendar import monthrange
from datetime import date, datetime, timedelta, timezone
from urllib.parse import urlparse

from models import AudioSource, PublicationRecord, TimelineEntry, WorkDetail

# Match the event itself, rather than words inside a qualification such as
# 「アルバム発売日（先行クロスフェードあり）」.
PREVIEW_PREFIXES = ("PV公開日", "クロスフェード公開日", "プレビュー公開日", "試聴公開日")
RELEASE_PREFIXES = (
    "muzie登録日", "旧muzie掲載日付", "BMS作品登録日", "アルバム発売日",
    "アルバム頒布日", "アルバム先行頒布日", "アルバム一般頒布日", "配信発売日",
    "本人動画公開日（公開版", "公式動画公開日", "ゲーム楽曲実装日", "ゲームイベント解禁開始日",
    "公式大会楽曲披露日",
)

PARTIAL_AUDIO_TERMS = ("抜粋", "クロスフェード", "PV", "プレビュー", "紹介映像", "紹介動画", "告知", "Short Edit", "全曲フル尺の公開とはしない", "全曲試聴ではない", "全編の公開ではない")
UNAVAILABLE_AUDIO_TERMS = ("公開終了を確認", "削除を確認", "非公開を確認", "配信終了を確認")
VERIFIED_FULL_AUDIO_TERMS = ("全編再生確認済み", "フル尺再生確認済み", "全曲再生確認済み")


def audio_state(work: WorkDetail):
    candidates = [link for link in work.listening if not any(
        term.casefold() in " ".join((link.label, link.version, link.availability)).casefold()
        for term in PARTIAL_AUDIO_TERMS
    )]
    available = [link for link in candidates if any(term in link.availability for term in VERIFIED_FULL_AUDIO_TERMS)
                 and not any(term in link.availability for term in ("未確認", "未検証", "未実施", *UNAVAILABLE_AUDIO_TERMS))]
    # User's display rule: a full audio listing on YouTube, SoundCloud, or an
    # issued album counts as currently listenable. Do not call this a play test.
    current_date = datetime.now(timezone(timedelta(hours=9))).date().isoformat()
    listed = [link for link in candidates if any(
        (urlparse(link.url).hostname or "") == host or (urlparse(link.url).hostname or "").endswith("." + host)
        for host in ("youtube.com", "youtu.be", "soundcloud.com", "bandcamp.com", "music.apple.com", "open.spotify.com")
    ) and not any(term in link.availability for term in UNAVAILABLE_AUDIO_TERMS)]
    albums = [record for record in work.records if record.date and record.date <= current_date and record.kind.startswith(("アルバム発売日", "アルバム頒布日", "アルバム先行頒布日", "アルバム一般頒布日"))]
    links = list({link.url: link for link in [*available, *listed]}.values())
    sources = [*work.audio_sources, *(AudioSource(origin="official", url=link.url, label=link.label,
        version=link.version, evidence=link.official_basis, checked_on=work.checked_on) for link in links),
        *(AudioSource(origin="official", url=record.source_url, label=record.medium, version=record.version,
            evidence="発売・頒布済みアルバムへの収録記録。アルバムにあるものは聴ける扱い。", checked_on=record.checked_on) for record in albums)]
    sources = list({(source.origin, source.url): source for source in sources}.values())
    if sources or work.has_unofficial_audio:
        access = "official" if any(source.origin == "official" for source in sources) else "unofficial"
        note = "公式の全曲音源・アルバムの掲載あり。" if access == "official" else "聴取可能。"
        return "available", links, note + "掲載情報に基づき聴取可能として表示。実再生・地域制限、過去からの連続公開は未検証。", sources, access
    if candidates and all(any(term in link.availability for term in UNAVAILABLE_AUDIO_TERMS) for link in candidates):
        return "unavailable", [], "確認した全曲音源は公開終了。他の公開先・終了日は未確認。", [], "unverified"
    note = "全曲音源の候補リンクあり。現在のフル尺再生・地域制限は未確認。" if candidates else "現在フルで聴ける公開先は未確認。聴けないと確定した意味ではありません。"
    return "unverified", candidates, note + "ゲーム収録歴だけでは現在も聴けると判定しません。", [], "unverified"


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
    status, full_audio_links, audio_note, sources, access = audio_state(work)
    current_date = datetime.now(timezone(timedelta(hours=9))).date().isoformat()
    full_record = None
    if status == "available":
        urls = {link.url for link in sources}
        full_record = release if release and release.date <= current_date else next((record for record in dated if record.date <= current_date and record.source_url in urls and not record.kind.startswith(PREVIEW_PREFIXES)), None)
    return TimelineEntry(
        id=work.id, title=work.title, aliases=work.aliases,
        attribution=work.attribution, is_variant=work.is_variant,
        preview=preview, release=release, reference=reference, connect_preview=connect,
        audio_status=status, full_audio_links=full_audio_links, audio_note=audio_note,
        full_record=full_record,
        audio_sources=sources, audio_access=access,
    )

"""Build source-backed album/game indexes without changing work dates or identities."""
import hashlib
import json
import re
import sys
import unicodedata
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

SITE = Path(__file__).resolve().parents[1]
ROOT = SITE.parent
sys.path.insert(0, str(SITE / "backend"))
from models import CollectionDetail, CollectionList, CollectionSummary

SOLO = {"Parousia", "Agartha", "World Fragments", "Evolved Chronicles", "Quietus Ray", "Storm and Impulse"}
# Product titles explicitly identified in the saved BOOTH evidence, not inferred
# from a publication service or a generic source URL.
ADDITIONAL_ALBUM_MEDIA = {"LOSTAIR EP", "WBC:DAIDA"}
GAME_NAMES = {
    "maimai": "maimai", "chunithm": "CHUNITHM", "ongeki": "オンゲキ",
    "sdvx-konaste": "コナステ SOUND VOLTEX III", "sdvx": "SOUND VOLTEX",
    "museca": "MÚSECA 1+1/2", "iidx": "beatmania IIDX", "deemo2": "DEEMO II",
    "danmaku": "東方ダンマクカグラ ファンタジア・ロスト", "in-falsus": "In Falsus",
}
SEGA_GAMES = {"maimai.sega.jp": "maimai", "chunithm.sega.jp": "chunithm", "ongeki.sega.jp": "ongeki"}


def norm(value):
    return unicodedata.normalize("NFKC", value).casefold().strip()


def public_url(value):
    parsed = urlparse(value)
    if parsed.scheme not in {"https", "http"} or not parsed.netloc:
        raise ValueError(f"Not a public source: {value}")
    return value


class GameLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.games = set()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a" and "game-logo-link" in attrs.get("class", "").split():
            game = SEGA_GAMES.get(urlparse(attrs.get("href", "")).netloc)
            if game:
                self.games.add(game)


def build():
    works = json.loads((SITE / "backend/data/catalogue.json").read_text(encoding="utf-8"))["works"]
    albums = json.loads((ROOT / "xi_chronology/data/album_metadata.json").read_text(encoding="utf-8"))
    videos = {v["url"]: v for v in json.loads((ROOT / "xi_chronology/data/youtube_metadata.json").read_text(encoding="utf-8"))}
    collections = []
    review = {"matching": [], "held": [], "rules": [
        "曲別の一次クレジット・保存済み公式曲目を根拠にする。最も早い公開媒体だけから収録先を推測しない。",
        "osu! Featured Artistの許諾曲一覧を、ゲーム内の公式収録曲一覧へ読み替えない。",
        "動画公開日・ポータル登録日・アルバム発売日をゲーム初収録日へ転用しない。",
        "ソロアルバムはゲストの編曲も含む公式曲目を保持。参加作品はxi関連の曲目に限定。曲名一致だけで別音源を同一版と確定しない。",
    ]}

    def track(work, title, credit, url, evidence, checked, number=None, disc=None, note="", listening=None, role=None):
        return {"work_id": work["id"] if work else None, "title": title,
                "credited_name": credit or (work["credited_name"] if work else "名義未確認"),
                "role": role if role is not None else (work["role"] if work else ""),
                "attribution": work["attribution"] if work else "unverified",
                "disc": disc, "track_number": number, "source_url": public_url(url),
                "evidence": evidence, "checked_on": checked, "listening": listening, "note": note}

    def release_records(url=None, medium=None):
        found = {}
        for work in works:
            for record in work["records"]:
                if "アルバム" not in record["kind"]:
                    continue
                if url is not None and record["source_url"] != url or medium is not None and record["medium"] != medium:
                    continue
                key = (record["date"], record["kind"], record["source_url"])
                found.setdefault(key, record)
        return sorted(found.values(), key=lambda r: (r["date"] is None, r["date"] or "", r["id"]))

    def add_collection(id, kind, title, category, url, tracks, releases=None, note=""):
        if not tracks:
            return
        checked = max(t["checked_on"] for t in tracks)
        collection = CollectionDetail(id=id, kind=kind, title=title, category=category,
            entry_count=len(tracks), source_url=public_url(url), release_records=releases or [],
            checked_on=checked, tracks=tracks, note=note)
        collections.append(collection.model_dump())

    # Resolve album tracks with the existing numbered source record first, then
    # exact title + source credit. Never use fuzzy matching for public links.
    for album in albums:
        url = album["url"]
        source_tracks = []
        for item in album["tracks"]:
            credit = item.get("artist") or ("xi" if album["title"] in SOLO else "")
            title = item["title"]
            if item.get("artist") and title.startswith(item["artist"] + " - "):
                title = title[len(item["artist"]) + 3:]
            numbered = []
            for work in works:
                if any(r["source_url"] == url and re.search(rf"第{item['track_number']}曲(?!\d)", r["evidence"]) for r in work["records"]):
                    numbered.append(work)
            matches = numbered
            method = "numbered_primary_record"
            if not matches:
                credit_has_xi = bool(re.search(r"(?<![a-z])xi(?![a-z])", credit, re.I))
                matches = [w for w in works if norm(w["title"]) == norm(title) and credit_has_xi]
                method = "exact_title_and_xi_credit"
            work = matches[0] if len(matches) == 1 else None
            include = album["title"] in SOLO or work is not None or bool(re.search(r"(?<![a-z])xi(?![a-z])", credit, re.I))
            if not include:
                continue
            if len(matches) > 1:
                review["held"].append({"album": album["title"], "track": title, "reason": "作品IDとの対応が複数。紐付け保留。"})
            note = "音源の版は未同定。" if work and not work["is_variant"] else ""
            role = None
            if "remixed by" in credit.casefold():
                role = "他者によるxi楽曲のリミックス"
                note = "xiの新規作曲として数えない。"
            if not work:
                note = note or "曲目は公式資料で確認。作品IDとの対応は未照合。"
            listening = None
            if item.get("streaming") and item.get("url"):
                listening = {"url": public_url(item["url"]), "label": "Bandcamp", "version": title,
                    "official_basis": "Diverse Systemのレーベル管理ページの曲別試聴。",
                    "officialness_source_url": url, "availability": "既存調査で試聴掲載を確認。現在の再生可否は未再検証。"}
            source_tracks.append(track(work, title, credit, url,
                f"Diverse System公式Bandcamp『{album['title']}』第{item['track_number']}曲の曲名・名義を確認。",
                "2026-10-23", number=item["track_number"], note=note, listening=listening, role=role))
            review["matching"].append({"album": album["title"], "track": title, "number": item["track_number"],
                "work_id": work["id"] if work else None, "method": method if work else "unlinked_official_track", "source_url": url})
        add_collection(urlparse(url).path.rstrip("/").split("/")[-1], "album", album["title"],
            "ソロアルバム" if album["title"] in SOLO else "参加作品", url, source_tracks,
            release_records(url=url), "公式資料で確認した曲目を掲載。音源の版は曲別の記録も参照してください。" if album["title"] in SOLO else "このアーカイブで確認できたxi関連の収録曲を掲載。")

    # Additional albums already supported by publication records (including
    # separate advance/general release dates). Do not infer an album from a URL.
    known_titles = {a["title"] for a in albums}
    extras = {}
    for work in works:
        for record in work["records"]:
            if ("アルバム" in record["kind"] or record["medium"] in ADDITIONAL_ALBUM_MEDIA) and record["medium"] not in known_titles:
                extras.setdefault(record["medium"], {}).setdefault(work["id"], (work, record))
    for title, members in sorted(extras.items()):
        tracks = []
        for work, record in members.values():
            sources = [s for s in work["attribution_basis"]["sources"] if s["kind"] == "primary" and s["url"] == record["source_url"]]
            locator = " ".join(s["locator"] for s in sources)
            num = re.search(r"(?:第|tr\.?\s*)(\d+)(?:曲)?", locator, re.I)
            disc = re.search(r"Disc\.?\s*(\d+)", locator, re.I)
            tracks.append(track(work, work["title"], work["credited_name"], record["source_url"], record["evidence"],
                record["checked_on"], int(num[1]) if num else None, int(disc[1]) if disc else None))
        tracks.sort(key=lambda t: (t["disc"] or 1, t["track_number"] is None, t["track_number"] or 0, t["title"]))
        id = "release-" + hashlib.sha256(title.encode()).hexdigest()[:10]
        add_collection(id, "album", title, "参加作品", tracks[0]["source_url"], tracks,
            release_records(medium=title), "このアーカイブで確認できたxi関連の収録曲を掲載。")

    games = {}
    for work in works:
        for source in work["attribution_basis"]["sources"]:
            if source["kind"] != "primary" or not source["url"]:
                continue
            url = source["url"]
            ids = set()
            evidence = source["summary"]
            if urlparse(url).netloc == "music-am.sega.jp":
                key = hashlib.sha256(url.encode()).hexdigest()[:16]
                paths = sorted((ROOT / "xi_chronology/sources").glob(f"**/{key}.html"))
                if paths:
                    parser = GameLinks()
                    parser.feed(paths[0].read_text(encoding="utf-8"))
                    ids = parser.games
                    evidence = "保存したSEGA公式曲別ページの『プレイ可能な音楽ゲーム』欄に該当ゲームのリンクと、曲名・アーティスト表記を確認。ポータル登録日時を初収録日に転用しない。"
            elif "p.eagate.573.jp/game/eacsdvx/iii/" in url:
                ids = {"sdvx-konaste"}
            elif "p.eagate.573.jp/game/sdvx/" in url:
                ids = {"sdvx"}
            elif "p.eagate.573.jp/game/museca/" in url:
                ids = {"museca"}
            elif url in videos and videos[url]["channel"] == "UCwzcz476gcGbMnXyxWDUpaA":
                video = videos[url]
                title = video["title"]
                # Only work-specific title markers; descriptions can contain
                # unrelated albums, events and other games.
                for marker, game in [("[DEEMO II]", "deemo2"), ("[CHUNITHM]", "chunithm"),
                    ("[maimai でらっくす]", "maimai"), ("[オンゲキ]", "ongeki"),
                    ("【beatmania IIDX", "iidx"), ("[東方ダンマクカグラ ファンタジア・ロスト]", "danmaku"),
                    ("【In Falsus】", "in-falsus")]:
                    if marker in title:
                        ids.add(game)
                evidence = f"本人チャンネルの動画タイトル『{title}』で対象ゲームとの関係を確認。動画公開日をゲーム初収録日とはしない。"
                if "Championship" in title:
                    review["held"].append({"work_id": work["id"], "reason": "大会向け書き下ろしは確認。通常のゲーム内収録を別途確認する。", "source_url": url})
            for id in ids:
                games.setdefault(id, {}).setdefault(work["id"], track(work, work["title"], source["credit"], url,
                    evidence, source["checked_on"], note="ゲームの初収録日・現在の配信状況は未確認。",
                    listening=next((link for link in work["listening"] if link["url"] == url), None)))
    for id, members in sorted(games.items(), key=lambda item: GAME_NAMES[item[0]]):
        tracks = sorted(members.values(), key=lambda t: norm(t["title"]))
        add_collection(id, "game", GAME_NAMES[id], "ゲーム", tracks[0]["source_url"], tracks,
            note="既存資料で確認できた収録・提供記録。初収録日と現在の配信状況は未確認です。")

    if len({(c["kind"], c["id"]) for c in collections}) != len(collections):
        raise ValueError("Duplicate collection IDs")
    public = {"collections": collections}
    for destination in [ROOT / "xi_chronology/data/media_collections.json", SITE / "backend/data/collections.json"]:
        destination.write_text(json.dumps(public, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ids = {"albums": [c["id"] for c in collections if c["kind"] == "album"], "games": [c["id"] for c in collections if c["kind"] == "game"]}
    (SITE / "web/lib/collection-ids.json").write_text(json.dumps(ids, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (ROOT / "xi_chronology/data/media_collection_review.json").write_text(json.dumps(review, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Built {sum(c['kind']=='album' for c in collections)} albums, {sum(c['kind']=='game' for c in collections)} games")
    print(f"Game appearances: {sum(c['entry_count'] for c in collections if c['kind']=='game')}; unlinked album tracks: {sum(t['work_id'] is None for c in collections if c['kind']=='album' for t in c['tracks'])}")


if __name__ == "__main__":
    build()

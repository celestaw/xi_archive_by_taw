"""Expose existing attribution evidence without promoting input lists into proof.

This inventories saved research; it does not claim a fresh web check for every song.
Manual findings and corrections live in attribution_overrides.json.
"""
import csv
import json
import re
import unicodedata
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
REVIEWED_ON = "2026-10-24"
IDENTITY_ANCHOR = "https://manbow.nothing.sh/event/event.cgi?action=More_def&event=50&num=15"


def read(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def load_research():
    """Combine the reconciled input snapshot with later, separately curated works."""
    research = read("works.json")
    path = DATA / "additional_works.json"
    if path.exists():
        research["works"].extend(json.loads(path.read_text(encoding="utf-8"))["works"])
    ids = [work["id"] for work in research["works"]]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate work IDs in research data")
    return research


def comparable(title):
    title = unicodedata.normalize("NFKD", title).casefold()
    return "".join(c for c in title if c.isalnum() and not unicodedata.combining(c))


def primary_source(work, event, sources, albums):
    url = event["source_url"]
    host = urlparse(url).netloc
    source = sources.get(url, {})
    label = source.get("title") or event["medium"]
    credit = None
    locator = event["medium"]
    summary = event["evidence_summary"]
    identity_note = "保存済みの一次資料確認記録を表示。帰属と個別の制作工程・初公開日は区別する。"
    if host == "diversesystem.bandcamp.com":
        album = albums.get(url, {})
        expected = [work["title"], (event.get("original_workbook_claim") or {}).get("E", "")]
        tracks = [t for t in album.get("tracks", []) if comparable(t["title"].split(" - ", 1)[-1]) in {comparable(x) for x in expected if x}]
        if len(tracks) == 1:
            track = tracks[0]
            credit = track.get("artist") or album.get("artist")
            locator = f"『{album['title']}』第{track['track_number']}曲／{track['title']}"
            summary = f"保存した公式曲目に『{track['title']}』を掲載。クレジットは『{credit}』。アルバムの発売日を作曲日や初公開日とはしていない。"
        identity_note = "Diverse Systemのレーベル管理ページの曲別クレジットを根拠とする。合作・リミックスの表記は原文の名義を保持する。"
    elif host == "web.archive.org":
        credit = "xi（muzie ID a037818）"
        locator = f"アーティストID a037818の楽曲欄／{work['title']}"
        identity_note = f"FREEDOM DiVE↓の本人BMS登録ページが同じmuzie ID a037818へリンクするため、対象のxiと照合している。照合元：{IDENTITY_ANCHOR}"
    elif host == "manbow.nothing.sh":
        raw_path = ROOT / "sources" / (source.get("key", "") + ".txt")
        body = raw_path.read_text(encoding="utf-8") if raw_path.exists() else ""
        hit = re.search(r"BMS Artist\s*\n([^\n]+)", body)
        credit = hit.group(1).strip() if hit else None
        locator = "Title／BMS Artist欄・登録者コメント"
        identity_note = "当時のBMSイベント登録ページの作者欄を根拠とする。匿名名義の対応は他の資料と分けて確認する。"
        if work["id"] == "XI-028":
            identity_note = "現在のBMS Artist欄にxiとowl-lightの両表記がある。匿名投稿時の名義だけから推測した対応ではない。"
        if work["id"] == "XI-083":
            identity_note = "このページの表記はFesta。試聴リンクが本人SoundCloudを指すことと、別掲の本人YouTube動画によるLemuriaの公開を合わせて照合している。"
    elif host == "osu.ppy.sh":
        credit = "xi（Featured Artist 727）"
        locator = f"xiの公式許諾曲一覧／{work['title']}"
        identity_note = "osu!運営のxi紹介ページと、そのページに結び付いた許諾曲一覧が根拠。紹介文・本人外部リンクで対象の作曲家を照合した記録がある。"
    elif host == "www.youtube.com":
        credit = work["credited_name"]
        locator = "本人動画のタイトル・説明欄（名義は既存調査の転記）"
        identity_note = "保存済み動画メタデータのchannelIdは本人チャンネルUCwzcz476gcGbMnXyxWDUpaA。本人の正規配信案内のYouTubeリンクと照合した記録がある。"
    elif host == "soundcloud.com":
        credit = "xi" if "/xi_com_giko_31/" in url else work["credited_name"]
        locator = "公開者のトラック本文・説明欄"
        identity_note = "本人SoundCloudはosu!公式紹介ページからのリンクと照合。レーベルのクロスフェードの場合は曲別担当の公式特設を併用する。"
    elif host == "linkco.re":
        credit = work["credited_name"]
        locator = "曲別の作曲・制作クレジット（名義は既存調査の転記）"
        identity_note = "正規配信案内の曲別担当と、そこからリンクする本人チャンネルを照合した記録がある。表示名の一致だけを根拠にしていない。"
    else:
        credit = work["credited_name"]
        locator = f"『{work['title']}』の曲名・担当欄（名義は既存調査の転記）"
        identity_note = "ゲーム運営・頒布元の公式ページの曲別クレジットを根拠とする。サイト内の別曲のxi表記だけでは確認済みとしない。"
    return dict(kind="primary", label=label, url=url, locator=locator, credit=credit,
                summary=summary, identity_note=identity_note, checked_on=event["checked_on"])


def build_reviews(research=None, events=None):
    research = research if research is not None else load_research()
    events = events if events is not None else read("publication_events.json")
    notes = {n["id"]: n for n in read("note_entries_raw.json")}
    sources = {s["url"]: s for s in read("sources.json")}
    albums = {a["url"]: a for a in read("album_metadata.json")}
    overrides = read("attribution_overrides.json")
    additions_path = DATA / "research_additions.json"
    additions = json.loads(additions_path.read_text(encoding="utf-8")) if additions_path.exists() else {}
    reviews = {}
    for work in research["works"]:
        evidence, seen = [], set()
        for event in events:
            if event["work_id"] == work["id"] and event["verification_status"].startswith("一次") and event["source_url"] not in seen:
                evidence.append(primary_source(work, event, sources, albums))
                seen.add(event["source_url"])
        inclusion = []
        if work.get("original_sheet"):
            inclusion.append(dict(kind="input", label="提供Excel『xi_composition_chronology_research.xlsx』", url=None,
                locator=f"「{work['original_sheet']}」{work['original_row']}行目", credit=work.get("credit_claim"),
                summary="既存調査表から調査対象として引き継いだ。シート名や元表の記載だけでxiへの帰属を確定したものではない。",
                identity_note="入力資料の記載であり、独立した一次証拠ではない。", checked_on=work["checked_on"]))
        work_notes = [notes[n] for n in work["note_entry_ids"]]
        if work_notes:
            inclusion.append(dict(kind="input", label="提供noteの楽曲リスト", url=work_notes[0]["source_url"],
                locator="／".join(f"{n['section']}・{n['subsection']}：{n['title_token']}" for n in work_notes), credit=None,
                summary="リストにある表記を照合し、調査対象に含めた。リストへの掲載だけでは帰属や初公開日を証明しない。",
                identity_note="曲名・別名・版の対応は別途の照合判断。", checked_on=work["checked_on"]))
        if not inclusion:
            inclusion.append(dict(kind="input", label="既存調査で追加した項目", url=None, locator=work["id"], credit=None,
                summary="本人またはレーベルの公開資料の調査から追加。帰属の資料は以下に掲げる。", identity_note="元リストへの掲載を意味しない。", checked_on=work["checked_on"]))
        override = overrides.get(work["id"], {})
        evidence.extend(override.get("sources", []))
        extra = additions.get(work["id"], {})
        evidence.extend(extra.get("sources", []))
        for url in work["source_urls_candidates"]:
            if url not in {s["url"] for s in evidence}:
                evidence.append(dict(kind="lead", label="補助Excelに記載された探索先（未検証）", url=url, locator="曲名・担当の該当箇所は未確認", credit=None,
                    summary="候補URLとして引き継いだもの。リンク先にこの曲があることや、xiの担当を確認した証拠としては扱わない。",
                    identity_note="名前の一致やWikiへのリンクだけでは同一人物と判断しない。", checked_on=work["checked_on"]))
        verdict = override.get("verdict", "primary_credit" if extra.get("verified_credit") or (any(s["kind"] == "primary" for s in evidence) and work["identity_status"] == "一次資料にクレジットあり") else "unverified")
        summary = override.get("summary", f"一次資料にクレジットを確認した既存調査記録あり。記録上の名義は『{work['credited_name']}』、担当は『{work['role']}』。" if verdict == "primary_credit" else "xiの作品と判断できる一次資料は未確認。入力資料に掲載された調査候補として残している。")
        if extra.get("verified_credit"):
            summary = f"追加調査で曲別の一次クレジットを確認。名義は『{extra['credited_name']}』。" + extra["sources"][0]["summary"]
        limitations = list(override.get("limitations", []))
        if verdict == "unverified" and not limitations:
            limitations.append("本人・レーベル・ゲーム運営・当時の登録資料で曲名と担当を確認する必要がある。未確認は誤情報との確定を意味しない。")
        if verdict == "primary_credit":
            limitations.append("資料の確認日は各出典に表示。追加資料は個別に確認したが、それ以前の全出典を再検証したことは意味しない。")
        limitations.extend(extra.get("issues", []))
        reviews[work["id"]] = dict(verdict=verdict, summary=summary, inclusion=inclusion, sources=evidence,
                                    limitations=limitations, reviewed_on=max(REVIEWED_ON, work["checked_on"]))
    return reviews


def main():
    reviews = build_reviews()
    (DATA / "attribution_reviews.json").write_text(json.dumps(reviews, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    works = {w["id"]: w for w in load_research()["works"]}
    with (DATA / "attribution_reviews.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["id", "title", "verdict", "summary", "inclusion", "sources", "limitations", "reviewed_on"])
        for key, review in reviews.items():
            writer.writerow([key, works[key]["title"], review["verdict"], review["summary"], *[json.dumps(review[k], ensure_ascii=False) for k in ("inclusion", "sources", "limitations")], review["reviewed_on"]])
    primary = sum(r["verdict"] == "primary_credit" for r in reviews.values())
    lines = ["# 曲別の掲載・帰属根拠", "", f"整理日：{REVIEWED_ON}。全{len(reviews)}項目。一次クレジットに基づく項目{primary}件、xiへの帰属未確認{len(reviews)-primary}件。", "", "保存済みの根拠を曲ごとに公開するための整理。資料の取得日と今回の整理日を分ける。全曲の外部資料を新規に再検証したという意味ではない。元Excel・元リスト・従来の判定は変更せず、新たな判断はattribution_overrides.jsonに残す。", ""]
    for key, review in reviews.items():
        lines += [f"## {key}：{works[key]['title']}", "", review["summary"], ""]
        for source in review["inclusion"] + review["sources"]:
            link = f"[{source['label']}]({source['url']})" if source["url"] else source["label"]
            lines += [f"- {source['kind']}：{link}／{source['locator']}。{source['summary']}（確認日：{source['checked_on']}）"]
        lines += ["", *[f"- 未解決：{x}" for x in review["limitations"]], ""]
    (ROOT / "帰属根拠一覧.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Attribution reviews: {len(reviews)} entries, {primary} primary, {len(reviews)-primary} unverified")


if __name__ == "__main__":
    main()

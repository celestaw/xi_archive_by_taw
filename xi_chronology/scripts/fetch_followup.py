"""Fetch research page text only; never download audio or video."""
import concurrent.futures
import hashlib
import json
import re
import urllib.request
from pathlib import Path
from html.parser import HTMLParser


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.links, self.title, self.skip, self.in_title = [], [], '', 0, False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in ('script', 'style'):
            self.skip += 1
        if tag == 'title':
            self.in_title = True
        if tag == 'a' and attrs.get('href'):
            self.links.append(attrs['href'])
        if tag in ('p', 'div', 'li', 'br', 'h1', 'h2', 'h3', 'h4', 'tr', 'td', 'th'):
            self.parts.append('\n')

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self.skip = max(0, self.skip - 1)
        if tag == 'title':
            self.in_title = False
        if tag in ('p', 'div', 'li', 'h1', 'h2', 'h3', 'h4', 'tr', 'td', 'th'):
            self.parts.append('\n')

    def handle_data(self, data):
        if self.in_title:
            self.title += data
        if not self.skip:
            self.parts.append(data)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'sources' / 'followup-20261024'
CHECKED_ON = '2026-10-24'
OUT.mkdir(exist_ok=True)


def fetch(url):
    key = hashlib.sha256(url.encode()).hexdigest()[:16]
    item = dict(url=url, key=key, checked_on=CHECKED_ON)
    try:
        request = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(request, timeout=25) as response:
            data = response.read(5_000_000)
            charset = response.headers.get_content_charset()
            if not charset:
                declared = re.search(br'charset=["\x27\s]*([a-zA-Z0-9_-]+)', data[:12000], re.I)
                charset = declared.group(1).decode('ascii') if declared else 'utf-8'
            if charset.lower() in ('shift_jis', 'shift-jis', 'sjis'):
                charset = 'cp932'
            (OUT / (key + '.bin')).write_bytes(data)
            text = data.decode(charset, errors='replace')
            item.update(status='retrieved', http_status=response.status, final_url=response.url,
                        sha256=hashlib.sha256(data).hexdigest(), bytes=len(data),
                        read_limit_reached=len(data) == 5_000_000)
        (OUT / (key + '.html')).write_text(text, encoding='utf-8')
        parser = PageParser()
        parser.feed(text)
        visible = '\n'.join(line.strip() for line in ''.join(parser.parts).splitlines() if line.strip())
        (OUT / (key + '.txt')).write_text(visible, encoding='utf-8')
        item.update(title=parser.title, links=parser.links)
    except Exception as error:
        item.update(status='failed', error=str(error))
    (OUT / (key + '.meta.json')).write_text(json.dumps(item, ensure_ascii=False, indent=2), encoding='utf-8')
    return item


if __name__ == '__main__':
    import argparse
    cli = argparse.ArgumentParser()
    cli.add_argument('input')
    cli.add_argument('--folder', default='followup-20261024')
    cli.add_argument('--checked-on', default='2026-10-24')
    args = cli.parse_args()
    if not re.fullmatch(r'[a-zA-Z0-9-]+', args.folder):
        cli.error('folder must be a simple source directory name')
    OUT = ROOT / 'sources' / args.folder
    OUT.mkdir(exist_ok=True)
    CHECKED_ON = args.checked_on
    urls = json.loads(Path(args.input).read_text(encoding='utf-8'))
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(fetch, urls))
    (OUT / (Path(args.input).stem + '-fetch.json')).write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
    for item in results:
        print(item['status'], item['url'])

"""Read-only HTTP checks for the same-domain web/API deployment; no browser needed."""
import argparse
import csv
import io
import json
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

SITE = Path(__file__).resolve().parents[1]
PRIVATE_FIELDS = {
    'attribution_basis', 'issues', 'inclusion', 'identity_note', 'locator', 'original_text',
    'original_workbook_claim', 'approval_note', 'approved_on', 'verification_notes',
    'amendments', 'revision_history', 'local_path', 'private_note',
}


class CheckFailed(Exception):
    pass


def require(condition, message):
    if not condition:
        raise CheckFailed(message)


def base_url(value):
    parsed = urlsplit(value)
    require(parsed.scheme in {'http', 'https'} and parsed.hostname, 'Use an HTTP or HTTPS site origin')
    require(not parsed.username and not parsed.password and not parsed.query and not parsed.fragment,
            'The site origin must not contain credentials, a query or a fragment')
    require(parsed.path in {'', '/'}, 'Use the site origin without a page path')
    return value.rstrip('/')


def public_fields(value):
    if isinstance(value, dict):
        require(not PRIVATE_FIELDS.intersection(value), 'A response contains an internal field')
        for child in value.values():
            public_fields(child)
    elif isinstance(value, list):
        for child in value:
            public_fields(child)


class PageParts(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_titles = False
        self.titles = []
        self.scripts = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'textarea' and attrs.get('id') == 'song-titles':
            self.in_titles = True
        if tag == 'script' and attrs.get('src', '').startswith('/_next/static/'):
            self.scripts.append(attrs['src'])

    def handle_endtag(self, tag):
        if tag == 'textarea':
            self.in_titles = False

    def handle_data(self, data):
        if self.in_titles:
            self.titles.append(data)


def check_csv(payload, titles):
    require(payload.startswith(b'\xef\xbb\xbf'), 'CSV does not have a UTF-8 BOM')
    rows = list(csv.reader(io.StringIO(payload.decode('utf-8-sig'), newline=''), strict=True))
    require(rows == [['曲名'], *[[title] for title in titles]], 'CSV titles, order or escaping differ from the public catalogue')
    return len(rows) - 1


def verify(origin):
    origin = base_url(origin)
    catalogue = json.loads((SITE / 'backend/data/catalogue.json').read_text(encoding='utf-8'))
    local_collections = json.loads((SITE / 'backend/data/collections.json').read_text(encoding='utf-8'))['collections']
    local = {work['id']: work for work in catalogue['works']}
    titles = [work['title'] for work in catalogue['works']]
    requests = 0

    def fetch(path, status=200):
        nonlocal requests
        requests += 1
        try:
            response = urlopen(Request(origin + path, headers={'User-Agent': 'xi-archive-deployment-check'}), timeout=15)
        except HTTPError as error:
            require(error.code == status, f'HTTP {error.code} at {path}; expected {status}')
            return b''
        except URLError:
            raise CheckFailed(f'Could not connect to {path}') from None
        with response:
            require(response.status == status, f'Unexpected HTTP status at {path}')
            return response.read()

    def get_json(path):
        try:
            data = json.loads(fetch(path))
        except (ValueError, UnicodeDecodeError):
            raise CheckFailed(f'Expected JSON at {path}') from None
        public_fields(data)
        return data

    require(get_json('/api/v1/health')['status'] == 'ok', 'API health check failed')
    require(get_json('/api/v1/meta')['total_entries'] == len(local), 'API metadata count differs')
    api_works = []
    for offset in range(0, len(local), 100):
        page = get_json(f'/api/v1/works?limit=100&offset={offset}')
        require(page['total'] == len(local), 'API pagination total differs')
        api_works.extend(page['items'])
    require(len(api_works) == len(local) and {work['id']: work['title'] for work in api_works} ==
            {key: work['title'] for key, work in local.items()}, 'API work IDs or titles differ')
    require(len(get_json('/api/v1/timeline')['items']) == len(local), 'Timeline count differs')
    for kind in ['album', 'game']:
        path = '/api/v1/' + ('albums' if kind == 'album' else 'games')
        require(len(get_json(path)['items']) == sum(item['kind'] == kind for item in local_collections), 'Collection count differs')
    for work_id in ['XI-025', 'XI-034', 'XI-051', 'XI-052', 'XI-072']:
        work = get_json('/api/v1/works/' + work_id)
        for field in ['title', 'comment', 'pronunciation']:
            require(work.get(field) == local[work_id].get(field), f'Public detail differs for {work_id}')
    parts = PageParts()
    parts.feed(fetch('/songs').decode('utf-8'))
    require(''.join(parts.titles).replace('\r\n', '\n') == '\n'.join(titles), 'Server-rendered title list differs')
    csv_count = check_csv(fetch('/songs.csv'), titles)
    require(parts.scripts, 'No Next.js client asset found on the title page')
    fetch(parts.scripts[0])
    for path in ['/', '/works/XI-025', '/api/v1/docs']:
        fetch(path)
    private_paths = ['/.git/config', '/.env', '/xi_chronology/data/listener_comments.json', '/backend/data/catalogue.json']
    for path in private_paths:
        fetch(path, status=404)
    return {'status': 'passed', 'origin': origin, 'catalogue_entries': len(local), 'csv_rows': csv_count,
            'html_titles': len(titles), 'http_requests': requests, 'private_paths_404': len(private_paths),
            'clipboard_and_motion': 'not exercised by this HTTP-only check'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('url', help='Site origin, e.g. https://your-project.vercel.app')
    args = parser.parse_args()
    try:
        print(json.dumps(verify(args.url), ensure_ascii=False))
    except (CheckFailed, csv.Error, UnicodeDecodeError, KeyError) as error:
        print(json.dumps({'status': 'failed', 'error': str(error)}, ensure_ascii=False))
        raise SystemExit(1)

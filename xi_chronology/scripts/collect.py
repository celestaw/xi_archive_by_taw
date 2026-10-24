import concurrent.futures, datetime, hashlib, json, pathlib, re, shutil, sys, urllib.request
import openpyxl
from html.parser import HTMLParser

class PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts=[]; self.links=[]; self.skip=0; self.title=''; self.in_title=False
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag in ('script','style'): self.skip+=1
        if tag=='title': self.in_title=True
        if tag=='a' and attrs.get('href'): self.links.append(attrs['href'])
        if tag in ('p','div','li','br','h1','h2','h3','h4','tr','td'): self.parts.append('\n')
    def handle_endtag(self,tag):
        if tag in ('script','style'): self.skip=max(0,self.skip-1)
        if tag=='title': self.in_title=False
        if tag in ('p','div','li','h1','h2','h3','h4','tr'): self.parts.append('\n')
    def handle_data(self,data):
        if self.in_title: self.title+=data
        if not self.skip: self.parts.append(data)

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / 'sources'
RAW.mkdir(parents=True, exist_ok=True)
TODAY = '2026-10-23'
INPUT = pathlib.Path(r'C:\Users\matha\Downloads\xi_composition_chronology_research.xlsx')

def dump(p, value):
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str), encoding='utf-8')

def extract():
    shutil.copy2(INPUT, RAW / INPUT.name)
    book = openpyxl.load_workbook(INPUT, read_only=False, data_only=False)
    sheets = []
    for s in book:
        rows = []
        for row in s:
            cells = [{'coordinate':c.coordinate,'value':c.value,'type':c.data_type,
                      'hyperlink':c.hyperlink.target if c.hyperlink else None}
                     for c in row if c.value is not None or c.hyperlink]
            if cells: rows.append({'row':row[0].row,'cells':cells})
        sheets.append({'name':s.title,'rows':rows})
    dump(RAW / 'workbook_raw.json', {'input':str(INPUT),'sha256':hashlib.sha256(INPUT.read_bytes()).hexdigest(),'extracted_on':TODAY,'sheets':sheets})
    print('Workbook preserved:', [(s['name'],len(s['rows'])) for s in sheets])

def fetch_one(url):
    key = hashlib.sha256(url.encode()).hexdigest()[:16]
    meta = {'url':url,'checked_on':TODAY,'key':key}
    try:
        request = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0 (compatible; chronology-research/1.0)'})
        with urllib.request.urlopen(request, timeout=35) as response:
            body = response.read()
            (RAW / (key+'.bin')).write_bytes(body)
            charset = response.headers.get_content_charset()
            match = re.search(rb'charset=["\s]*([\w-]+)',body[:12000], re.I)
            if match: charset=match.group(1).decode('ascii')
            if charset and charset.lower() in ('x-sjis','shift_jis','sjis'): charset='cp932'
            charset=charset or 'utf-8'
            try:
                html = body.decode(charset,errors='replace')
                if '\ufffd' in html:
                    candidates=[body.decode(enc,errors='replace') for enc in ('utf-8','cp932','euc-jp')]
                    html=min(candidates,key=lambda s:s.count('\ufffd'))
            except LookupError: html = body.decode('utf-8',errors='replace')
            (RAW / (key+'.html')).write_text(html,encoding='utf-8')
            parser=PageParser(); parser.feed(html)
            text = '\n'.join(x.strip() for x in ''.join(parser.parts).splitlines() if x.strip())
            (RAW / (key+'.txt')).write_text(text,encoding='utf-8')
            meta.update(status='retrieved',http_status=response.status,final_url=response.url,bytes=len(body),sha256=hashlib.sha256(body).hexdigest(),title=parser.title,links=parser.links)
    except Exception as ex: meta.update(status='failed',error=str(ex))
    dump(RAW / (key+'.meta.json'),meta)
    return meta

def fetch(mode):
    if mode.startswith('extras'): urls=json.loads((ROOT/'data'/('extra_urls.json' if mode=='extras' else mode+'_urls.json')).read_text(encoding='utf-8'))
    elif mode == 'note': urls=['https://note.com/taw_fr0mug/n/nff07ee8d5758']
    else:
        raw=json.loads((RAW/'workbook_raw.json').read_text(encoding='utf-8'))
        urls=[]
        for sheet in raw['sheets']:
            if sheet['name']=='公開記録と出典':
                for row in sheet['rows']:
                    for c in row['cells']:
                        if isinstance(c['value'],str) and c['value'].startswith('http'): urls.append(c['value'])
        urls=list(dict.fromkeys(urls))
        if mode=='archives': urls=[u for u in urls if 'web.archive.org' in u]
        if mode=='archive_raw': urls=[re.sub(r'/web/(\d+)/',r'/web/\1id_/',u) for u in urls if 'web.archive.org' in u]
    results=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        for result in pool.map(fetch_one,urls):
            results.append(result)
            print(result['status'],result['url'],flush=True)
    dump(RAW / ('fetch_'+mode+'.json'),results)

if __name__=='__main__':
    if sys.argv[1]=='extract': extract()
    elif sys.argv[1]=='fetch': fetch(sys.argv[2])

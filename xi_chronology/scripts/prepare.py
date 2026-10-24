import collections, csv, difflib, html, json, pathlib, re, unicodedata
from collect import ROOT,RAW,PageParser,dump,TODAY

DATA=ROOT/'data'; DATA.mkdir(exist_ok=True)
def norm(s): return re.sub(r'\s+','',unicodedata.normalize('NFKC',s)).casefold()
def loose(s): return re.sub(r'[^\w\u3000-\u9fff]','',norm(s))
def table(name):
    book=json.loads((RAW/'workbook_raw.json').read_text(encoding='utf-8'))
    sheet=next(s for s in book['sheets'] if s['name']==name)
    return [dict(row=r['row'],values={re.sub(r'\d','',c['coordinate']):c['value'] for c in r['cells']}) for r in sheet['rows']]

class NoteBody(PageParser):
    def __init__(self): super().__init__(); self.active=False; self.depth=0; self.lines=[]; self.chunk=[]; self.locator=None
    def flush(self):
        t=''.join(self.chunk).strip(); self.chunk=[]
        if t: self.lines.append({'text':t,'paragraph_id':self.locator})
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='div' and a.get('id')=='note-body': self.active=True; self.depth=1; return
        if not self.active:return
        if tag=='div': self.depth+=1
        if tag in ('p','h2','h3'):self.flush(); self.locator=a.get('id')
        if tag=='br':self.flush()
    def handle_endtag(self,tag):
        if not self.active:return
        if tag in ('p','h2','h3'):self.flush()
        if tag=='div':
            self.depth-=1
            if self.depth==0:self.flush();self.active=False
    def handle_data(self,data):
        if self.active:self.chunk.append(data)

def prepare():
    works={}
    for row in table('確認済み公開年表'):
        v=row['values']; k=v.get('B','')
        if not k.startswith('XI-'):continue
        works[k]={'id':k,'title':v['C'],'credit_claim':v.get('G'),'date_claim':v.get('D'),'date_kind_claim':v.get('E'),'medium_claim':v.get('F'),'notes_claim':v.get('H'),'original_row':row['row'],'original_sheet':'確認済み公開年表'}
    for row in table('要確認候補'):
        v=row['values']; k=v.get('B','')
        if not k.startswith('XI-'):continue
        works[k]={'id':k,'title':v['C'],'status_claim':v.get('D'),'medium_claim':v.get('E'),'notes_claim':v.get('F'),'candidate_url':v.get('G'),'original_row':row['row'],'original_sheet':'要確認候補'}
    dump(DATA/'workbook_items.json',list(works.values()))
    m=json.loads((RAW/'fetch_note.json').read_text(encoding='utf-8'))[0]
    parser=NoteBody();parser.feed((RAW/(m['key']+'.html')).read_text(encoding='utf-8'))
    dump(RAW/'note_lines.json',parser.lines)
    lines=parser.lines; entries=[]; top=''; sub=''
    heads={'アルバム収録','音ゲー収録','コンピアルバム','Remix','bms関連イベントまとめ'}
    for i,line in enumerate(lines):
        t=line['text']
        if t in heads:top=t;sub='';continue
        if t in ('osu!収録','beatmania ⅡDX収録','SDVX'):sub=t;continue
        if t.startswith('・'):sub=t[1:];continue
        if t.startswith(('（','ずっと','とりあえず','抜けあったら')):continue
        if t in ('Artemis xi remix',):pass
        year=None; title=t
        if top=='bms関連イベントまとめ':
            mat=re.match(r'(\d{4}):(.*)',t)
            if mat:year,title=mat.groups()
        entries.append({'id':f'NOTE-{len(entries)+1:03}','original_text':t,'title_token':title,'section':top,'subsection':sub,'year_claim':year,'line_number':i+1,'paragraph_id':line['paragraph_id'],'source_url':m['url']})
    dump(DATA/'note_entries_raw.json',entries)
    suggestions=[]
    exact={norm(w['title']):w['id'] for w in works.values()}
    for e in entries:
        n=norm(e['title_token']); matches=[]
        if n in exact:matches=[(1,exact[n],works[exact[n]]['title'])]
        else:
            matches=sorted([(difflib.SequenceMatcher(None,loose(e['title_token']),loose(w['title'])).ratio(),w['id'],w['title']) for w in works.values()],reverse=True)[:3]
        suggestions.append({'entry':e, 'suggestions':matches})
    dump(DATA/'matching_suggestions.json',suggestions)
    print('Workbook IDs',len(works),'Note appearances',len(entries),'Note raw distinct tokens',len({norm(e['title_token']) for e in entries}))
    for s in suggestions:
        if s['suggestions'][0][0]<1: print(s['entry']['id'],s['entry']['title_token'],':',s['suggestions'])
    albums=[]
    for meta in json.loads((RAW/'fetch_evidence.json').read_text(encoding='utf-8')):
        if '.bandcamp.com/' not in meta['url']:continue
        h=(RAW/(meta['key']+'.html')).read_text(encoding='utf-8')
        m=re.search(r'data-tralbum="([^"]+)"',h)
        if not m:continue
        obj=json.loads(html.unescape(m.group(1)))
        albums.append({'url':meta['url'],'title':obj['current']['title'],'artist':obj.get('artist'),'release_date':obj.get('album_release_date'),'tracks':[{'title':x['title'],'artist':x.get('artist'),'url':'https://diversesystem.bandcamp.com'+x['title_link'],'track_number':x['track_num'],'streaming':bool(x.get('streaming') and x.get('file'))} for x in obj['trackinfo']]})
    dump(DATA/'album_metadata.json',albums)
    print('Album pages parsed',len(albums))

if __name__=='__main__':prepare()

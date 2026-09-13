from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os, urllib.request, urllib.parse, json, time, math, re, sqlite3, threading

VERSION='2.0.0-production'
app=FastAPI(title='Iran Market AI Gateway',version=VERSION)
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_credentials=False, allow_methods=['*'], allow_headers=['*'])

class Candle(BaseModel):
    t:int; o:float; h:float; l:float; c:float; v:float=0
class MarketTick(BaseModel):
    symbol:str; price:float; change_pct:float=0; volume:float=0; value:float=0; source:str='demo'; ts:int=0
class Analysis(BaseModel):
    symbol:str; price:float; change_pct:float; rsi14:float; ema20:float; ema50:float; momentum:float; volume_change:float; score:int; signal:str; risk:str; entry:float; stop:float; target1:float; target2:float; source:str
class News(BaseModel):
    title:str; sentiment:str; score:int; source:str; ts:int

ASSETS=['TSE','GOLD18','USD','SILVER']
NAMES={'TSE':'شاخص کل بورس ایران','GOLD18':'طلای ۱۸ عیار','USD':'دلار آزاد','SILVER':'نقره ۹۲۵'}

DEMO={
'TSE':[100,100.2,99.8,100.6,101,101.4,101.1,102,102.6,102.1,103,103.7,104,103.2,104.5,105,104.8,106,106.7,106.2,107.5,108,107.4,109,109.6,110,109.5,111,111.8,112.2,111.7,113,113.6,114,113.5,115,115.8,116.2,117,116.5,118,118.8,119,118.5,120,121,120.5,122,123,124],
'GOLD18':[100,101,100.5,102,103,102.5,104,105,104.5,106,107,106.5,108,109,110,109,111,112,111,113,114,113,115,116,117,116,118,119,118,120,121,120,122,123,122,124,125,124,126,127,128,127,129,130,129,131,132,131,133,134,135],
'USD':[100,99.5,100,100.8,101,101.5,102,101.7,102.5,103,103.8,104,103.6,104.5,105,106,105.5,107,108,107.5,109,110,109.5,111,112,113,112.5,114,115,114.5,116,117,118,117.5,119,120,121,120.5,122,123,124,123.5,125,126,127,126.5,128,129,130,131],
'SILVER':[100,100.5,100.2,101,101.5,102,101.8,102.4,103,103.5,104,103.8,104.5,105,106,105.4,106.5,107,108,107.5,109,110,109.3,111,112,113,112.5,114,115,114.2,116,117,118,117.2,119,120,121,120.5,122,123,124,123.5,125,126,127,126.5,128,129,130,131]
}

class DataProvider:
    name='base'
    live=False
    def candles(self,symbol,limit=100): raise NotImplementedError

class DemoProvider(DataProvider):
    name='demo'; live=False
    def candles(self,symbol,limit=100):
        vals=DEMO.get(symbol.upper(),DEMO['TSE'])[-limit:]; now=int(time.time())
        return [Candle(t=now-(len(vals)-1-i)*86400,o=v*.995,h=v*1.01,l=v*.99,c=v,v=1000+i*25) for i,v in enumerate(vals)]

DB_PATH=os.getenv('IRAN_MARKET_DB','market_history.sqlite3')
_db_lock=threading.Lock()
def db():
    c=sqlite3.connect(DB_PATH,check_same_thread=False)
    c.execute('CREATE TABLE IF NOT EXISTS snapshots(symbol TEXT, ts INTEGER, price REAL, volume REAL, value REAL, source TEXT)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_snap ON snapshots(symbol,ts)')
    c.commit(); return c
DB=db()

def save_snapshot(symbol, price, volume=0, value=0, source='live', ts=None):
    ts=ts or int(time.time())
    with _db_lock:
        DB.execute('INSERT INTO snapshots(symbol,ts,price,volume,value,source) VALUES(?,?,?,?,?,?)',(symbol,ts,price,volume,value,source)); DB.commit()

def stored_candles(symbol,limit=100):
    rows=DB.execute('SELECT ts,price,volume FROM snapshots WHERE symbol=? ORDER BY ts DESC LIMIT ?', (symbol,limit)).fetchall()[::-1]
    if not rows:return []
    out=[]
    for t,p,v in rows:
        out.append(Candle(t=t,o=p,h=p,l=p,c=p,v=v or 0))
    return out

HEADERS={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36','Accept':'application/json,text/plain,text/html,*/*','Referer':'https://www.tsetmc.com/','Origin':'https://www.tsetmc.com'}

def http_json(url,timeout=10,headers=None):
    req=urllib.request.Request(url,headers=headers or HEADERS)
    with urllib.request.urlopen(req,timeout=timeout) as r:
        return json.loads(r.read().decode('utf-8','replace'))

def http_text(url,timeout=10,headers=None):
    req=urllib.request.Request(url,headers=headers or {'User-Agent':HEADERS['User-Agent'],'Accept':'text/html,*/*'})
    with urllib.request.urlopen(req,timeout=timeout) as r:
        return r.read().decode('utf-8','replace')

def num(s):
    if s is None:return None
    s=str(s).replace(',','').replace('٬','').replace('،','').replace('٫','.')
    s=re.sub(r'[^0-9.\-]','',s)
    try:return float(s) if s else None
    except:return None

class TSETMCProvider(DataProvider):
    name='tsetmc'; live=True
    base='https://cdn.tsetmc.com/api'
    def index_tick(self):
        u=self.base+'/Index/GetIndexB1LastAll/SelectedIndexes/1'
        d=http_json(u)
        arr=d.get('indexB1',d if isinstance(d,list) else [])
        if not arr: raise RuntimeError('TSETMC index response empty')
        # The first selected index is normally شاخص کل; locate by Persian label where possible.
        item=next((x for x in arr if 'کل' in str(x.get('lVal30',''))),arr[0])
        p=num(item.get('xPhNivJIdx004') or item.get('xDrNivJIdx004') or item.get('last'))
        ch=num(item.get('indexChange')) or 0
        pct=num(item.get('xVarIdxJRfV')) or 0
        if p is None: raise RuntimeError('TSETMC index price missing')
        ts=int(time.time())
        return p,ch,pct,ts
    def candles(self,symbol,limit=100):
        p,ch,pct,ts=self.index_tick(); prev=p/(1+pct/100) if pct>-99 else p
        save_snapshot(symbol,p,0,0,self.name,ts)
        cs=stored_candles(symbol,limit)
        if len(cs)<2:
            cs=[Candle(t=ts-86400,o=prev,h=prev,l=prev,c=prev,v=0),Candle(t=ts,o=p,h=p,l=p,c=p,v=0)]
        return cs

class TGJUProvider(DataProvider):
    name='tgju'; live=True
    urls={'GOLD18':'https://www.tgju.org/profile/geram18','USD':'https://www.tgju.org/profile/price_dollar_rl','SILVER':'https://www.tgju.org/profile/silver_925'}
    def current(self,symbol):
        url=os.getenv(f'TGJU_{symbol.upper()}_URL',self.urls.get(symbol.upper(),''))
        if not url: raise RuntimeError('No TGJU URL configured')
        html=http_text(url)
        # TGJU pages expose the current rate in several HTML attributes. Prefer explicit نرخ فعلی, then known price classes.
        patterns=[r'نرخ فعلی[^0-9]{0,200}([0-9][0-9,]{3,})',r'current[^0-9]{0,120}([0-9][0-9,]{3,})',r'"price"\s*:\s*"?([0-9,]+)']
        p=None
        for pat in patterns:
            m=re.search(pat,html,re.I|re.S)
            if m:
                p=num(m.group(1))
                if p: break
        if not p: raise RuntimeError('TGJU price not found')
        # Try to locate percent change nearby; otherwise derive it from our own previous snapshot.
        ts=int(time.time()); prevrow=DB.execute('SELECT price FROM snapshots WHERE symbol=? ORDER BY ts DESC LIMIT 1',(symbol,)).fetchone()
        prev=prevrow[0] if prevrow else p
        pct=(p/prev-1)*100 if prev else 0
        save_snapshot(symbol,p,0,0,self.name,ts)
        return p,pct,ts
    def candles(self,symbol,limit=100):
        p,pct,ts=self.current(symbol)
        cs=stored_candles(symbol,limit)
        if len(cs)<2:
            prev=p/(1+pct/100) if pct>-99 else p
            cs=[Candle(t=ts-86400,o=prev,h=prev,l=prev,c=prev,v=0),Candle(t=ts,o=p,h=p,l=p,c=p,v=0)]
        return cs

class CompositeProvider(DataProvider):
    name='real-composite'; live=True
    def __init__(self): self.tse=TSETMCProvider(); self.tg=TGJUProvider()
    def candles(self,symbol,limit=100):
        s=symbol.upper()
        if s=='TSE': return self.tse.candles(s,limit)
        if s in ('GOLD18','USD','SILVER'): return self.tg.candles(s,limit)
        raise RuntimeError('Unknown symbol')

LIVE=os.getenv('ENABLE_REAL_DATA','1').lower() not in ('0','false','no')
PROVIDER=CompositeProvider() if LIVE else DemoProvider()

# Optional external gateway remains supported as an override/fallback.
class JsonHttpProvider(DataProvider):
    name='external-gateway'; live=True
    def __init__(self,base_url): self.base_url=base_url.rstrip('/')
    def candles(self,symbol,limit=100):
        req=urllib.request.Request(f'{self.base_url}/market/candles/{urllib.parse.quote(symbol)}?limit={limit}',headers={'User-Agent':'IranMarketAI/1.8'})
        with urllib.request.urlopen(req,timeout=8) as r: data=json.loads(r.read().decode())
        return [Candle(**x) for x in data]

if os.getenv('IRAN_MARKET_LIVE_URL','').strip():
    PROVIDER=JsonHttpProvider(os.getenv('IRAN_MARKET_LIVE_URL').strip())


def ema(xs,n):
    e=xs[0]; k=2/(n+1)
    for x in xs[1:]: e=x*k+e*(1-k)
    return e

def rsi(xs,n=14):
    if len(xs)<=n:return 50.0
    ds=[b-a for a,b in zip(xs[-n-1:-1],xs[-n:])]; g=sum(max(d,0) for d in ds)/n; l=sum(max(-d,0) for d in ds)/n
    return 100.0 if l==0 else 100-100/(1+g/l)

def analyze(symbol,cs,source):
    xs=[x.c for x in cs]; vs=[x.v for x in cs]; p=xs[-1]; prev=xs[-2]; e20=ema(xs,20); e50=ema(xs,50); rr=rsi(xs); mom=(p/xs[-6]-1)*100 if len(xs)>=6 else 0; vc=(vs[-1]/vs[-6]-1)*100 if len(xs)>=6 and vs[-6] else 0
    score=50+(12 if p>e20 else -12)+(10 if e20>e50 else -10)+(10 if rr>=55 else -10 if rr<=45 else 0)+(8 if mom>0 else -8)+(5 if vc>0 else -5)
    score=max(0,min(100,round(score))); sig='BUY' if score>=68 else 'SELL' if score<=38 else 'HOLD'
    risk='LOW' if 45<=rr<=65 and abs(mom)<5 else 'HIGH' if rr>72 or rr<28 else 'MEDIUM'
    stop=p*(0.97 if sig=='BUY' else 0.98); t1=p*(1.04 if sig=='BUY' else 0.99); t2=p*(1.08 if sig=='BUY' else 0.97)
    return Analysis(symbol=symbol,price=round(p,4),change_pct=round((p/prev-1)*100,2),rsi14=round(rr,2),ema20=round(e20,4),ema50=round(e50,4),momentum=round(mom,2),volume_change=round(vc,2),score=score,signal=sig,risk=risk,entry=round(p,4),stop=round(stop,4),target1=round(t1,4),target2=round(t2,4),source=source)

def get_candles(symbol,limit=100):
    try:return PROVIDER.candles(symbol,limit),PROVIDER.name
    except Exception as e:
        # If a real source is unavailable, only use demo if explicitly allowed.
        if os.getenv('ALLOW_DEMO_FALLBACK','1').lower() in ('1','true','yes'):
            return DemoProvider().candles(symbol,limit),'demo-fallback'
        raise HTTPException(status_code=503,detail=f'Live data unavailable: {type(e).__name__}')

POLL_SECONDS=int(os.getenv('POLL_SECONDS','60'))
_poll_stop=threading.Event()

def _poll_once():
    for sym in ASSETS:
        try:
            PROVIDER.candles(sym, 2)
        except Exception:
            pass

def _poll_loop():
    # Build real snapshot history while the gateway is running.
    while not _poll_stop.wait(POLL_SECONDS):
        _poll_once()

@app.on_event('startup')
def startup_polling():
    if os.getenv('ENABLE_POLLING','1').lower() not in ('0','false','no'):
        threading.Thread(target=_poll_loop, name='market-poller', daemon=True).start()

@app.get('/health')
def health(): return {'ok':True,'version':VERSION,'timestamp':int(time.time()),'provider':PROVIDER.name,'live':getattr(PROVIDER,'live',False)}
@app.get('/provider')
def provider_info(): return {'name':PROVIDER.name,'live':getattr(PROVIDER,'live',False),'real_sources':{'TSE':'TSETMC','GOLD18':'TGJU','USD':'TGJU','SILVER':'TGJU'},'demo_fallback':os.getenv('ALLOW_DEMO_FALLBACK','1').lower() in ('1','true','yes')}
@app.get('/assets')
def assets(): return [{'symbol':s,'name':NAMES[s]} for s in ASSETS]
@app.get('/market/candles/{symbol}',response_model=List[Candle])
def candles(symbol:str,limit:int=Query(100,ge=2,le=500)): return get_candles(symbol,limit)[0]
@app.get('/market/tick/{symbol}',response_model=MarketTick)
def tick(symbol:str):
    cs,src=get_candles(symbol,20); p=cs[-1].c; prev=cs[-2].c
    return MarketTick(symbol=symbol.upper(),price=p,change_pct=round((p/prev-1)*100,2),volume=cs[-1].v,value=cs[-1].c*cs[-1].v,source=src,ts=cs[-1].t)
@app.get('/market/analyze/{symbol}',response_model=Analysis)
def market_analyze(symbol:str):
    cs,src=get_candles(symbol,100); return analyze(symbol.upper(),cs,src)
@app.get('/market/summary')
def summary(): return {'version':VERSION,'data_mode':PROVIDER.name,'timestamp':int(time.time()),'assets':[market_analyze(s).model_dump() for s in ASSETS]}
@app.get('/news/{symbol}',response_model=List[News])
def news(symbol:str):
    # News remains provider-ready; no fabricated live headlines.
    return []
@app.get('/risk/{symbol}')
def risk(symbol:str):
    a=market_analyze(symbol); return {'symbol':a.symbol,'risk':a.risk,'score':a.score,'note':'این خروجی ابزار تحلیلی است و توصیه قطعی سرمایه‌گذاری نیست.'}

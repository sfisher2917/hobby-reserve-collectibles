"""Owner OAuth bootstrap. Credentials stay in transient memory until saved in Render."""
import base64
from html import escape
from http.cookies import SimpleCookie
import json
import os
import secrets
import threading
import time
import urllib.parse
import urllib.request
from ebay_live import ProductionEbay, InventoryError, verify_seller

ORIGIN = 'https://hobby-reserve-inventory-api.onrender.com'
SCOPE = 'https://api.ebay.com/oauth/api_scope'
COOKIE = '__Host-hr_connect'
LOCK = threading.Lock()
SESSIONS = {}
TTL = 900

def page(title, content):
    return ('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>'+escape(title)+' | Hobby Reserve</title><style>body{background:#090a0a;color:#ece7db;font:18px/1.7 system-ui;margin:0}main{max-width:760px;margin:50px auto;padding:24px}h1{color:#d7b56d}a{color:#e7c983}button,.button{display:inline-block;background:#d7b56d;color:#111;border:0;padding:16px 22px;font:inherit;border-radius:8px;cursor:pointer;text-decoration:none}textarea{box-sizing:border-box;width:100%;height:150px;background:#161712;color:#eee;border:1px solid #9e854e;padding:12px}small{color:#bbb}</style>'
        '<main><p>HOBBY RESERVE COLLECTIBLES</p><h1>'+escape(title)+'</h1>'+content+'</main></html>')

def session_id(handler):
    try:
        cookie=SimpleCookie();cookie.load(handler.headers.get('Cookie',''))
        value=cookie.get(COOKIE)
        return value.value if value else ''
    except Exception: return ''

def cleanup():
    now=time.monotonic()
    for key in list(SESSIONS):
        if SESSIONS[key]['expires'] < now: del SESSIONS[key]

def send_page(handler, status, title, content):
    data=page(title,content).encode()
    handler.send_response(status)
    for key,value in [('Content-Type','text/html; charset=utf-8'),('Content-Length',str(len(data))),
        ('Cache-Control','no-store, private'),('CDN-Cache-Control','no-store'),('Referrer-Policy','same-origin'),
        ('X-Content-Type-Options','nosniff'),('X-Frame-Options','DENY'),
        ('Content-Security-Policy',"default-src 'none'; style-src 'unsafe-inline'; form-action 'self' https://auth.ebay.com https://signin.ebay.com; base-uri 'none'; frame-ancestors 'none'")]:
        handler.send_header(key,value)
    handler.end_headers();handler.wfile.write(data)

def redirect(handler, location, cookie=None):
    handler.send_response(303)
    handler.send_header('Location',location)
    handler.send_header('Cache-Control','no-store')
    handler.send_header('Referrer-Policy','no-referrer')
    if cookie: handler.send_header('Set-Cookie',cookie)
    handler.send_header('Content-Length','0');handler.end_headers()

def exchange(code):
    client,secret,runame=[os.environ.get(k,'') for k in ('EBAY_CLIENT_ID','EBAY_CLIENT_SECRET','EBAY_REDIRECT_URI')]
    if not all((client,secret,runame)) or '-PRD-' not in client: raise InventoryError('production_configuration_required')
    auth=base64.b64encode((client+':'+secret).encode()).decode()
    request=urllib.request.Request('https://api.ebay.com/identity/v1/oauth2/token',
        data=urllib.parse.urlencode({'grant_type':'authorization_code','code':code,'redirect_uri':runame}).encode(),
        headers={'Authorization':'Basic '+auth,'Content-Type':'application/x-www-form-urlencoded'})
    try:
        with urllib.request.urlopen(request,timeout=20) as response: result=json.load(response)
        access,refresh=result['access_token'],result['refresh_token']
        if not isinstance(refresh,str) or not refresh: raise ValueError()
    except Exception: raise InventoryError('authorization_exchange_failed') from None
    api=object.__new__(ProductionEbay);api.token=access
    verify_seller(api)
    return refresh

def handle(handler, path, query, method='GET'):
    if path == '/oauth/connect' and method == 'GET':
        send_page(handler,200,'Connect your eBay inventory',
            '<p>Authorize the real Hobby Reserve seller account. Sign-in and consent happen on eBay. This connection requests only the base Trading API scope and verifies the seller before accepting a token.</p>'
            '<a class="button" href="/oauth/start">Continue to eBay Production</a>'
            '<p>After approval, one final step saves the refresh credential in protected Render settings so the connection survives restarts. No listing data is saved.</p>')
        return True
    if path == '/oauth/start' and method in ('GET','POST'):
        # Starting consent creates only a transient browser-bound nonce. No
        # account access is granted until the single-use callback is verified.
        if method == 'POST' and handler.headers.get('Origin') != ORIGIN:
            send_page(handler,403,'Request not accepted','<p>Open the connection page and use its button.</p>');return True
        client,runame=[os.environ.get(k,'') for k in ('EBAY_CLIENT_ID','EBAY_REDIRECT_URI')]
        if not client or not runame:
            send_page(handler,503,'Configuration pending','<p>The Production redirect configuration is not ready.</p>');return True
        sid,state=secrets.token_urlsafe(32),secrets.token_urlsafe(32)
        with LOCK:
            cleanup()
            if len(SESSIONS)>=32:
                send_page(handler,429,'Please try later','<p>Too many connection attempts are pending.</p>');return True
            SESSIONS[sid]={'state':state,'expires':time.monotonic()+TTL}
        params=urllib.parse.urlencode({'client_id':client,'redirect_uri':runame,'response_type':'code','scope':SCOPE,'state':state})
        redirect(handler,'https://auth.ebay.com/oauth2/authorize?'+params,
            COOKIE+'='+sid+'; Path=/; Secure; HttpOnly; SameSite=Lax; Max-Age='+str(TTL))
        return True
    if path == '/oauth/callback' and method == 'GET':
        sid=session_id(handler)
        with LOCK:
            cleanup();entry=SESSIONS.get(sid)
            state=query.get('state',[])
            valid=entry and len(state)==1 and secrets.compare_digest(entry.get('state',''),state[0])
            if valid: entry.pop('state',None)
        if not valid:
            send_page(handler,400,'Connection link expired','<p>Start again from the connection page in the same browser.</p><a href="/oauth/connect">Connect eBay</a>');return True
        codes=query.get('code',[])
        if query.get('error') or len(codes)!=1 or not codes[0]:
            with LOCK: SESSIONS.pop(sid,None)
            send_page(handler,400,'Authorization was not completed','<p>No connection was saved. You can start again.</p>');return True
        try:
            refresh=exchange(codes[0])
            with LOCK:
                if sid not in SESSIONS: raise InventoryError('session_expired')
                SESSIONS[sid].update(refresh=refresh,expires=time.monotonic()+TTL)
            # Bootstrap activation is explicitly temporary until Render saves it.
            os.environ['EBAY_REFRESH_TOKEN']=refresh
            redirect(handler,'/oauth/result')
        except Exception:
            with LOCK: SESSIONS.pop(sid,None)
            send_page(handler,400,'Connection could not be verified','<p>Check that you authorized hobbyreservecollectibles and that the eBay accepted URL and RuName match this service. No credentials or listing data were logged.</p>')
        return True
    if path == '/oauth/result' and method == 'GET':
        with LOCK:
            cleanup();entry=SESSIONS.get(session_id(handler));ready=bool(entry and entry.get('refresh'))
        if not ready:
            send_page(handler,403,'Private connection result','<p>This page is available only in the browser that completed authorization, for 15 minutes.</p>');return True
        send_page(handler,200,'Seller verified — finish saving',
            '<p>Your seller authorization was verified. It is active in this running process, but must be saved in Render to survive a restart.</p>'
            '<ol><li>Reveal the refresh token below and copy it.</li><li>Open the Hobby Reserve Inventory API service in Render, then Environment.</li>'
            '<li>Add <strong>EBAY_REFRESH_TOKEN</strong>, paste the token, and choose Save, rebuild, and deploy.</li></ol>'
            '<form method="post" action="/oauth/reveal"><button>Reveal refresh token privately</button></form>'
            '<p>Do not post the token publicly or send a screenshot containing it.</p>')
        return True
    if path == '/oauth/reveal' and method == 'POST':
        if handler.headers.get('Origin') != ORIGIN:
            send_page(handler,403,'Request not accepted','<p>Use the result page in the same browser.</p>');return True
        with LOCK:
            cleanup();entry=SESSIONS.get(session_id(handler));refresh=entry.get('refresh') if entry else None
        if not refresh:
            send_page(handler,403,'Connection result expired','<p>Start authorization again.</p>');return True
        send_page(handler,200,'Private refresh credential',
            '<p>Copy this value into the API service’s protected Render environment variable <strong>EBAY_REFRESH_TOKEN</strong>.</p>'
            '<textarea readonly aria-label="Refresh token">'+escape(refresh)+'</textarea>'
            '<p>Keep this private. This page expires 15 minutes after authorization. After saving and deploying in Render, close this page.</p>')
        return True
    return False

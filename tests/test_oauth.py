import io
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from urllib.parse import urlsplit,parse_qs
sys.path.insert(0,str(Path('api').resolve()))
import oauth_connect as oauth
from ebay_live import InventoryError

class Handler:
    def __init__(self,headers=None):self.headers=headers or {};self.wfile=io.BytesIO();self.sent={}
    def send_response(self,status):self.status=status
    def send_header(self,k,v):self.sent[k]=v
    def end_headers(self):pass

class Tests(unittest.TestCase):
    def setUp(self):oauth.SESSIONS.clear()
    def test_form_pages_preserve_same_origin_but_no_cross_site_referrer(self):
        h=Handler();oauth.handle(h,'/oauth/connect',{})
        self.assertEqual(h.sent['Referrer-Policy'],'same-origin')
        self.assertEqual(h.sent['X-Frame-Options'],'DENY')
        self.assertIn('no-store',h.sent['Cache-Control'])
    def start(self):
        h=Handler({'Origin':oauth.ORIGIN})
        with patch.dict(os.environ,{'EBAY_CLIENT_ID':'owner-PRD-test','EBAY_REDIRECT_URI':'owner-runame'}):
            oauth.handle(h,'/oauth/start',{},'POST')
        cookie=h.sent['Set-Cookie'].split(';')[0]
        return h,cookie,parse_qs(urlsplit(h.sent['Location']).query)['state'][0]
    def test_exact_production_scope_and_secure_session(self):
        h,cookie,state=self.start()
        target=urlsplit(h.sent['Location']);args=parse_qs(target.query)
        self.assertEqual(target.netloc,'auth.ebay.com')
        self.assertEqual(args['scope'],[oauth.SCOPE])
        self.assertEqual(args['redirect_uri'],['owner-runame'])
        self.assertTrue(all(flag in h.sent['Set-Cookie'] for flag in ['Secure','HttpOnly','SameSite=Lax']))
        self.assertEqual(h.sent['Cache-Control'],'no-store')
    def test_wrong_origin_and_missing_state_rejected(self):
        h=Handler({'Origin':'https://other.example'})
        oauth.handle(h,'/oauth/start',{},'POST');self.assertEqual(h.status,403)
        h=Handler({'Origin':'null'})
        oauth.handle(h,'/oauth/start',{},'POST');self.assertEqual(h.status,403)
        h=Handler()
        with patch.object(oauth,'exchange') as exchange:
            oauth.handle(h,'/oauth/callback',{'code':['private-code'],'state':['wrong']})
            exchange.assert_not_called()
        self.assertEqual(h.status,400)
        self.assertNotIn(b'private-code',h.wfile.getvalue())
    def test_owner_result_is_cookie_bound_and_state_single_use(self):
        _,cookie,state=self.start();h=Handler({'Cookie':cookie})
        with patch.dict(os.environ,{},clear=True),patch.object(oauth,'exchange',return_value='fake-private-refresh'):
            oauth.handle(h,'/oauth/callback',{'state':[state],'code':['valid']})
            self.assertEqual(os.environ['EBAY_REFRESH_TOKEN'],'fake-private-refresh')
            self.assertEqual(h.sent['Location'],'/oauth/result')
        h=Handler({'Cookie':cookie})
        oauth.handle(h,'/oauth/callback',{'state':[state],'code':['valid']})
        self.assertEqual(h.status,400)
        stranger=Handler();oauth.handle(stranger,'/oauth/result',{})
        self.assertEqual(stranger.status,403)
        self.assertNotIn(b'fake-private-refresh',stranger.wfile.getvalue())
        h=Handler({'Cookie':cookie});oauth.handle(h,'/oauth/result',{})
        self.assertEqual(h.status,200)
        self.assertNotIn(b'fake-private-refresh',h.wfile.getvalue())
        h=Handler({'Origin':oauth.ORIGIN,'Cookie':cookie})
        oauth.handle(h,'/oauth/reveal',{},'POST')
        self.assertIn(b'fake-private-refresh',h.wfile.getvalue())
        self.assertIn('no-store',h.sent['Cache-Control'])
        self.assertEqual(h.sent['X-Frame-Options'],'DENY')
    def test_expired_session_cannot_reveal_credentials(self):
        h,cookie,_=self.start();sid=cookie.split('=',1)[1]
        oauth.SESSIONS[sid].update(expires=0,refresh='fake-secret')
        h=Handler({'Cookie':cookie,'Origin':oauth.ORIGIN})
        oauth.handle(h,'/oauth/reveal',{},'POST')
        self.assertEqual(h.status,403);self.assertNotIn(b'fake-secret',h.wfile.getvalue())
    def test_wrong_seller_token_is_not_accepted(self):
        class Result(io.BytesIO):
            def __enter__(self):return self
            def __exit__(self,*args):self.close()
        with patch.dict(os.environ,{'EBAY_CLIENT_ID':'owner-PRD-test','EBAY_CLIENT_SECRET':'fake','EBAY_REDIRECT_URI':'runame'}),patch.object(oauth.urllib.request,'urlopen',return_value=Result(json.dumps({'access_token':'fake-access','refresh_token':'fake-refresh'}).encode())),patch.object(oauth,'verify_seller',side_effect=InventoryError('seller_mismatch')):
            with self.assertRaises(InventoryError):oauth.exchange('fake-code')

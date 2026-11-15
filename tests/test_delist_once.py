import hashlib
import io
import json
import os
from pathlib import Path
import sys
import time
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET
sys.path.insert(0, str(Path('api').resolve()))
import delist_once as d

def response(content):
    return ET.fromstring('<Response xmlns="urn:ebay:apis:eBLBaseComponents">'+content+'</Response>')

class Fake:
    token = 'private-fixture'
    def __init__(self, seller=d.SELLER, listing='FixedPriceItem', status='Active'):
        self.seller, self.listing, self.status = seller, listing, status
    def call(self, *args):
        return response('<Item><Seller><UserID>'+self.seller+'</UserID></Seller><ListingType>'+self.listing+'</ListingType><SellingStatus><ListingStatus>'+self.status+'</ListingStatus></SellingStatus></Item>')

class Handler:
    def __init__(self, body=None):
        data = json.dumps(body or {}).encode()
        self.headers = {'Content-Length':str(len(data))}
        self.rfile = io.BytesIO(data)
    def send_json(self, code, data):
        self.code, self.result = code, data

class Tests(unittest.TestCase):
    def setUp(self):
        d.JOB = None
    def test_auth_requires_secret_and_expiry(self):
        token = 'a'*48
        with patch.dict(os.environ, {'DELIST_ONCE_TOKEN_SHA256':hashlib.sha256(token.encode()).hexdigest(), 'DELIST_ONCE_EXPIRES':str(time.time()+60)}, clear=True):
            self.assertTrue(d.authorized({'Authorization':'Bearer '+token}))
            self.assertFalse(d.authorized({'Authorization':'Bearer wrong'}))
            os.environ['DELIST_ONCE_EXPIRES']='0'
            self.assertFalse(d.authorized({'Authorization':'Bearer '+token}))
    def test_public_cannot_trigger_job(self):
        h = Handler()
        with patch.object(d,'authorized',return_value=False), patch.object(d,'ProductionEbay') as api:
            self.assertTrue(d.handle(h,'/admin/delist-once/prepare','POST'))
            self.assertEqual(h.code,404)
            api.assert_not_called()
    def test_wrong_seller_or_auction_never_mutates(self):
        with patch.object(d.urllib.request,'urlopen') as network:
            with self.assertRaises(d.InventoryError):
                d.end_fixed(Fake(seller='other'),'123456789012')
            self.assertEqual(d.end_fixed(Fake(listing='Chinese'),'123456789012')['status'],'skipped_non_fixed')
            self.assertEqual(d.end_fixed(Fake(status='Completed'),'123456789012')['status'],'already_inactive')
            network.assert_not_called()
    def test_fixed_end_requires_ack_and_end_time(self):
        class Reply(io.BytesIO):
            pass
        for body, valid in [('<Ack>Success</Ack><EndTime>2026-11-15T00:00:00Z</EndTime>',True),('<Ack>Failure</Ack><Errors><ErrorCode>123</ErrorCode></Errors>',False),('<Ack>Success</Ack>',False)]:
            payload=ET.tostring(response(body))
            with patch.object(d.urllib.request,'urlopen',return_value=Reply(payload)) as network:
                if valid:
                    self.assertEqual(d.end_fixed(Fake(),'123456789012')['status'],'ended')
                else:
                    with self.assertRaises(d.InventoryError): d.end_fixed(Fake(),'123456789012')
                request=network.call_args.args[0]
                self.assertIn(b'<EndingReason>NotAvailable</EndingReason>',request.data)
                self.assertIn(b'EndFixedPriceItemRequest',request.data)
    def test_prepare_does_not_mutate_and_replay_does_not_start_twice(self):
        catalog={'products':[{'id':'123456789012','listingType':'fixed'}]}
        with patch.object(d,'authorized',return_value=True), patch.object(d,'ProductionEbay'), patch.object(d,'live_catalog',return_value=catalog), patch.object(d,'end_fixed') as end, patch.object(d.threading,'Thread') as thread:
            h=Handler();d.handle(h,'/admin/delist-once/prepare','POST')
            self.assertEqual(h.code,200);end.assert_not_called();thread.assert_not_called()
            h=Handler({'confirmation':'wrong'});d.handle(h,'/admin/delist-once/execute','POST')
            self.assertEqual(h.code,409);thread.assert_not_called()
            for _ in range(2):
                h=Handler({'confirmation':d.JOB['confirmation']});d.handle(h,'/admin/delist-once/execute','POST')
                self.assertEqual(h.code,202)
            thread.assert_called_once()
    def test_auction_in_plan_blocks_all(self):
        with patch.object(d,'authorized',return_value=True),patch.object(d,'ProductionEbay'),patch.object(d,'live_catalog',return_value={'products':[{'id':'123456789012','listingType':'auction'}]}):
            h=Handler();d.handle(h,'/admin/delist-once/prepare','POST')
            self.assertEqual(h.code,409);self.assertIsNone(d.JOB)

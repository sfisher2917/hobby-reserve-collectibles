import json
import os
from pathlib import Path
import sys
import threading
import urllib.request
import urllib.error
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET
sys.path.insert(0, str(Path('api').resolve()))
import ebay_live as live
import server
def response(content): return ET.fromstring('<Response xmlns="'+live.URN+'"><Ack>Success</Ack>'+content+'</Response>')
def item(item_id, seller='hobbyreservecollectibles', status='Active', quantity='1'):
    return f'<Item><ItemID>{item_id}</ItemID><Title>Football card</Title><Seller><UserID>{seller}</UserID></Seller><Quantity>{quantity}</Quantity><QuantityAvailable>{quantity}</QuantityAvailable><SellingStatus><CurrentPrice currencyID="USD">12.50</CurrentPrice><ListingStatus>{status}</ListingStatus><QuantitySold>0</QuantitySold><HighBidder><UserID>PRIVATE_BUYER</UserID></HighBidder></SellingStatus><Description>&lt;p&gt;Card description&lt;/p&gt;</Description><PictureDetails><PictureURL>https://i.ebayimg.com/images/g/test/s-l1600.jpg</PictureURL></PictureDetails><PrivateNotes>PRIVATE_NOTES</PrivateNotes></Item>'
class Fake:
    def __init__(self): self.calls=[]
    def call(self, name, fields):
        self.calls.append((name, fields))
        if name == 'GetUser': return response('<User><UserID>hobbyreservecollectibles</UserID></User>')
        if name == 'GetItem': return response(item(fields['ItemID']))
        page = fields['ActiveList']['Pagination']['PageNumber']
        return response('<ActiveList><PaginationResult><TotalNumberOfPages>2</TotalNumberOfPages><TotalNumberOfEntries>2</TotalNumberOfEntries></PaginationResult><ItemArray>'+item(str(123456789000 + page))+'</ItemArray></ActiveList>')
class Tests(unittest.TestCase):
    def test_all_pages_and_no_private_fields(self):
        api=Fake(); result=live.live_catalog(api)
        self.assertEqual(len(result['products']),2)
        self.assertEqual([n for n,_ in api.calls],['GetUser','GetMyeBaySelling','GetMyeBaySelling'])
        self.assertNotIn('PRIVATE',json.dumps(result))
        self.assertNotIn('description',result['products'][0])
        for _, fields in api.calls:
            self.assertTrue(fields['OutputSelector'])
            self.assertFalse(any(s in ('Ack','Errors.ErrorCode') for s in fields['OutputSelector']))
            self.assertFalse(any('HighBidder' in s or 'PrivateNotes' in s or 'Email' in s for s in fields['OutputSelector']))
    def test_details_are_live_and_allowlisted(self):
        result=live.live_item(Fake(),'123456789001')
        self.assertEqual(result['product']['description'],'Card description')
        self.assertEqual(len(result['product']['images']),1)
        self.assertNotIn('PRIVATE',json.dumps(result))
    def test_other_seller_and_ended_listing_rejected(self):
        for seller,status,qty in [('someone_else','Active','1'),('hobbyreservecollectibles','Completed','1'),('hobbyreservecollectibles','Active','0')]:
            api=Fake(); api.call=lambda *_:response(item('123456789001',seller,status,qty))
            with self.assertRaises(live.InventoryError): live.live_item(api,'123456789001')
    def test_wrong_authorized_seller_rejected(self):
        api=Fake(); api.call=lambda *_:response('<User><UserID>someone_else</UserID></User>')
        with self.assertRaises(live.InventoryError): live.live_catalog(api)
    def test_incomplete_catalog_never_published(self):
        api=Fake(); original=api.call
        def missing(name, fields):
            if name=='GetMyeBaySelling': return response('<ActiveList/>')
            return original(name,fields)
        api.call=missing
        with self.assertRaises(live.InventoryError): live.live_catalog(api)
    def test_unsafe_item_rejected_without_network(self):
        api=Fake()
        with self.assertRaises(live.InventoryError): live.live_item(api,'../orders')
        self.assertEqual(api.calls,[])
    def test_xml_encoding_and_repeated_selectors(self):
        body=live.xml_request('GetItem',{'ItemID':'123456789001','OutputSelector':['Ack','Item.Title']})
        self.assertTrue(body.startswith(b"<?xml version='1.0' encoding='utf-8'?>"))
        self.assertEqual(len(ET.fromstring(body).findall('e:OutputSelector',live.NS)),2)
    def test_sandbox_keys_cannot_enable_production(self):
        with patch.dict(os.environ,{'EBAY_CLIENT_ID':'test-SBX-client','EBAY_CLIENT_SECRET':'secret','EBAY_REFRESH_TOKEN':'refresh'},clear=True):
            with self.assertRaises(live.InventoryError) as error: live.ProductionEbay()
            self.assertEqual(error.exception.code,'production_configuration_required')
    def test_http_no_store_read_only_and_no_saved_fallback(self):
        http=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
        thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start()
        base='http://127.0.0.1:'+str(http.server_port)
        try:
            with patch.dict(os.environ,{},clear=True):
                with self.assertRaises(urllib.error.HTTPError) as error: urllib.request.urlopen(base+'/api/inventory')
                self.assertEqual(error.exception.code,503)
                self.assertIn('no-store',error.exception.headers['Cache-Control'])
                self.assertNotIn('products',json.load(error.exception))
            with patch.object(server,'ProductionEbay',return_value=Fake()):
                with urllib.request.urlopen(base+'/api/inventory') as result:
                    self.assertEqual(len(json.load(result)['products']),2)
                    self.assertIn('no-store',result.headers['CDN-Cache-Control'])
                    self.assertEqual(result.headers['Access-Control-Allow-Origin'],server.ORIGIN)
            with self.assertRaises(urllib.error.HTTPError) as error:
                urllib.request.urlopen(urllib.request.Request(base+'/api/inventory',data=b'{}'))
            self.assertEqual(error.exception.code,405)
        finally: http.shutdown();http.server_close();thread.join()

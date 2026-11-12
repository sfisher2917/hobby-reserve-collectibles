"""Read-only Sandbox test: no inventory writes, commits or deployment."""
import os
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from sync_inventory import Ebay, export, URN, NS, text_at

class SandboxEbay(Ebay):
    def __init__(self):
        self.api_url = 'https://api.sandbox.ebay.com/ws/api.dll'
        self.token = os.environ.get('EBAY_SANDBOX_ACCESS_TOKEN','')
        seller = os.environ.get('EBAY_SANDBOX_SELLER_ID','')
        if not self.token or not seller.lower().startswith('testuser_'):
            raise RuntimeError('Sandbox OAuth access token and TESTUSER_ seller required.')
        os.environ['EBAY_SELLER_ID'] = seller

    def call(self, name, fields):
        # Developer Portal Auth'n'Auth tokens require XML credentials, not IAF.
        if not self.token.startswith('v^1.'):
            return super().call(name, fields)
        root = ET.Element(name+'Request', xmlns=URN)
        def add(parent, values):
            for key, value in values.items():
                child = ET.SubElement(parent, key)
                if isinstance(value, dict): add(child, value)
                else: child.text = str(value)
        add(root, {'RequesterCredentials': {'eBayAuthToken': self.token}, **fields})
        request = urllib.request.Request(self.api_url, data=ET.tostring(root), headers={
            'Content-Type': 'text/xml', 'X-EBAY-API-CALL-NAME': name,
            'X-EBAY-API-SITEID': '0', 'X-EBAY-API-COMPATIBILITY-LEVEL': '1489'})
        with urllib.request.urlopen(request, timeout=60) as result:
            response = ET.fromstring(result.read())
        if text_at(response, 'e:Ack') not in ('Success', 'Warning'):
            codes = [text_at(error, 'e:ErrorCode') for error in response.findall('e:Errors', NS)]
            print('eBay rejected', name, 'with error codes:', ', '.join(c for c in codes if re.fullmatch(r'\d+', c)))
            raise RuntimeError('Sandbox API rejected authorization or request.')
        return response

if __name__ == '__main__':
    try:
        data = export(SandboxEbay(),{},datetime.now(timezone.utc))
        products = data['products']
        print('Sandbox authorization and active-list retrieval succeeded.')
        print('Active test listings:',len(products))
        print('With photos:',sum(bool(p.get('image')) for p in products))
        print('With descriptions:',sum(bool(p.get('description')) for p in products))
        if not products: print('Create a Sandbox test listing to validate photos and descriptions.')
        print('No inventory was written or published.')
    except Exception:
        print('Sandbox test failed. Check user token, expiry and test seller. No inventory was published.')
        raise SystemExit(1) from None

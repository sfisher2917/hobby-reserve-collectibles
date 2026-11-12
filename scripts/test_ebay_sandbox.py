"""Read-only Sandbox test: no inventory writes, commits or deployment."""
import os
from datetime import datetime, timezone
from sync_inventory import Ebay, export

class SandboxEbay(Ebay):
    def __init__(self):
        self.api_url = 'https://api.sandbox.ebay.com/ws/api.dll'
        self.token = os.environ.get('EBAY_SANDBOX_ACCESS_TOKEN','')
        seller = os.environ.get('EBAY_SANDBOX_SELLER_ID','')
        if not self.token or not seller.lower().startswith('testuser_'):
            raise RuntimeError('Sandbox OAuth access token and TESTUSER_ seller required.')
        os.environ['EBAY_SELLER_ID'] = seller

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
        print('Sandbox test failed. Check OAuth access token, expiry and test seller. No inventory was published.')
        raise SystemExit(1) from None

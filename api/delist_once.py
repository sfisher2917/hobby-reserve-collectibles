"""Expiring owner-only delisting job; no public writes or automatic execution."""
import hashlib
import json
import os
import secrets
import threading
import time
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from ebay_live import ProductionEbay, InventoryError, SELLER, NS, text_at, xml_request, live_catalog, verify_seller

LOCK = threading.Lock()
JOB = None

def authorized(headers):
    expected = os.environ.get('DELIST_ONCE_TOKEN_SHA256', '')
    try:
        deadline = float(os.environ.get('DELIST_ONCE_EXPIRES', '0'))
    except ValueError:
        return False
    token = headers.get('Authorization', '')
    return (len(expected) == 64 and time.time() < deadline and
            token.startswith('Bearer ') and secrets.compare_digest(
                hashlib.sha256(token[7:].encode()).hexdigest(), expected))

def inspect(api, item_id):
    document = api.call('GetItem', {'ItemID': item_id, 'OutputSelector': [
        'Item.ItemID', 'Item.Seller.UserID', 'Item.ListingType',
        'Item.SellingStatus.ListingStatus']})
    item = document.find('e:Item', NS)
    if item is None or text_at(item, 'e:Seller/e:UserID').lower() != SELLER:
        raise InventoryError('seller_mismatch')
    return text_at(item, 'e:ListingType'), text_at(item, 'e:SellingStatus/e:ListingStatus')

def end_fixed(api, item_id):
    listing_type, status = inspect(api, item_id)
    if status != 'Active':
        return {'id': item_id, 'status': 'already_inactive'}
    if listing_type not in ('FixedPriceItem', 'StoresFixedPrice'):
        return {'id': item_id, 'status': 'skipped_non_fixed'}
    # Deliberately separate from the public read-only API call allowlist.
    request = urllib.request.Request('https://api.ebay.com/ws/api.dll',
        data=xml_request('EndFixedPriceItem', {'ItemID': item_id, 'EndingReason': 'NotAvailable'}),
        headers={'Content-Type': 'text/xml; charset=utf-8',
                 'X-EBAY-API-CALL-NAME': 'EndFixedPriceItem', 'X-EBAY-API-SITEID': '0',
                 'X-EBAY-API-COMPATIBILITY-LEVEL': '1489', 'X-EBAY-API-IAF-TOKEN': api.token})
    with urllib.request.urlopen(request, timeout=30) as response:
        document = ET.fromstring(response.read(1024 * 1024))
    if text_at(document, 'e:Ack') not in ('Success', 'Warning'):
        codes = [text_at(e, 'e:ErrorCode') for e in document.findall('e:Errors', NS)]
        safe = [c for c in codes if c.isdigit()]
        raise InventoryError('end_failed_' + '_'.join(safe))
    end_time = text_at(document, 'e:EndTime')
    if not end_time:
        raise InventoryError('end_time_missing')
    return {'id': item_id, 'status': 'ended', 'endTime': end_time}

def run(job):
    try:
        api = ProductionEbay()
        verify_seller(api)
        def one(item_id):
            try:
                return end_fixed(api, item_id)
            except Exception as error:
                # Never blindly repeat an uncertain mutation.
                try:
                    _, status = inspect(api, item_id)
                    if status != 'Active':
                        return {'id': item_id, 'status': 'verified_inactive'}
                except Exception:
                    pass
                return {'id': item_id, 'status': 'failed', 'error':
                        error.code if isinstance(error, InventoryError) else 'upstream_uncertain'}
        with ThreadPoolExecutor(max_workers=3) as pool:
            for result in pool.map(one, job['ids']):
                with LOCK:
                    job['results'].append(result)
        remaining = live_catalog(api)
        with LOCK:
            job['remainingActive'] = remaining['storeListingCount']
            job['remainingIds'] = [p['id'] for p in remaining['products']]
            job['state'] = 'complete'
    except Exception as error:
        with LOCK:
            job['state'] = 'verification_failed'
            job['error'] = error.code if isinstance(error, InventoryError) else 'upstream_unavailable'

def handle(handler, path, method):
    global JOB
    if not path.startswith('/admin/delist-once/'):
        return False
    if not authorized(handler.headers):
        handler.send_json(404, {'error': 'not_found'})
        return True
    if method == 'GET' and path == '/admin/delist-once/status':
        with LOCK:
            result = json.loads(json.dumps(JOB)) if JOB else {'state': 'not_prepared'}
        handler.send_json(200, result)
        return True
    if method != 'POST':
        handler.send_json(405, {'error': 'method_not_allowed'})
        return True
    try:
        size = int(handler.headers.get('Content-Length', '0'))
        if not 0 < size <= 4096:
            raise ValueError()
        body = json.loads(handler.rfile.read(size))
        if not isinstance(body, dict):
            raise ValueError()
    except Exception:
        handler.send_json(400, {'error': 'invalid_request'})
        return True
    if path == '/admin/delist-once/prepare':
        with LOCK:
            if JOB is not None:
                handler.send_json(409, {'error': 'already_prepared'})
                return True
            try:
                catalog = live_catalog(ProductionEbay())
                products = catalog['products']
                if len(products) > 1000 or any(p['listingType'] != 'fixed' for p in products):
                    raise InventoryError('fixed_price_only_limit', 409)
                ids = sorted(p['id'] for p in products)
                JOB = {'state': 'prepared', 'seller': SELLER, 'count': len(ids), 'ids': ids,
                       'confirmation': hashlib.sha256(('end:' + ','.join(ids)).encode()).hexdigest(),
                       'preparedAt': time.time(), 'results': []}
                handler.send_json(200, JOB)
            except InventoryError as error:
                handler.send_json(error.status, {'error': error.code})
        return True
    if path == '/admin/delist-once/execute':
        with LOCK:
            if not JOB or body.get('confirmation') != JOB['confirmation']:
                handler.send_json(409, {'error': 'confirmation_mismatch'})
                return True
            if JOB['state'] == 'prepared':
                if time.time() - JOB['preparedAt'] > 900:
                    handler.send_json(409, {'error': 'plan_expired'})
                    return True
                JOB['state'] = 'running'
                threading.Thread(target=run, args=(JOB,), daemon=True).start()
            handler.send_json(202, {'state': JOB['state'], 'count': JOB['count']})
        return True
    handler.send_json(404, {'error': 'not_found'})
    return True

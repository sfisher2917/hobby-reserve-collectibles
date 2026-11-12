"""Production-only, request-scoped eBay inventory. No listing cache or disk writes."""
import base64
from datetime import datetime, timezone
import json
import math
import os
import re
import sys
import urllib.parse
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from sync_inventory import classify, details_from_item, NS, URN, text_at

SELLER = 'hobbyreservecollectibles'
COMMON = []  # Standard Ack/error metadata is returned automatically, not selectable.
SUMMARY = ['ItemID', 'Title', 'PictureDetails.GalleryURL',
           'SellingStatus.CurrentPrice', 'QuantityAvailable', 'ListingType',
           'ListingDetails.StartTime', 'ListingDetails.EndTime']
DETAIL = ['ItemID', 'Title', 'Seller.UserID', 'Description', 'PictureDetails.PictureURL',
          'PictureDetails.GalleryURL', 'PrimaryCategory.CategoryName', 'ConditionDisplayName',
          'ItemSpecifics.NameValueList', 'SellingStatus.CurrentPrice', 'SellingStatus.ListingStatus',
          'SellingStatus.QuantitySold', 'Quantity', 'ListingType', 'ListingDetails.StartTime',
          'ListingDetails.EndTime', 'ShippingDetails.ShippingServiceOptions.ShippingService',
          'ShippingDetails.ShippingServiceOptions.ShippingServiceCost', 'ReturnPolicy.ReturnsAccepted',
          'ReturnPolicy.ReturnsWithin', 'ReturnPolicy.Refund', 'ReturnPolicy.ShippingCostPaidBy']

class InventoryError(Exception):
    def __init__(self, code='upstream_unavailable', status=503):
        self.code, self.status = code, status
        super().__init__(code)

def configured():
    return all(os.environ.get(k) for k in ('EBAY_CLIENT_ID', 'EBAY_CLIENT_SECRET', 'EBAY_REFRESH_TOKEN'))

def xml_request(name, fields):
    root = ET.Element(name + 'Request', xmlns=URN)
    def add(parent, key, value):
        if isinstance(value, list):
            for entry in value: add(parent, key, entry)
            return
        child = ET.SubElement(parent, key)
        if isinstance(value, dict):
            for k, v in value.items(): add(child, k, v)
        else: child.text = str(value)
    for key, value in fields.items(): add(root, key, value)
    return ET.tostring(root, encoding='utf-8', xml_declaration=True)

class ProductionEbay:
    def __init__(self):
        if not configured(): raise InventoryError('authorization_required')
        client, secret, refresh = [os.environ[k] for k in ('EBAY_CLIENT_ID', 'EBAY_CLIENT_SECRET', 'EBAY_REFRESH_TOKEN')]
        if '-PRD-' not in client or os.environ.get('EBAY_SELLER_ID', SELLER).lower() != SELLER:
            raise InventoryError('production_configuration_required')
        authorization = base64.b64encode((client + ':' + secret).encode()).decode()
        request = urllib.request.Request('https://api.ebay.com/identity/v1/oauth2/token',
            data=urllib.parse.urlencode({'grant_type':'refresh_token', 'refresh_token':refresh,
                 'scope':'https://api.ebay.com/oauth/api_scope'}).encode(),
            headers={'Authorization':'Basic ' + authorization, 'Content-Type':'application/x-www-form-urlencoded'})
        try:
            with urllib.request.urlopen(request, timeout=20) as response: data = json.load(response)
            self.token = data['access_token']
        except Exception: raise InventoryError('authorization_required') from None

    def call(self, name, fields):
        if name not in ('GetUser', 'GetMyeBaySelling', 'GetItem'): raise InventoryError('unsupported_call', 400)
        request = urllib.request.Request('https://api.ebay.com/ws/api.dll', data=xml_request(name, fields),
            headers={'Content-Type':'text/xml; charset=utf-8', 'X-EBAY-API-CALL-NAME':name,
                     'X-EBAY-API-SITEID':'0', 'X-EBAY-API-COMPATIBILITY-LEVEL':'1489',
                     'X-EBAY-API-IAF-TOKEN':self.token})
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                document = ET.fromstring(response.read(8 * 1024 * 1024))
        except urllib.error.HTTPError as error:
            raise InventoryError('ebay_http_' + str(error.code)) from None
        except TimeoutError: raise InventoryError('ebay_timeout') from None
        except ET.ParseError: raise InventoryError('ebay_invalid_xml') from None
        except Exception: raise InventoryError('ebay_transport_error') from None
        if text_at(document, 'e:Ack') not in ('Success', 'Warning'):
            codes = {text_at(e, 'e:ErrorCode') for e in document.findall('e:Errors', NS)}
            if codes & {'21916984', '931', '932', '16110'}: raise InventoryError('authorization_required')
            if codes & {'17', '1047'}: raise InventoryError('item_unavailable', 410)
            safe_codes=sorted(c for c in codes if re.fullmatch(r'\d{1,12}', c))
            raise InventoryError('ebay_' + name.lower() + '_' + ('_'.join(safe_codes) or 'missing_ack'))
        return document

def verify_seller(api):
    identity = api.call('GetUser', {'OutputSelector': COMMON + ['User.UserID']})
    if text_at(identity, 'e:User/e:UserID').lower() != SELLER:
        raise InventoryError('seller_mismatch')

def public_summary(item):
    item_id, title = text_at(item, 'e:ItemID'), text_at(item, 'e:Title')
    price = item.find('e:SellingStatus/e:CurrentPrice', NS)
    if not re.fullmatch(r'\d{9,15}', item_id) or not title or price is None or price.attrib.get('currencyID') != 'USD':
        raise InventoryError('incomplete_inventory')
    try: amount = float(price.text)
    except (ValueError, TypeError): raise InventoryError('incomplete_inventory') from None
    if not math.isfinite(amount) or amount < 0: raise InventoryError('incomplete_inventory')
    category = text_at(item, 'e:PrimaryCategory/e:CategoryName')
    picture = text_at(item, 'e:PictureDetails/e:PictureURL') or text_at(item, 'e:PictureDetails/e:GalleryURL')
    if picture.startswith('https://i.ebayimg.com/'):
        picture = re.sub(r's-l\d+(?=\.)', 's-l1600', picture)
    else: picture = ''
    product = {'id':item_id, 'title':title, 'price':amount, 'currency':'USD', 'image':picture,
        'url':'https://www.ebay.com/itm/' + item_id, 'categories':classify(title, category),
        'featured':item_id in os.environ.get('FEATURED_ITEM_IDS', '').split(','),
        'listingType':'auction' if text_at(item, 'e:ListingType') in ('Chinese', 'Dutch') else 'fixed',
        'startTime':text_at(item, 'e:ListingDetails/e:StartTime'),
        'endTime':text_at(item, 'e:ListingDetails/e:EndTime')}
    quantity = text_at(item, 'e:QuantityAvailable')
    if quantity.isdigit(): product['quantity'] = int(quantity)
    return product

def live_catalog(api):
    verify_seller(api)
    products, page, pages = {}, 1, 1
    expected = None
    while page <= pages:
        response = api.call('GetMyeBaySelling', {
            'ActiveList':{'Include':'true', 'Pagination':{'EntriesPerPage':200, 'PageNumber':page}},
            'SoldList':{'Include':'false'}, 'UnsoldList':{'Include':'false'},
            'ScheduledList':{'Include':'false'},
            'OutputSelector':COMMON + ['ActiveList.PaginationResult.TotalNumberOfPages',
                'ActiveList.PaginationResult.TotalNumberOfEntries'] + ['ActiveList.ItemArray.Item.' + field for field in SUMMARY]})
        page_count = text_at(response, 'e:ActiveList/e:PaginationResult/e:TotalNumberOfPages')
        total = text_at(response, 'e:ActiveList/e:PaginationResult/e:TotalNumberOfEntries')
        if not page_count.isdigit() or not total.isdigit(): raise InventoryError('incomplete_inventory')
        pages, total = int(page_count), int(total)
        if pages > 125 or total >= 25000 or (expected is not None and expected != total):
            raise InventoryError('inventory_changed_retry')
        expected = total
        for item in response.findall('e:ActiveList/e:ItemArray/e:Item', NS):
            product = public_summary(item)
            products[product['id']] = product
        page += 1
    if len(products) != expected: raise InventoryError('incomplete_inventory')
    now = datetime.now(timezone.utc)
    available = [p for p in products.values() if p.get('quantity') != 0 and
        (not p['endTime'] or datetime.fromisoformat(p['endTime'].replace('Z', '+00:00')) > now)]
    return {'status':'ok', 'source':'ebay_live', 'updatedAt':now.isoformat(),
            'seller':SELLER, 'storeListingCount':len(available), 'products':available}

def live_item(api, item_id):
    if not re.fullmatch(r'\d{9,15}', item_id): raise InventoryError('invalid_item', 400)
    response = api.call('GetItem', {'ItemID':item_id, 'DetailLevel':'ReturnAll',
        'IncludeItemSpecifics':'true', 'OutputSelector':COMMON + ['Item.' + field for field in DETAIL]})
    item = response.find('e:Item', NS)
    if item is None or text_at(item, 'e:Seller/e:UserID').lower() != SELLER:
        raise InventoryError('item_unavailable', 404)
    if text_at(item, 'e:SellingStatus/e:ListingStatus') != 'Active': raise InventoryError('item_unavailable', 410)
    now = datetime.now(timezone.utc)
    product = public_summary(item)
    total, sold = text_at(item, 'e:Quantity'), text_at(item, 'e:SellingStatus/e:QuantitySold')
    if total.isdigit() and sold.isdigit(): product['quantity'] = max(0, int(total) - int(sold))
    if product.get('quantity') == 0: raise InventoryError('item_unavailable', 410)
    if product['endTime'] and datetime.fromisoformat(product['endTime'].replace('Z', '+00:00')) <= now:
        raise InventoryError('item_unavailable', 410)
    product.update(details_from_item(item, now))
    return {'status':'ok', 'source':'ebay_live', 'updatedAt':now.isoformat(), 'product':product}

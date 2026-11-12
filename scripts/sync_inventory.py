"""Read-only eBay Trading API exporter. Credentials remain in environment memory."""
import base64
from datetime import datetime, timezone, timedelta
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

NS = {'e': 'urn:ebay:apis:eBLBaseComponents'}
URN = NS['e']

class PlainText(HTMLParser):
    def __init__(self):
        super().__init__(); self.parts = []; self.blocked = 0
    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'): self.blocked += 1
        if tag in ('br','p','div','li'): self.parts.append('\n')
    def handle_endtag(self, tag):
        if tag in ('script','style'): self.blocked = max(0, self.blocked - 1)
    def handle_data(self, data):
        if not self.blocked: self.parts.append(data)

def plain(value):
    p = PlainText(); p.feed(value or '')
    return re.sub(r'\n\s*\n+', '\n\n', ''.join(p.parts)).strip()[:12000]

def text_at(node, path, default=''):
    value = node.find(path, NS)
    return value.text if value is not None and value.text is not None else default

def details_from_item(item, now):
    images = [n.text for n in item.findall('e:PictureDetails/e:PictureURL', NS) if n.text]
    if not images:
        gallery = text_at(item,'e:PictureDetails/e:GalleryURL')
        images = [gallery] if gallery else []
    specifics = {}
    for entry in item.findall('e:ItemSpecifics/e:NameValueList', NS):
        name = text_at(entry,'e:Name')
        if name: specifics[name] = [n.text for n in entry.findall('e:Value', NS) if n.text]
    shipping = []
    for option in item.findall('e:ShippingDetails/e:ShippingServiceOptions', NS):
        service = text_at(option,'e:ShippingService')
        amount = text_at(option,'e:ShippingServiceCost')
        cost = float(amount) if amount else None
        if service: shipping.append({'service':service,'cost':cost})
    returns = [text_at(item,'e:ReturnPolicy/'+field) for field in ['ReturnsAccepted','ReturnsWithin','Refund','ShippingCostPaidBy']]
    return {'description':plain(text_at(item,'e:Description')),'image':images[0] if images else '', 'images':images,'categoryName':text_at(item,'e:PrimaryCategory/e:CategoryName'),'descriptionUpdatedAt':now.isoformat(),'condition':text_at(item,'e:ConditionDisplayName'),'itemSpecifics':specifics,'shipping':shipping,'returns':' · '.join(filter(None,returns))}

def classify(title, category):
    t = (title + ' ' + category).lower(); result = []
    if re.search(r'\b(sealed|hobby box|blaster|booster box|booster pack|mega box|elite trainer|factory set|breakers delight)\b', t): result.append('Sealed Products')
    if re.search(r'\b(memorabilia|jersey|helmet|signed ball|signed bat|signed photo)\b', t): result.append('Memorabilia')
    sports = [('Football',r'football|\bnfl\b'),('Basketball',r'basketball|\bnba\b|\bwnba\b'),('Baseball',r'baseball|\bmlb\b'),('Soccer',r'soccer|\bfifa\b|\buefa\b')]
    if 'pokémon' in t or 'pokemon' in t or 'pok mon' in t: result.append('Pokémon')
    else:
        for name, pattern in sports:
            if re.search(pattern, t): result.append(name); break
        else:
            if re.search(r'\btc[g]?\b|magic:|magic the gathering|yu-gi-oh|yugioh|lorcana|one piece|digimon|flesh and blood', t): result.append('Other TCG')
    return result or ['Other Collectibles']

def request_json(url, data, headers):
    req = urllib.request.Request(url, data=data, headers=headers, method='POST')
    with urllib.request.urlopen(req, timeout=45) as r: return json.load(r)

class Ebay:
    def __init__(self):
        client, secret, refresh = (os.environ.get(k,'') for k in ('EBAY_CLIENT_ID','EBAY_CLIENT_SECRET','EBAY_REFRESH_TOKEN'))
        if not all((client, secret, refresh)): raise RuntimeError('Missing eBay authorization. Configure the three repository secrets listed in README.md.')
        auth = base64.b64encode((client+':'+secret).encode()).decode()
        result = request_json('https://api.ebay.com/identity/v1/oauth2/token', urllib.parse.urlencode({'grant_type':'refresh_token','refresh_token':refresh,'scope':'https://api.ebay.com/oauth/api_scope'}).encode(), {'Authorization':'Basic '+auth,'Content-Type':'application/x-www-form-urlencoded'})
        self.token = result['access_token']
    def call(self, name, fields):
        root = ET.Element(name+'Request', xmlns=URN)
        def add(parent, data):
            for key, val in data.items():
                e = ET.SubElement(parent,key)
                if isinstance(val, dict): add(e,val)
                else: e.text = str(val)
        add(root, fields)
        req = urllib.request.Request(getattr(self,'api_url','https://api.ebay.com/ws/api.dll'),data=ET.tostring(root),headers={'Content-Type':'text/xml','X-EBAY-API-CALL-NAME':name,'X-EBAY-API-SITEID':'0','X-EBAY-API-COMPATIBILITY-LEVEL':'1489','X-EBAY-API-IAF-TOKEN':self.token})
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req,timeout=60) as r: response=ET.fromstring(r.read())
                if text_at(response,'e:Ack') not in ('Success','Warning'): raise RuntimeError('eBay rejected '+name+'; check seller authorization and API status.')
                return response
            except (TimeoutError, urllib.error.URLError):
                if attempt == 2: raise RuntimeError('eBay is temporarily unavailable.') from None
                time.sleep(2 ** attempt)

def export(api, previous, now):
    identity = api.call('GetUser', {})
    seller = text_at(identity,'e:User/e:UserID')
    if seller.lower() != os.environ.get('EBAY_SELLER_ID','hobbyreservecollectibles').lower():
        raise RuntimeError('Authorized seller does not match EBAY_SELLER_ID. No inventory was published.')
    active = []; page = 1; pages = 1
    while page <= pages:
        response = api.call('GetMyeBaySelling',{'ActiveList':{'Include':'true','Pagination':{'EntriesPerPage':200,'PageNumber':page}},'SoldList':{'Include':'false'},'UnsoldList':{'Include':'false'},'ScheduledList':{'Include':'false'}})
        pages = int(text_at(response,'e:ActiveList/e:PaginationResult/e:TotalNumberOfPages','0'))
        count = int(text_at(response,'e:ActiveList/e:PaginationResult/e:TotalNumberOfEntries','0'))
        if count >= 25000: raise RuntimeError('eBay pagination limit reached; export needs an alternate inventory API.')
        active.extend(response.findall('e:ActiveList/e:ItemArray/e:Item', NS)); page += 1
    cached = {p['id']:p for p in previous.get('products',[]) if p.get('id')}
    featured = set(filter(None,os.environ.get('FEATURED_ITEM_IDS','').split(',')))
    products = []
    for item in active:
        item_id = text_at(item,'e:ItemID')
        if not re.fullmatch(r'\d+',item_id): raise RuntimeError('Invalid eBay item identifier.')
        old = cached.get(item_id,{})
        fresh_detail = old.get('descriptionUpdatedAt') and (now - datetime.fromisoformat(old['descriptionUpdatedAt'].replace('Z','+00:00'))) < timedelta(hours=24)
        if fresh_detail: detail = old
        else:
            response = api.call('GetItem',{'ItemID':item_id,'DetailLevel':'ReturnAll','IncludeItemSpecifics':'true'})
            found = response.find('e:Item',NS)
            if found is None: raise RuntimeError('An eBay item response was incomplete.')
            if text_at(found,'e:Seller/e:UserID').lower() != seller.lower(): raise RuntimeError('Unexpected seller in item response.')
            detail = details_from_item(found,now)
            time.sleep(.15)
        title = text_at(item,'e:Title'); price_node = item.find('e:SellingStatus/e:CurrentPrice',NS)
        if price_node is None or price_node.attrib.get('currencyID') != 'USD': raise RuntimeError('Missing price or unsupported currency; export stopped.')
        price = float(price_node.text)
        if price < 0 or not __import__('math').isfinite(price): raise RuntimeError('Invalid price.')
        p = {**detail,'id':item_id,'title':title,'price':price,'currency':'USD','url':'https://www.ebay.com/itm/'+item_id,'categories':classify(title,detail.get('categoryName','')),'featured':item_id in featured,'startTime':text_at(item,'e:ListingDetails/e:StartTime'),'endTime':text_at(item,'e:ListingDetails/e:EndTime'),'listingType':'auction' if text_at(item,'e:ListingType') in ('Chinese','Dutch') else 'fixed'}
        available = text_at(item,'e:QuantityAvailable')
        if available.isdigit(): p['quantity'] = int(available)
        if not p['image']: p['image'] = text_at(item,'e:PictureDetails/e:GalleryURL')
        products.append(p)
    unique = {p['id']:p for p in products}
    return {'status':'ok','updatedAt':now.isoformat(),'seller':seller,'products':list(unique.values())}

def main():
    path = Path(os.environ.get('INVENTORY_PATH','data/inventory.json')); previous = json.loads(path.read_text()) if path.exists() else {}
    payload = export(Ebay(),previous,datetime.now(timezone.utc))
    path.parent.mkdir(parents=True,exist_ok=True)
    temp = path.with_suffix('.tmp'); temp.write_text(json.dumps(payload,ensure_ascii=False,indent=2)); temp.replace(path)
    print('Published snapshot with',len(payload['products']),'active listings.')

if __name__ == '__main__':
    try: main()
    except Exception as exc:
        # Never print provider response bodies, request objects, or credentials.
        print('Inventory sync failed. Previous snapshot was preserved. Check authorization, API availability, and export validation.',file=sys.stderr)
        sys.exit(1)

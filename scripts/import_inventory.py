"""Import a seller-provided CSV or JSON export; validate coverage before replacement.

Example: python3 scripts/import_inventory.py export.csv --expected-count 357
Only customer-facing listing fields are copied. No buyer/customer fields are published.
"""
import argparse
import csv
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
from urllib.parse import urlparse
from sync_inventory import classify, plain

def normalized(value): return re.sub(r'[^a-z0-9]','',str(value).lower())
def pick(row,*names):
    normalized_row = {normalized(k):v for k,v in row.items()}
    return next((normalized_row[normalized(n)] for n in names if normalized(n) in normalized_row and normalized_row[normalized(n)] not in ('',None)), '')
def photo_urls(value):
    values = value if isinstance(value,list) else re.split(r'[|;\s]+',str(value))
    valid = []
    for s in values:
        u=urlparse(s)
        if u.scheme=='https' and (u.hostname=='ebayimg.com' or (u.hostname or '').endswith('.ebayimg.com')): valid.append(s)
    return list(dict.fromkeys(valid))

def convert(rows, previous, expected, require_descriptions=False):
    old={p['id']:p for p in previous.get('products',[])};result={};missing_photos=[];missing_descriptions=[];review=[]
    for line,row in enumerate(rows,2):
        status=str(pick(row,'status','listing status')).lower()
        if status and status not in ('active','listed','scheduled'): continue
        if status=='scheduled': continue
        item_id=str(pick(row,'id','item id','item number','itemid')).strip()
        if item_id.endswith('.0'): item_id=item_id[:-2]
        if not re.fullmatch(r'\d{9,15}',item_id): raise ValueError(f'Row {line}: missing or invalid eBay item number.')
        if item_id in result: raise ValueError(f'Duplicate item number {item_id}; consolidate variation rows before importing.')
        title=str(pick(row,'title','item title','listing title')).strip()
        if not title: raise ValueError(f'Item {item_id}: title is missing.')
        amount=re.sub(r'[^\d.\-]','',str(pick(row,'price','current price','start price','buy it now price')))
        price=float(amount)
        if not math.isfinite(price) or price<0: raise ValueError(f'Item {item_id}: invalid price.')
        currency=str(pick(row,'currency','currency id') or 'USD').upper()
        if currency!='USD': raise ValueError(f'Item {item_id}: unsupported currency {currency}.')
        cached=old.get(item_id,{})
        images=photo_urls(pick(row,'images','picture urls','picurl','item photo url','image urls','image','image url','picture url')) or photo_urls([cached.get('image',''),*cached.get('images',[])])
        if not images: missing_photos.append(item_id)
        description=plain(str(pick(row,'description','item description','listing description') or cached.get('description','')))
        if not description: missing_descriptions.append(item_id)
        category_name=str(pick(row,'category name','category','store category'))
        categories=pick(row,'categories')
        if not isinstance(categories,list): categories=cached.get('categories') or classify(title,category_name)
        if categories==['Other Collectibles']:review.append(item_id)
        specifics=pick(row,'itemSpecifics')
        if not isinstance(specifics,dict):specifics={k[2:]:str(v) for k,v in row.items() if str(k).startswith('C:') and v}
        p={'id':item_id,'title':title,'price':price,'currency':'USD','url':'https://www.ebay.com/itm/'+item_id,'image':images[0] if images else '', 'images':images,'description':description,'categories':categories,'condition':str(pick(row,'condition','condition display name') or cached.get('condition','')),'itemSpecifics':specifics,'listingType':'auction' if 'auction' in str(pick(row,'listing type','format','listingType')).lower() else 'fixed','featured':bool(cached.get('featured',False))}
        quantity=str(pick(row,'quantity','available quantity','quantity available'))
        if quantity.isdigit():p['quantity']=int(quantity)
        for key,names in [('startTime',('startTime','start date')),('endTime',('endTime','end date'))]:
            value=pick(row,*names)
            if value:p[key]=str(value)
        result[item_id]=p
    if len(result)!=expected:raise ValueError(f'Found {len(result)} unique active listings; expected {expected}. Existing inventory was not replaced.')
    if missing_photos:raise ValueError(f'{len(missing_photos)} listings lack photo URLs, including '+', '.join(missing_photos[:8])+'. Export does not contain complete image data; existing inventory was not replaced.')
    if require_descriptions and missing_descriptions:raise ValueError(f'{len(missing_descriptions)} listings lack descriptions. Existing inventory was not replaced.')
    report={'count':len(result),'missingDescriptions':missing_descriptions,'categoryReview':review}
    return {'status':'ok','source':'seller_export','coverage':'complete','storeListingCount':expected,'updatedAt':datetime.now(timezone.utc).isoformat(),'products':list(result.values())},report

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('export');parser.add_argument('--expected-count',type=int,required=True);parser.add_argument('--output',default='public/inventory.json');parser.add_argument('--require-descriptions',action='store_true');args=parser.parse_args()
    source=Path(args.export);out=Path(args.output)
    previous=json.loads(out.read_text()) if out.exists() else {}
    if source.suffix.lower()=='.json':
        raw=json.loads(source.read_text(encoding='utf-8-sig'));rows=raw['products'] if isinstance(raw,dict) else raw
    elif source.suffix.lower()=='.csv':
        with source.open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
    else:raise ValueError('Supported export formats: CSV and JSON.')
    payload,report=convert(rows,previous,args.expected_count,args.require_descriptions)
    tmp=out.with_suffix('.tmp');tmp.write_text(json.dumps(payload,ensure_ascii=False,indent=2));tmp.replace(out)
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()

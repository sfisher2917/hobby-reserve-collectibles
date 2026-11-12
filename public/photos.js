import {safeUrl} from './catalog.js';

// Trading API $_1.JPG URLs are 300×400 thumbnails. Use the same photo's
// full-size CDN endpoint; never alter or synthesize the photographed card.
export function photoCandidates(value){
 const original=safeUrl(value,'image');if(!original)return [];
 const url=new URL(original),match=url.pathname.match(/\/(?:images\/g|z)\/([A-Za-z0-9_-]+)\//);
 if(!match)return [original];
 return [...new Set([`https://i.ebayimg.com/images/g/${match[1]}/s-l2000.jpg`,`https://i.ebayimg.com/images/g/${match[1]}/s-l1600.jpg`,original])];
}
export function productPhotos(product){
 const photos=[],seen=new Set();
 for(const value of [...product.images||[],product.image]){
  const candidates=photoCandidates(value);if(!candidates.length||seen.has(candidates[0]))continue;
  seen.add(candidates[0]);photos.push(value);
 }
 return photos;
}
export function loadPhoto(img,value,{onload,onerror}={}){
 const candidates=photoCandidates(value);let index=0;
 const next=()=>{if(index>=candidates.length){img.onload=null;img.onerror=null;onerror?.();return}img.src=candidates[index++]};
 img.decoding='async';
 img.onload=()=>{
  // Unsupported eBay size variants can return an 80px placeholder with HTTP 200.
  if(img.naturalWidth<=96&&img.naturalHeight<=96&&index<candidates.length){next();return}
  img.dataset.resolution=`${img.naturalWidth}×${img.naturalHeight}`;onload?.(img.currentSrc||img.src);
 };
 img.onerror=next;next();
}

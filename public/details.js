import {safeUrl} from './catalog.js';
import {requestLive} from './inventory-api.js?v=production-live-20261112';
import {loadPhoto,productPhotos,photoCandidates} from './photos.js?v=gallery-20261112';
const el=(tag,cls,text)=>{const n=document.createElement(tag);if(cls)n.className=cls;if(text!=null)n.textContent=text;return n};
const money=n=>new Intl.NumberFormat('en-US',{style:'currency',currency:'USD'}).format(n);
let dialog,lightbox,previousHash='',opener,generation=0;

function ensureDialog(){
 if(dialog)return;
 dialog=el('dialog','product-dialog');dialog.setAttribute('aria-labelledby','detail-title');document.body.append(dialog);
 dialog.addEventListener('click',e=>{if(e.target===dialog){const r=dialog.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)dialog.close()}});
 dialog.addEventListener('close',()=>{generation++;if(lightbox?.open)lightbox.close();dialog.replaceChildren();document.body.classList.remove('modal-open');history.replaceState(null,'',location.pathname+location.search+previousHash);opener?.focus({preventScroll:true})});
}
export async function openProduct(product,updatedAt,source){
 ensureDialog();const request=++generation;
 if(!dialog.open){opener=document.activeElement;previousHash=location.hash}
 showProduct(product,updatedAt,{pending:true});
 try{
  const data=await requestLive('/api/items/'+encodeURIComponent(product.id));
  if(data.source!=='ebay_live'||data.product?.id!==product.id)throw Error();
  if(request===generation&&dialog.open)showProduct(data.product,data.updatedAt);
 }catch(error){
  if(request!==generation||!dialog.open)return;
  const gone=[404,410].includes(error.status);
  showProduct(product,updatedAt,{error:gone?'This listing is no longer available.':'We couldn’t verify the latest details. Please check the listing on eBay.'});
  if(gone)window.dispatchEvent(new CustomEvent('inventory-item-unavailable',{detail:product.id}));
 }
}
function accordion(label,content,open=false){
 const section=el('details','detail-section');section.open=open;section.append(el('summary','',label),content);return section;
}
function showProduct(p,updatedAt,{pending=false,error=''}={}){
 dialog.replaceChildren();
 const header=el('div','detail-header');header.append(el('span','eyebrow','HOBBY RESERVE · ITEM DETAILS'));
 const close=el('button','detail-close','Close ×');close.type='button';close.setAttribute('aria-label','Close product details');close.onclick=()=>dialog.close();header.append(close);
 const layout=el('div','detail-layout'),gallery=el('div','detail-gallery'),photos=productPhotos(p);
 let selected=0;const imageButton=el('button','photo-open');imageButton.type='button';imageButton.disabled=pending||!photos.length;imageButton.setAttribute('aria-label','Enlarge product photo');
 const image=el('img','detail-photo');image.alt=p.title;image.fetchPriority='high';const hint=el('span','photo-hint',pending?'Loading current details…':'Enlarge photo ›');
 imageButton.append(image,hint);gallery.append(imageButton);
 const status=el('p','gallery-caption',photos.length?`Photo 1 of ${photos.length}`:'Photos available on eBay');status.setAttribute('aria-live','polite');
 const thumbs=el('div','detail-thumbs');thumbs.setAttribute('aria-label','Product photos');
 function select(index){
  selected=index;image.classList.add('is-loading');
  loadPhoto(image,photos[index],{onload:()=>image.classList.remove('is-loading'),onerror:()=>{image.classList.remove('is-loading');hint.textContent='View photo on eBay'}});
  status.textContent=`Photo ${index+1} of ${photos.length}`;
  for(const [i,button]of [...thumbs.children].entries())button.setAttribute('aria-pressed',String(i===index));
 }
 photos.forEach((photo,index)=>{
  const button=el('button','detail-thumb');button.type='button';button.setAttribute('aria-label',`View photo ${index+1}`);button.setAttribute('aria-pressed',String(index===0));
  const thumb=el('img');thumb.alt=`Product photo ${index+1}`;loadPhoto(thumb,photo);button.append(thumb);button.onclick=()=>select(index);thumbs.append(button);
 });
 if(photos.length){select(0);gallery.append(status);if(photos.length>1)gallery.append(thumbs)}else image.hidden=true;
 imageButton.onclick=()=>openLightbox(photos,selected,p.title,imageButton);
 gallery.append(el('p','gallery-note','Actual seller photos. Select an image for a closer look.'));
 const info=el('div','detail-info');info.setAttribute('aria-busy',String(pending));
 info.append(el('p','eyebrow',pending?'VERIFYING LIVE LISTING':error?'LISTING UPDATE':'FROM THE RESERVE'));
 const title=el('h2','',p.title);title.id='detail-title';info.append(title);
 const price=el('p','price',money(p.price));price.append(el('small','',p.listingType==='auction'?'Current bid · USD':'Listed price · USD'));info.append(price);
 const quick=el('div','detail-quick-facts');
 for(const [label,value]of [['Condition',p.condition],['Available',p.quantity!=null?`${p.quantity}`:null],['Format',p.listingType==='auction'?'Auction':'Fixed price']]){
  if(value){const fact=el('div');fact.append(el('span','',label),el('strong','',value));quick.append(fact)}
 }
 if(quick.children.length)info.append(quick);
 const note=el('p',pending?'detail-status is-pending':error?'detail-status is-error':'detail-status',pending?'Checking the latest photos, description and availability…':error||'Current listing information, retrieved directly from eBay.');note.setAttribute('role','status');info.append(note);
 if(!pending&&!error){
  const desc=el('div','detail-section-content');desc.append(el('p','',p.description||'Please view the eBay listing for the seller’s description.'));info.append(accordion('Description',desc,true));
  const facts=el('dl','detail-facts');
  const fact=(key,value)=>{if(value!==undefined&&value!==null&&String(value).trim()!=='')facts.append(el('dt','',key),el('dd','',String(value)))};
  for(const [key,value]of Object.entries(p.itemSpecifics||{}))fact(key,Array.isArray(value)?value.join(', '):value);
  fact('eBay item number',p.id);
  for(const [key,value]of [['Listed',p.startTime],['Ends',p.endTime]])if(value&&Number.isFinite(Date.parse(value)))fact(key,new Date(value).toLocaleString());
  if(facts.children.length)info.append(accordion('Card & listing details',facts));
  const shipping=el('div','detail-section-content');
  if(p.shipping?.length)for(const s of p.shipping)shipping.append(el('p','',[s.service,s.cost!=null?money(s.cost):null].filter(Boolean).join(' · ')));
  if(p.returns)shipping.append(el('p','',p.returns));
  shipping.append(el('p','','Shipping, taxes, delivery and return terms are confirmed on the eBay listing.'));info.append(accordion('Shipping & returns',shipping));
 }
 if(updatedAt)info.append(el('p','detail-capture',`Last checked ${new Date(updatedAt).toLocaleString()}. Final price and availability are confirmed on eBay.`));
 layout.append(gallery,info);
 const purchase=el('div','detail-purchase'),purchasePrice=el('div','purchase-price',money(p.price));purchasePrice.append(el('small','',p.listingType==='auction'?'Current bid':'Secure checkout on eBay'));
 const buy=el('a','button',pending?'View listing on eBay ›':error?'Check listing on eBay ›':p.listingType==='auction'?'View auction on eBay ›':'View & buy on eBay ›');buy.href=safeUrl(p.url);buy.target='_blank';buy.rel='noopener noreferrer';purchase.append(purchasePrice,buy);
 dialog.append(header,layout,purchase);history.replaceState(null,'','#item-'+p.id);document.body.classList.add('modal-open');
 if(!dialog.open)dialog.showModal();close.focus({preventScroll:true});
}
function openLightbox(photos,index,title,returnFocus){
 if(!lightbox){lightbox=el('dialog','photo-lightbox');lightbox.setAttribute('aria-label','Full-resolution product photos');document.body.append(lightbox)}
 lightbox.replaceChildren();let selected=index,zoomed=false;
 const header=el('div','lightbox-header'),counter=el('span','lightbox-counter'),tools=el('div','lightbox-tools');
 const zoom=el('button','lightbox-control','Zoom in');zoom.type='button';zoom.setAttribute('aria-pressed','false');
 const original=el('a','lightbox-original','Open full photo ›');original.target='_blank';original.rel='noopener noreferrer';
 const close=el('button','lightbox-control','Close ×');close.type='button';close.setAttribute('aria-label','Close full photo');close.onclick=()=>lightbox.close();tools.append(zoom,original,close);header.append(counter,tools);
 const stage=el('div','lightbox-stage'),image=el('img','lightbox-image');image.alt=title;stage.append(image);
 const footer=el('div','lightbox-footer'),prev=el('button','lightbox-control','← Previous'),next=el('button','lightbox-control','Next →');prev.type=next.type='button';
 const caption=el('p','',title);footer.append(prev,caption,next);
 function show(i){
  selected=(i+photos.length)%photos.length;zoomed=false;stage.classList.remove('is-zoomed');zoom.setAttribute('aria-pressed','false');zoom.textContent='Zoom in';stage.scrollTop=stage.scrollLeft=0;
  counter.textContent=`${selected+1} / ${photos.length}`;original.href=photoCandidates(photos[selected])[0];loadPhoto(image,photos[selected],{onload:src=>{original.href=src}});
 }
 zoom.onclick=()=>{zoomed=!zoomed;stage.classList.toggle('is-zoomed',zoomed);zoom.textContent=zoomed?'Fit to screen':'Zoom in';zoom.setAttribute('aria-pressed',String(zoomed))};
 prev.onclick=()=>show(selected-1);next.onclick=()=>show(selected+1);prev.disabled=next.disabled=photos.length<2;
 lightbox.onkeydown=e=>{if(e.key==='ArrowLeft'){e.preventDefault();show(selected-1)}if(e.key==='ArrowRight'){e.preventDefault();show(selected+1)}};
 lightbox.onclose=()=>{lightbox.replaceChildren();returnFocus.focus({preventScroll:true})};
 lightbox.append(header,stage,footer);show(selected);lightbox.showModal();close.focus();
}

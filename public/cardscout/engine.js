export const DEFAULT_WEIGHTS = {reference:40,autos:35,budget:25,chase:0};
export function effectivePrice(d, opts={}) {
 if(!Number.isFinite(d.asking)||d.asking<=0)return null;
 const shipping=Number.isFinite(d.shipping)?d.shipping:Math.max(0,Number(opts.shipping)||0);
 return (d.asking+shipping)*(1+Math.max(0,Number(opts.tax)||0)/100);
}
export function chaseMid(d){return d.chase && Number.isFinite(d.chase.low)&&Number.isFinite(d.chase.high)?(d.chase.low+d.chase.high)/2:null;}
const clamp=x=>Math.max(0,Math.min(100,x));
export function metrics(d,opts={}){
 const price=effectivePrice(d,opts);
 if(price===null)return {price:null,score:null,components:{}};
 if(d.sport==='TCG'||['announced','preorder','soldout'].includes(d.status)){const ref=d.reference??d.retail;return {price,score:null,components:{},costPerAuto:d.autos>0?price/d.autos:null,discount:ref>0?(ref-price)/ref*100:null};}
 const ref=d.reference??d.retail;
 const components={reference:ref>0?clamp(50+100*(ref-price)/ref):0,autos:clamp(d.autos*10000/price),budget:10000/(100+price),chase:chaseMid(d)!==null?clamp(chaseMid(d)/price*10):0};
 const w=opts.weights??DEFAULT_WEIGHTS;
 const total=Object.values(w).reduce((a,b)=>a+Math.max(0,Number(b)||0),0);
 return {price,components,score:total>0?Object.entries(components).reduce((sum,[k,v])=>sum+v*Math.max(0,Number(w[k])||0),0)/total:0,missingReference:!(ref>0),costPerAuto:d.autos>0?price/d.autos:null,discount:ref>0?(ref-price)/ref*100:null};
}
export function rangeMatch(value,min,max){
 const lo=min!==''&&min!==null&&min!==undefined?Number(min):null;
 const hi=max!==''&&max!==null&&max!==undefined?Number(max):null;
 if(lo===null&&hi===null)return true;
 if(!Number.isFinite(value))return false;
 return (lo===null||value>=lo)&&(hi===null||value<=hi);
}
export function filterListings(rows,f={},opts={}){
 return rows.filter(d=>d.licensed===true)
 .filter(d=>!f.sport||f.sport==='All'||d.sport===f.sport)
 .filter(d=>!f.brand||f.brand==='All'||d.brand===f.brand)
 .filter(d=>!f.family||f.family==='All'||d.family===f.family)
 .filter(d=>!f.collection||f.collection==='All'||(f.collection==='upcoming'?['announced','preorder'].includes(d.status):d.collection===f.collection))
 .filter(d=>!f.type||f.type==='All'||d.type===f.type)
 .filter(d=>!f.available||d.status!=='soldout')
 .filter(d=>!f.verified||d.status==='listed')
 .filter(d=>!f.saved||f.savedIds?.includes(d.id))
 .filter(d=>!f.belowRetail||(d.retail>0&&effectivePrice(d,opts)!==null&&effectivePrice(d,opts)<=d.retail))
 .filter(d=>!f.query||`${d.title} ${d.brand} ${d.year} ${d.sport} ${d.source} ${d.family||''} ${d.license||''} ${d.chaseNames}`.toLowerCase().includes(f.query.trim().toLowerCase()))
 .filter(d=>rangeMatch(effectivePrice(d,opts),f.priceMin,f.priceMax))
 .filter(d=>rangeMatch(d.asking,f.askMin,f.askMax))
 .filter(d=>rangeMatch(d.retail,f.retailMin,f.retailMax))
 .filter(d=>rangeMatch(d.autos,f.autoMin,f.autoMax))
 .filter(d=>rangeMatch(chaseMid(d),f.chaseMin,f.chaseMax));
}
export function rankListings(rows,sort='value',opts={}){
 const byValue=(a,b)=>(metrics(b,opts).score??-1)-(metrics(a,opts).score??-1);
 return [...rows].sort((a,b)=>{
 // Unavailable products never outrank a currently listed product.
 if(sort==='newest'){const era=Number(b.collection==='current')-Number(a.collection==='current');if(era)return era;const dates=(b.releaseDate||b.year?.slice(0,4)||'').localeCompare(a.releaseDate||a.year?.slice(0,4)||'');if(dates)return dates;}
 const availability=Number(a.status==='soldout')-Number(b.status==='soldout');
 if(availability)return availability;
 const ma=metrics(a,opts),mb=metrics(b,opts);
 let order=0;
 if(sort==='price')order=(ma.price??Infinity)-(mb.price??Infinity);
 else if(sort==='autos')order=(ma.costPerAuto??Infinity)-(mb.costPerAuto??Infinity);
 else if(sort==='discount')order=(mb.discount??-Infinity)-(ma.discount??-Infinity);
 else if(sort==='chase')order=(chaseMid(b)??-1)-(chaseMid(a)??-1);
 else order=byValue(a,b);
 return (Number.isNaN(order)?0:order)||byValue(a,b)||((ma.price??Infinity)-(mb.price??Infinity))||a.id.localeCompare(b.id);
 });
}

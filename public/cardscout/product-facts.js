// Only publish product facts supported by a recorded value; zero autos means unstated.
export function productFacts(d, total) {
 const facts=[];
 const positive=n=>Number.isFinite(n)&&n>0;
 const money=n=>new Intl.NumberFormat('en-US',{style:'currency',currency:'USD'}).format(n);
 if(positive(d.retail))facts.push({key:'retail',label:'Retail price',value:money(d.retail),note:d.isEdited?'Your retail assumption':'Retail reference · see source'});
 if(d.sport!=='TCG'&&positive(d.autos))facts.push({key:'autos',label:'Autographs / product',value:d.autos+' on average',note:positive(total)?money(total/d.autos)+' per average autograph · averages are not guarantees':'Stated average · not a guarantee'});
 const reference=positive(d.reference)?d.reference:d.retail;
 if(positive(reference)&&positive(total)){const discount=(reference-total)/reference*100;facts.push({key:'reference',label:'Vs. reference price',value:Math.abs(discount).toFixed(0)+'% '+(discount>=0?'below':'above'),note:money(reference)+' · '+(d.referenceKind||'Retail reference')});}
 if(d.chase&&Number.isFinite(d.chase.low)&&Number.isFinite(d.chase.high)&&d.chase.low>=0&&d.chase.high>=d.chase.low)facts.push({key:'chase',label:'Estimated chase value',value:d.chase.low===d.chase.high?money(d.chase.low):money(d.chase.low)+'–'+money(d.chase.high),note:d.chase.userEstimate?'Your scenario · uncertain':d.chase.label||'Historical comp · not box value'});
 return facts;
}

import {test} from 'node:test';
import assert from 'node:assert/strict';
import {productFacts} from '../public/cardscout/product-facts.js';
import {LISTINGS} from '../public/cardscout/data.js';
import {effectivePrice} from '../public/cardscout/engine.js';
test('missing retail, unstated autos, reference and chase are omitted entirely',()=>{assert.deepEqual(productFacts({autos:0,retail:null,reference:null,chase:null},50),[]);});
test('all four available facts retain pricing, average count and historical context',()=>{const f=productFacts({retail:100,autos:2,reference:100,chase:{low:50,high:80,label:'PSA 10 historical sale'}},80);assert.deepEqual(f.map(x=>x.key),['retail','autos','reference','chase']);assert.equal(f[2].value,'20% below');assert.match(f[1].note,/40.00/);assert.match(f[3].note,/PSA 10/);});
test('TCG omits autograph fields and estimates stay labeled',()=>{const f=productFacts({sport:'TCG',autos:2,chase:{low:5,high:10,userEstimate:true}},25);assert.equal(f.length,1);assert.equal(f[0].note,'Your scenario · uncertain');});
test('every catalog item publishes only available facts, without unknown placeholders',()=>{for(const d of LISTINGS){const f=productFacts(d,effectivePrice(d));assert.ok(!/Unknown|No verified|Missing reference|Unpriced|0 stated minimum/.test(JSON.stringify(f)));assert.equal(f.some(x=>x.key==='retail'),Number.isFinite(d.retail)&&d.retail>0);assert.equal(f.some(x=>x.key==='autos'),d.sport!=='TCG'&&d.autos>0);}});

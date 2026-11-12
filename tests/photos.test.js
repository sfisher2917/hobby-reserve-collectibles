import test from 'node:test';
import assert from 'node:assert/strict';
import {photoCandidates,productPhotos,loadPhoto} from '../public/photos.js';

const legacy='https://i.ebayimg.com/00/s/OTYwWDcyMA==/z/gEIAAeSwMPJq36Yf/$_1.JPG?set_id=8800005007';
test('detail thumbnails resolve to the same photo at full source resolution',()=>{
 const candidates=photoCandidates(legacy);
 assert.equal(candidates[0],'https://i.ebayimg.com/images/g/gEIAAeSwMPJq36Yf/s-l2000.jpg');
 assert.equal(candidates[1],'https://i.ebayimg.com/images/g/gEIAAeSwMPJq36Yf/s-l1600.jpg');
 assert.equal(candidates.at(-1),legacy);
});
test('cover and detail variants do not produce duplicate gallery photos',()=>{
 assert.equal(productPhotos({image:'https://i.ebayimg.com/images/g/gEIAAeSwMPJq36Yf/s-l1600.jpg',images:[legacy]}).length,1);
 assert.equal(productPhotos({image:legacy,images:[legacy,'https://i.ebayimg.com/images/g/second/s-l500.jpg']}).length,2);
});
test('unsupported size placeholders and network errors fall back without inventing images',()=>{
 const image={dataset:{},naturalWidth:80,naturalHeight:80};let loaded='';
 loadPhoto(image,legacy,{onload:src=>loaded=src});
 assert.match(image.src,/s-l2000/);image.onload();assert.match(image.src,/s-l1600/);
 image.naturalWidth=720;image.naturalHeight=960;image.onload();
 assert.match(loaded,/s-l1600/);assert.equal(image.dataset.resolution,'720×960');
});
test('unknown but valid eBay image paths retain the source; unsafe hosts are rejected',()=>{
 assert.deepEqual(photoCandidates('https://i.ebayimg.com/custom/original.jpg'),['https://i.ebayimg.com/custom/original.jpg']);
 for(const value of ['javascript:alert(1)','https://evil.example/photo.jpg','https://ebayimg.com.evil.example/z/key/a.jpg','http://i.ebayimg.com/photo.jpg'])assert.deepEqual(photoCandidates(value),[]);
});

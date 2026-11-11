import{access,readdir,cp,mkdir}from'node:fs/promises';for(const name of['index.html','styles.css','app.js','catalog.js','inventory.json','assets/hobby-reserve-logo.webp'])await access(new URL('../public/'+name,import.meta.url));console.log('Static storefront validated. No dependencies or compilation required.');

await mkdir(new URL('../dist/',import.meta.url),{recursive:true});await cp(new URL('../public/',import.meta.url),new URL('../dist/',import.meta.url),{recursive:true});

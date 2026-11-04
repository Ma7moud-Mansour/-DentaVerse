// Automated local artifact rendering; does not access a user browser profile.
import fs from 'node:fs/promises';
import path from 'node:path';
import http from 'node:http';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const require=createRequire(path.join(root,'frontend/package.json'));const {chromium}=require('@playwright/test');
const doc=await fs.readFile(path.join(root,'deliverables/DentaVerse_Figma_Kit/preview.html'));
const server=http.createServer((req,res)=>{if(req.url==='/'||req.url==='/preview.html'){res.setHeader('Content-Type','text/html;charset=utf-8');res.end(doc);}else{res.statusCode=404;res.end();}});
await new Promise(r=>server.listen(0,'127.0.0.1',r));let browser;
try{browser=await chromium.launch({channel:'msedge',args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});const page=await browser.newPage({viewport:{width:1440,height:1040}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
 const base='http://127.0.0.1:'+server.address().port;await page.goto(base);await fs.mkdir(path.join(root,'.review/ui'),{recursive:true});
 for(const id of ['studio','workbench_hand','bluetooth']){
  await page.locator('#screen').selectOption(id);await page.waitForFunction(v=>location.hash==='#'+v,id);await page.screenshot({path:path.join(root,'.review/ui/figma-'+id+'.png')});
 }
 await page.locator('#screen').selectOption('studio');await page.locator('svg a[href="#atlas"]').first().click();await page.waitForFunction(()=>location.hash==='#atlas');
 await page.locator('#all').click();await page.screenshot({path:path.join(root,'.review/ui/figma-overview.png')});if(errors.length)throw Error(errors.join('\n'));
 console.log('Local SVG preview rendered; Studio → Atlas link verified. Not a Figma editor test.');
}finally{if(browser)await browser.close();await new Promise(r=>server.close(r));}

// Local importer contract check, not a real Figma editor verification.
import fs from 'node:fs/promises';
import vm from 'node:vm';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const code=await fs.readFile(path.join(root,'deliverables/DentaVerse_Figma_Kit/code.js'),'utf8');
let id=0;const all=[],links=[];const pages=[];
class Node {
 constructor(type){this.type=type;this.id=String(++id);this.children=[];this.width=100;this.height=100;all.push(this);}
 appendChild(n){if(n.parent)n.parent.children=n.parent.children.filter(v=>v!==n);n.parent=this;this.children.push(n);}
 resize(w,h){if(!(w>0&&h>0))throw Error('Invalid size');this.width=w;this.height=h;}
 setPluginData(k,v){(this.data??={})[k]=v;}
 findOne(predicate){for(const c of this.children){if(predicate(c))return c;const child=c.findOne(predicate);if(child)return child;}return null;}
 createInstance(){const copy=(old)=>{const n=new Node(old.type);for(const k of ['name','characters','fontName','fontSize','textAutoResize','fills','x','y'])if(k in old)n[k]=old[k];n.resize(old.width,old.height);old.children.forEach(c=>n.appendChild(copy(c)));return n;};const n=copy(this);n.type='INSTANCE';return n;}
 async setReactionsAsync(reactions){links.push({source:this.id,target:reactions[0].actions[0].destinationId});}
}
const figma={editorType:'figma',async loadFontAsync(){},createPaintStyle:()=>({id:'style'+(++id)}),createTextStyle:()=>({id:'text'+(++id)}),
 createImage(bytes){if(bytes[0]!==137||bytes[1]!==80)throw Error('Invalid PNG');return {hash:'licensed-model'};},base64Decode:s=>Uint8Array.from(Buffer.from(s,'base64')),
 createPage(){const p=new Node('PAGE');pages.push(p);return p;},async setCurrentPageAsync(p){this.currentPage=p;},
 createText:()=>new Node('TEXT'),createRectangle:()=>new Node('RECTANGLE'),createFrame:()=>new Node('FRAME'),createComponent:()=>new Node('COMPONENT'),
 createNodeFromSvg(svg){if(!svg.startsWith('<svg '))throw Error('Invalid SVG');return new Node('FRAME');},
 combineAsVariants(nodes,parent){const n=new Node('COMPONENT_SET');parent.appendChild(n);nodes.forEach(v=>n.appendChild(v));return n;},viewport:{scrollAndZoomIntoView(){}},
 closePlugin(message){if(!message.startsWith('Created '))throw Error(message);},};
// In Figma each create* call automatically parents to the current page.
for(const name of ['createText','createRectangle','createFrame','createComponent']){
 const make=figma[name];figma[name]=()=>{const n=make();figma.currentPage?.appendChild(n);return n;};
}
await vm.runInNewContext(code,{figma,console:{log(){},error(e){throw e;}}});
const screens=pages.find(p=>p.name==='DentaVerse / Phase II screens');
if(screens.children.length!==17)throw Error('Expected 17 screens');
if(all.filter(n=>n.type==='COMPONENT').length!==9)throw Error('Expected 9 components');
if(links.length!==124||links.some(l=>!screens.children.some(n=>n.id===l.target)))throw Error('Unresolved prototype links');
if(all.filter(n=>n.type==='TEXT').length<400)throw Error('Expected editable text nodes');
console.log(JSON.stringify({local_contract:'passed',screens:screens.children.length,componentVariants:9,prototypeLinks:links.length,textNodes:all.filter(n=>n.type==='TEXT').length,real_figma_editor_verified:false}));

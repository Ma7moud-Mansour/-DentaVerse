// Render the licensed GLB for design reference; no camera or live session data.
import http from 'node:http';
import fs from 'node:fs/promises';
import path from 'node:path';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const require=createRequire(path.join(root,'frontend/package.json'));
const {chromium}=require('@playwright/test');
const out=path.join(root,'design/figma/assets/molar-preview.png');
const html=`<!doctype html><html><style>body{margin:0;background:#182521}canvas{display:block}</style>
<script type="importmap">{"imports":{"three":"/three/build/three.module.js","three/addons/":"/three/examples/jsm/"}}</script>
<script type="module">
import * as T from 'three';import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
const scene=new T.Scene();scene.background=new T.Color('#182521');
const camera=new T.PerspectiveCamera(31,700/760,.1,100);camera.position.set(0,.1,6.6);camera.lookAt(0,0,0);
const renderer=new T.WebGLRenderer({antialias:true,preserveDrawingBuffer:true});renderer.setSize(700,760);renderer.setPixelRatio(1);renderer.outputColorSpace=T.SRGBColorSpace;
document.body.append(renderer.domElement);scene.add(new T.HemisphereLight(0xffffff,0x54634b,2.2));
const key=new T.DirectionalLight(0xfff9e8,3);key.position.set(-3,4,5);scene.add(key);const fill=new T.DirectionalLight(0xe8f1ec,1.2);fill.position.set(3,1,-2);scene.add(fill);
new GLTFLoader().load('/model.glb',g=>{const src=g.scene;src.updateMatrixWorld(true);const bounds=new T.Box3().setFromObject(src);const center=bounds.getCenter(new T.Vector3());const scale=3.3/bounds.getSize(new T.Vector3()).y;const group=new T.Group();
src.traverse(o=>{if(!o.isMesh)return;const geom=o.geometry.clone();geom.applyMatrix4(o.matrixWorld);geom.translate(-center.x,-center.y,-center.z);geom.scale(scale,scale,scale);const mat=o.material.clone();mat.roughness=.46;mat.metalness=0;const m=new T.Mesh(geom,mat);m.rotation.x=Math.PI;m.scale.x=-1;group.add(m)});
group.rotation.set(.12,-.55,0);scene.add(group);renderer.render(scene,camera);window.rendered=true;},undefined,e=>{window.renderError=String(e)});
</script></html>`;
const server=http.createServer(async(req,res)=>{try{let file;
 if(req.url==='/'){res.setHeader('Content-Type','text/html');res.end(html);return;}
 if(req.url==='/model.glb')file=path.join(root,'frontend/public/models/maxillary-first-molar-left.glb');
 else if(req.url.startsWith('/three/')&&!req.url.includes('..'))file=path.join(root,'frontend/node_modules',req.url.slice(1));
 else{res.statusCode=404;res.end();return;}
 res.setHeader('Content-Type',file.endsWith('.js')?'text/javascript':'model/gltf-binary');res.end(await fs.readFile(file));
}catch{res.statusCode=500;res.end('Render asset unavailable');}});
await new Promise(r=>server.listen(0,'127.0.0.1',r));let browser;
try{browser=await chromium.launch({channel:'msedge',args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});const page=await browser.newPage({viewport:{width:700,height:760}});
 await page.goto('http://127.0.0.1:'+server.address().port);await page.waitForFunction(()=>window.rendered||window.renderError,{timeout:30000});
 const err=await page.evaluate(()=>window.renderError);if(err)throw Error(err);await fs.mkdir(path.dirname(out),{recursive:true});await page.locator('canvas').screenshot({path:out});console.log('Saved design reference: '+out);
}finally{if(browser)await browser.close();await new Promise(r=>server.close(r));}

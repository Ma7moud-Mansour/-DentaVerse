// Runs inside a user-created Figma Design development plugin.
// DESIGN and MOLAR_PNG are bundled by tools/build_figma_kit.py.
(async () => {
  if (figma.editorType !== 'figma') throw new Error('Open a Figma Design file.');
  async function font(family, style, fallback) {
    try { const f={family,style}; await figma.loadFontAsync(f); return f; }
    catch { const f={family:'Inter',style:fallback}; await figma.loadFontAsync(f); return f; }
  }
  const regular=await font('DM Sans','Regular','Regular');
  const bold=await font('DM Sans','Bold','Bold');
  const heading=await font('Manrope','Medium','Bold');
  const rgb=hex=>({r:parseInt(hex.slice(1,3),16)/255,g:parseInt(hex.slice(3,5),16)/255,b:parseInt(hex.slice(5,7),16)/255});
  const paint=hex=>[{type:'SOLID',color:rgb(hex)}];
  const styles={};
  for (const [name,color] of Object.entries(DESIGN.colors)) {
    const s=figma.createPaintStyle();s.name='DentaVerse/'+name;s.paints=paint(color);styles[color]=s.id;
  }
  for (const [name,size,f] of [['Body / Regular',14,regular],['Body / Strong',14,bold],['Heading',28,heading],['Caption',11,regular]]) {
    const s=figma.createTextStyle();s.name='DentaVerse/'+name;s.fontName=f;s.fontSize=size;s.lineHeight={unit:'PIXELS',value:size*1.5};
  }
  const imageHash=figma.createImage(figma.base64Decode(MOLAR_PNG)).hash;
  function fill(node,color) {
    node.fills=paint(color);
    if(styles[color])node.fillStyleId=styles[color];
  }
  function text(parent,spec) {
    const n=figma.createText();parent.appendChild(n);
    n.name=spec.name||spec.text.split('\n')[0].slice(0,64);
    n.fontName=spec.size>=22?heading:spec.bold?bold:regular;
    n.fontSize=spec.size;n.lineHeight={unit:'PIXELS',value:spec.size*1.5};
    n.characters=spec.text;n.textAutoResize='HEIGHT';n.resize(spec.w,spec.h);
    n.x=spec.x;n.y=spec.y;n.textAlignHorizontal=spec.align||'LEFT';fill(n,spec.color);return n;
  }
  const library=figma.createPage();library.name='DentaVerse / Components & tokens';
  await figma.setCurrentPageAsync(library);
  const intro=figma.createFrame();intro.name='Design system / notes';intro.resize(1080,230);fill(intro,DESIGN.colors.paper);
  text(intro,{x:30,y:25,w:1020,h:60,text:'DentaVerse — Phase II design source',size:30,bold:true,color:DESIGN.colors.forest});
  text(intro,{x:30,y:90,w:1020,h:100,text:'Editable UI nodes, reusable component variants and prototype links.\nStatic 3D model imagery is a licensed educational reference, not a patient image.\nDesign examples are not participant records or evidence of physical BLE identification.',size:15,color:DESIGN.colors.muted});
  const componentMap={},families={};
  for(const [i,s] of DESIGN.components.entries()) {
    const c=figma.createComponent();c.name='Variant='+s.variant;c.resize(s.w,s.h);
    c.x=(i%4)*240;c.y=320+Math.floor(i/4)*100;fill(c,s.fill);c.cornerRadius=s.radius;
    if(s.stroke){c.strokes=paint(s.stroke);c.strokeWeight=1;}
    c.layoutMode='HORIZONTAL';c.primaryAxisAlignItems='CENTER';c.counterAxisAlignItems='CENTER';
    c.primaryAxisSizingMode='FIXED';c.counterAxisSizingMode='FIXED';c.paddingLeft=12;c.paddingRight=12;
    const label=text(c,{name:'Label',x:12,y:10,w:s.w-24,h:22,text:s.variant,size:s.size,color:s.color});
    label.textAlignHorizontal='CENTER';componentMap[s.id]=c;(families[s.family]??=[]).push(c);
  }
  let familyRow=0;
  for(const [name,nodes] of Object.entries(families)) {
    const set=figma.combineAsVariants(nodes,library);set.name='DentaVerse / '+name;
    set.x=0;set.y=310+familyRow*240;
    nodes.forEach((n,i)=>{n.x=24+i*224;n.y=40;});
    set.resize(nodes.length*224+24,126);familyRow++;
  }
  let swatchX=0;
  for(const [name,color] of Object.entries(DESIGN.colors)) {
    const s=figma.createFrame();s.name='Token / '+name;s.x=swatchX;s.y=1100;s.resize(132,132);fill(s,color);
    text(s,{x:10,y:92,w:112,h:25,text:name,size:12,color:color===DESIGN.colors.forest||color===DESIGN.colors.stage?DESIGN.colors.paper:DESIGN.colors.forest});swatchX+=150;
  }
  const page=figma.createPage();page.name='DentaVerse / Phase II screens';await figma.setCurrentPageAsync(page);
  const frames={},pending=[];let totalLayers=0;
  for(const [i,s] of DESIGN.screens.entries()) {
    const frame=figma.createFrame();frame.name=s.name;frame.resize(s.w,s.h);
    frame.x=(i%4)*1520;frame.y=Math.floor(i/4)*1060;frame.clipsContent=true;fill(frame,s.fill);frames[s.id]=frame;
    frame.setPluginData('dentaverse_screen',s.id);
    for(const l of s.children) {
      let n;
      if(l.type==='text')n=text(frame,l);
      else if(l.type==='instance') {
        n=componentMap[l.component].createInstance();frame.appendChild(n);n.resize(l.w,l.h);n.x=l.x;n.y=l.y;n.name=l.label;
        const label=n.findOne(v=>v.type==='TEXT'&&v.name==='Label');
        if(label){label.characters=l.label;label.textAutoResize='HEIGHT';label.resize(Math.max(10,l.w-24),label.height);}
      } else if(l.type==='svg') {
        n=figma.createNodeFromSvg(l.svg);frame.appendChild(n);n.resize(l.w,l.h);n.x=l.x;n.y=l.y;n.name=l.name;
      } else {
        n=figma.createRectangle();frame.appendChild(n);n.resize(l.w,l.h);n.x=l.x;n.y=l.y;n.name=l.name||l.type;
        if(l.type==='image')n.fills=[{type:'IMAGE',imageHash,scaleMode:'FIT'}];
        else {fill(n,l.fill);n.cornerRadius=l.radius||0;if(l.stroke){n.strokes=paint(l.stroke);n.strokeWeight=1;}}
        if(l.opacity!==undefined)n.opacity=l.opacity;
      }
      if(l.to)pending.push([n,l.to]);totalLayers++;
    }
  }
  let linked=0;const warnings=[];
  for(const [node,target] of pending) {
    try {
      await node.setReactionsAsync([{trigger:{type:'ON_CLICK'},actions:[{type:'NODE',destinationId:frames[target].id,navigation:'NAVIGATE',transition:null}]}]);linked++;
    }catch(e){warnings.push(node.name+': '+String(e));}
  }
  figma.currentPage.selection=[frames.studio];figma.viewport.scrollAndZoomIntoView([frames.studio]);
  console.log(JSON.stringify({screens:DESIGN.screens.length,layers:totalLayers,componentVariants:DESIGN.components.length,prototypeLinks:linked,warnings}));
  figma.closePlugin('Created '+DESIGN.screens.length+' editable screens, '+DESIGN.components.length+' component variants and '+linked+' prototype links.'+(warnings.length?' Check console for '+warnings.length+' link warnings.':''));
})().catch(error=>{console.error(error);figma.closePlugin('DentaVerse import stopped: '+String(error));});

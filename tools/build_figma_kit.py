"""Build editable design primitives and a native Figma Plugin API importer.

This does not claim a cloud Figma file was created or tested in Figma.
"""
import base64
import html
import json
import textwrap
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "deliverables/DentaVerse_Figma_Kit"
C = dict(enamel="#F3F2EC", paper="#FCFCF8", forest="#1D302C", stage="#182521",
         focus="#DBEEAB", line="#DEDFD5", muted="#737E73", caution="#E9C08F", blue="#8AC9EA")
SCREENS = []


def rect(x,y,w,h,fill="paper",radius=0,stroke=None,**extra):
    return dict(type="rect",x=x,y=y,w=w,h=h,fill=C.get(fill,fill),radius=radius,
                stroke=C.get(stroke,stroke),**extra)


def txt(x,y,w,value,size=14,color="forest",bold=False,**extra):
    return dict(type="text",x=x,y=y,w=w,h=extra.pop("h",max(22, size*1.5*(value.count('\n')+1))),
                text=value,size=size,color=C.get(color,color),bold=bold,**extra)


def button(x,y,label,to=None,kind="Primary",w=184):
    return dict(type="instance",component=f"Button/{kind}",x=x,y=y,w=w,h=42,label=label,to=to)


def pill(x,y,label,kind="Ready",w=144):
    return dict(type="instance",component=f"Status/{kind}",x=x,y=y,w=w,h=30,label=label)


def image(x,y,w,h):
    return dict(type="image",name="Licensed molar / static 3D reference",x=x,y=y,w=w,h=h)


def mirror(x,y):
    return dict(type="svg",name="Dental mirror / editable vector illustration",x=x,y=y,w=122,h=270,
        svg='<svg xmlns="http://www.w3.org/2000/svg" width="122" height="270" viewBox="0 0 122 270"><line x1="18" y1="253" x2="84" y2="79" stroke="#B7BFA8" stroke-width="11" stroke-linecap="round"/><ellipse cx="87" cy="46" rx="28" ry="41" transform="rotate(20 87 46)" fill="#D8DDCC" stroke="#AAB4A0" stroke-width="5"/><ellipse cx="87" cy="46" rx="22" ry="34" transform="rotate(20 87 46)" fill="#BFCAB7" stroke="#F3F2EC" stroke-width="1"/></svg>')


def card(x,y,w,h,title,body=""):
    return [rect(x,y,w,h,radius=10,stroke="line"),txt(x+22,y+20,w-44,title,19,bold=True),
            txt(x+22,y+62,w-44,body,14,"muted")]


def sidebar(active="Studio"):
    a=[rect(0,0,220,960),txt(27,31,175,"∩  DentaVerse",25,bold=True),txt(27,76,170,"ANATOMY WORKSPACE",10,"muted")]
    for i,(label,target) in enumerate([("Studio","studio"),("Anatomy atlas","atlas"),("Session setup","setup"),("Session journal","journal_empty"),("Gesture guide","guide"),("Preferences","preferences")]):
        a.append(dict(type="instance",component="Navigation/Active" if label==active else "Navigation/Default",x=16,y=141+i*58,w=188,h=44,label=label,to=target))
    a += [rect(22,822,176,1,"line"),txt(27,846,170,"DV  Beginning learner",13,bold=True),txt(27,873,170,"Manual profile preview",11,"muted")]
    return a


def shell(title,active="Studio",subtitle="DentaVerse / anatomy learning"):
    return sidebar(active)+[txt(264,33,900,title,27,bold=True),txt(264,74,900,subtitle,12,"muted"),rect(220,116,1220,1,"line"),rect(220,928,1220,32,"forest"),txt(246,934,1100,"Local session   ·   Explicit pause and recovery   ·   Mouse / keyboard alternative",11,"focus")]


def screen(key,title,layers,w=1440,h=960):
    SCREENS.append(dict(id=key,name=title,w=w,h=h,fill=C["enamel"],children=layers))


def workbench(hand=False):
    a=[rect(0,0,1440,72),txt(26,23,190,"∩  DentaVerse",23,bold=True),button(221,15,"← Studio","studio","Secondary",124),
       txt(371,25,460,"ANATOMY / PERMANENT DENTITION",11,"muted"),pill(1038,21,"Guided session"),button(1205,15,"Pause session","pause","Secondary",207),
       rect(0,72,58,856,"forest"),rect(58,72,982,856,"stage"),rect(1040,72,400,856,"enamel")]
    for i,label in enumerate(["Layers","Frame","Zoom","Reset"]):
        a += [rect(8,108+i*72,42,44,"#294035",7),txt(12,122+i*72,34,label[:1],16,"focus",True,align="CENTER")]
    a += [txt(92,111,650,"SPECIMEN / 16",11,"muted"),txt(92,143,690,"Upper right first molar",25,"paper",True),
          button(92,195,"Reset view","reset","Secondary",138),image(315,244,440,478),mirror(702,433),
          txt(786,384,150,"Crown",12,"paper"),rect(728,395,47,1,"muted"),txt(786,650,150,"Roots",12,"paper"),rect(728,662,47,1,"muted"),
          txt(92,818,740,"University of Dundee · CC BY 4.0 / mirrored educational model; anatomy review pending",10,"muted"),
          button(425,861,"Return to dentition","atlas","Primary",246),rect(0,928,1440,32,"forest"),txt(24,935,1350,"Hand controls · ready" if hand else "Manual input · Mouse & keyboard   |   Local session",11,"focus")]
    if hand:
        a += [rect(1062,98,356,520,"#EDF0DA",8,stroke="#8A9E69"),txt(1082,120,312,"Move it with your hands",18,bold=True),
              button(1082,159,"Use mouse & keyboard","workbench","Primary",312),txt(1082,221,312,"Open palms · left controls tooth,\nright controls instrument",13,"muted"),
              txt(1082,281,312,"LEFT · TOOTH\nReady · grip to rotate",13),txt(1082,345,312,"RIGHT · INSTRUMENT\nReady · grip / pinch to move",13),
              txt(1082,411,312,"Both pinches: spread hands to zoom in.\nBring them together to zoom out.",12,"muted"),
              txt(1082,470,312,"✓ Right-hand wave switches instruments",12),txt(1082,506,312,"DollarPy · Ready: wave side to side twice.",12,"muted"),
              txt(1082,547,312,"Movement sensitivity · 55%",12),rect(1082,580,306,6,"#9BAC76",3),rect(1204,574,18,18,"#819B55",9),
              rect(1062,640,356,222,"stage",8),txt(1082,663,310,"Hands     Body     Both",13,"focus"),txt(1092,717,290,"CAMERA PREVIEW AREA",16,"paper",True,align="CENTER"),
              txt(1082,808,312,"No personal camera imagery in this design.",11,"muted")]
    else:
        a += [txt(1062,109,330,"SPECIMEN",11,"muted"),txt(1062,144,90,"16",60),txt(1167,167,240,"Upper right\nFirst molar",16),
              rect(1062,253,356,1,"line"),txt(1062,278,330,"CURRENT TASK",11,"muted"),txt(1062,313,330,"Start with the first molar",22),
              txt(1062,354,330,"Inspect the specimen, explore its layers,\nthen position the mirror.",14,"muted"),
              txt(1062,423,330,"✓ Locate tooth 16\n✓ Inspect the specimen\n3  Position the mirror",14),rect(1062,519,356,1,"line"),txt(1062,545,330,"TISSUE EXPLORER",11,"muted")]
        for i,label in enumerate(["Surface","Enamel","Dentin","Pulp"]):
            a.append(button(1062+(i%2)*180,578+(i//2)*52,label,None,"Selected" if i==0 else "Secondary",170))
        a += [txt(1062,697,330,"External form. Rotate to compare the\ncrown and roots. Internal tissues are\nillustrations, not segmented anatomy.",13,"muted"),
              txt(1062,780,330,"Active tool · Dental mirror",14),button(1062,824,"Enable hand controls","workbench_hand","Primary",356)]
    return a


def modal(key,title,body,buttons):
    a=workbench(True)+[rect(0,0,1440,960,"#07110D",opacity=.56),rect(430,260,580,400,"paper",14,stroke="line"),
        txt(468,304,504,title,29,bold=True),txt(468,369,504,body,16,"muted")]
    for i,(label,to,kind) in enumerate(buttons):a.append(button(468+i*252,559,label,to,kind,240))
    screen(key,title,a)


def build_screens():
    a=shell("Your anatomy studio")+[pill(264,145,"Guided learning"),txt(264,218,570,"Knowledge,\nin your hands.",51,bold=True),
        txt(266,385,570,"Explore dental anatomy with a 3D specimen,\nclear guidance and purposeful hand controls.",19,"muted"),
        button(264,483,"Open anatomy atlas →","atlas",w=244),button(530,483,"Set up session","setup","Secondary",215),
        rect(866,154,520,590,"stage",14),image(936,208,380,410),txt(902,659,448,"FDI 16 · Upper right first molar",19,"paper",True),
        txt(902,704,448,"University of Dundee · CC BY 4.0",11,"muted")]
    a += card(264,650,263,192,"Inspect","Compare the crown\nand roots from a\nuseful viewpoint.")+card(547,650,263,192,"Explore layers","Surface, enamel,\ndentin and schematic\npulp explanations.")
    screen("studio","01 / Studio",a)
    a=shell("Anatomy atlas","Anatomy atlas")+[txt(264,152,1000,"Find your specimen",34,bold=True),txt(264,203,1000,"Permanent dentition · select FDI 16 to begin the guided activity.",15,"muted"),
        rect(264,251,1090,49,"paper",7,stroke="line"),txt(284,265,1040,"Search by tooth name or FDI number",14,"muted"),txt(303,346,970,"UPPER ARCH / PERMANENT TEETH",12,"muted",align="CENTER")]
    nums=list(range(18,10,-1))+list(range(21,29))
    for i,n in enumerate(nums):
        x=292+i*65;y=406+abs(7.5-i)*8
        a += [rect(x,y,53,86,"focus" if n==16 else "paper",18,stroke="line"),txt(x,y+29,53,str(n),16,bold=n==16,align="CENTER")]
    a += card(264,623,1090,210,"Upper right first molar","FDI 16 · Permanent / Maxillary\nSelect and isolate the tooth to inspect its external form and illustrative layers.")
    a.append(button(1060,765,"Inspect specimen →","workbench",w=268));screen("atlas","02 / Anatomy atlas",a)
    screen("workbench","03 / Workbench — manual",workbench())
    screen("workbench_hand","04 / Workbench — live hands",workbench(True))
    a=shell("Session setup","Session setup")+[txt(264,153,1040,"Set up a comfortable learning space",34,bold=True),txt(264,209,1040,"Connect only the services needed for this session.",16,"muted")]
    a += card(264,275,520,450,"Camera & tracking","Start the camera, keep the whole hand visible,\nand choose Hands, Body or Both overlays.")
    a += [rect(287,389,474,218,"stage",8),txt(319,480,410,"Live preview / no image stored in design",15,"paper",align="CENTER"),button(287,648,"Start camera","camera_unavailable",w=210),button(514,648,"Enter with hands","workbench_hand","Secondary",247)]
    a += card(808,275,546,450,"Bluetooth identity","Discover a peripheral advertising the DentaVerse\nGATT service and read its registered UserID.")
    a += [pill(831,412,"Offline","Offline"),button(831,474,"Discover devices","bluetooth",w=497),txt(831,548,493,"A phone must advertise the project service.\nIts ordinary Bluetooth name is not a UserID.",14,"muted"),button(264,782,"Use manual controls","workbench","Secondary",264)]
    screen("setup","05 / Session setup",a)
    a=shell("Bluetooth identity","Session setup")+card(264,163,1090,570,"Discover your DentaVerse peripheral","Read the application UserID from a connectable BLE GATT service.")
    a += [pill(288,276,"Bluetooth on"),button(1050,271,"Discover devices","bluetooth","Primary",280),txt(288,349,995,"No DentaVerse service found",26,bold=True),
        txt(288,405,995,"The phone must run a GATT server and advertise the custom service UUID.\nScanning the phone's ordinary Bluetooth name does not read a learning profile.",16,"muted"),
        txt(288,492,995,"SERVICE UUID\n7d8f0001-9c7a-4b82-8f10-2da6d7e04a31",14),txt(288,565,995,"READ CHARACTERISTIC\n7d8f0002-9c7a-4b82-8f10-2da6d7e04a31",14),
        txt(288,642,995,"Expected UTF-8 value: DV-STUDENT-01 (registered application identity)",14),button(264,780,"Back to setup","setup","Secondary",224)]
    screen("bluetooth","06 / Bluetooth — no compatible device",a)
    a=shell("Preferences","Preferences")+card(264,160,1090,700,"Input and learning profile","Settings reflect the current local session. Sensor calibration is separate from user identity.")
    a += [txt(289,285,1000,"INPUT MODE",12,"muted"),button(289,325,"Mouse & keyboard","workbench","Selected",290),button(599,325,"Live hand controls","workbench_hand","Secondary",290),
          txt(289,414,1000,"MANUAL PROFILE PREVIEW",12,"muted"),rect(289,454,1015,48,"enamel",5,stroke="line"),txt(310,468,960,"Beginning learner    /    Experienced learner    /    Teaching demonstrator",14),
          txt(289,539,1000,"This previews registered roles; it is not a new account or an authenticated login.",13,"muted"),
          button(289,594,"Preview experienced learner","identity_switch","Secondary",370),txt(289,676,1000,"Movement sensitivity · 55%\n✓ Right-hand wave switches instruments (DollarPy)",15),
          txt(289,761,1000,"Recorded V / circle / Z templates require actual camera captures.\nNo real gesture templates or participant records are included in this design.",13,"muted")]
    screen("preferences","07 / Preferences",a)
    a=shell("Gesture guide","Gesture guide")+[txt(264,153,1070,"Know what each movement does",34,bold=True)]
    for i,(title,body) in enumerate([("Open / grip","Open to rearm; left fist rotates the tooth.\nRight grip or pinch moves the instrument."),("Both pinches","Spread hands to zoom in.\nBring hands together to zoom out."),("Right-palm wave / DollarPy","Wave side to side twice to cycle instruments.\nHold the open palm still briefly before repeating."),("Recorded V / circle / Z","V: confirm selection. Circle: enamel. Z: pause.\nRequires recorded templates and calibration.")]):
        a += card(264+(i%2)*558,231+(i//2)*274,532,248,title,body)
    a.append(button(264,822,"Return to specimen","workbench_hand",w=266));screen("guide","08 / Gesture guide",a)
    a=shell("Review your session")+[txt(264,154,1050,"Reflect before you move on",35,bold=True),txt(264,212,1050,"Completed interaction checkpoints describe actions, not clinical competence.",15,"muted")]
    a += card(264,279,1090,201,"Session checkpoints","✓ Locate tooth 16     ✓ Inspect the specimen     ✓ Position the mirror")
    a += [txt(264,523,1050,"Reflect before you move on",18,bold=True),rect(264,566,1090,190,"paper",8,stroke="line"),txt(284,587,1030,"Write one spatial observation in your own words…",16,"muted"),
          button(264,800,"Save reflection","journal_saved",w=238),button(525,800,"Keep inspecting","workbench","Secondary",238)]
    screen("review","09 / Session review",a)
    a=shell("Session journal","Session journal")+card(264,224,1090,430,"Your saved observations appear here","There are no saved reflections for this learning profile yet.")
    a += [button(648,532,"Start an activity","atlas",w=270),txt(288,701,1020,"Journal entries belong to the active application UserID.",14,"muted")];screen("journal_empty","10 / Journal — empty",a)
    a=shell("Session journal","Session journal")+card(264,198,1090,330,"Example session · FDI 16","Example entry for layout demonstration.\nA real saved reflection appears here after the learner writes and saves one.")
    a += [pill(289,409,"Saved entry"),button(1050,436,"Open specimen","workbench","Secondary",275),txt(264,599,1090,"Illustrative design content only — not participant data or research findings.",14,"muted")];screen("journal_saved","11 / Journal — saved state",a)
    modal("pause","Take a moment.","Your scene and observations are retained.\nResume when you are ready, or return to manual controls.",[("Use manual controls","workbench","Secondary"),("Resume session","workbench_hand","Primary")])
    modal("tracking_lost","Let’s get your hand back.","Restore live camera frames, then resume explicitly.\nOpen your palm before grabbing an object again.",[("Use manual controls","workbench","Secondary"),("Resume session","workbench_hand","Primary")])
    modal("reset","Reset the specimen view?","Reset rotation, zoom and instrument placement.\nYour written reflection remains available.",[("Keep working","workbench","Secondary"),("Reset specimen","workbench","Primary")])
    modal("identity_switch","Switch learning profiles?","Save or discard the current activity before switching.\nThe next profile has its own learning guidance and journal.",[("Keep current profile","preferences","Secondary"),("Save & switch","studio_advanced","Primary")])
    a=shell("Session setup","Session setup")+card(264,211,1090,407,"Camera unavailable","The camera could not be opened. Check its access, index and whether another app is using it.\nYou can continue with the mouse and keyboard.")
    a += [pill(289,366,"Camera unavailable","Warning",240),button(289,464,"Try camera again","setup","Secondary",280),button(592,464,"Use manual controls","workbench",w=280)];screen("camera_unavailable","16 / Camera unavailable",a)
    a=shell("Your anatomy studio",subtitle="Experienced learning profile")+[pill(264,155,"Experienced learner"),txt(264,239,1090,"Explore structure and relationships",39,bold=True),
        txt(264,321,1080,"Inspect FDI 16 independently. Compare crown form and root arrangement,\nthen document one spatial observation from your chosen viewpoint.",19,"muted"),
        button(264,444,"Open anatomy atlas →","atlas",w=285)]+card(264,562,1090,227,"Different content, same specimen","Beginner: explicit tooth identity and step-by-step prompts.\nExperienced: self-directed inspection and spatial comparisons.\nDemonstrator: group discussion and explanation prompts.")
    screen("studio_advanced","17 / Experienced learner context",a)


def components():
    result=[]
    for variant,fill,stroke,color in [("Primary","focus",None,"forest"),("Secondary","paper","line","forest"),("Selected","#E7EFCB","#9EB967","forest"),("Disabled","line",None,"muted")]:
        result.append(dict(id="Button/"+variant,family="Button",variant=variant,w=184,h=42,fill=C.get(fill,fill),stroke=C.get(stroke,stroke),radius=6,color=C[color],size=13))
    for variant,fill,color in [("Default","paper","forest"),("Active","focus","forest")]:
        result.append(dict(id="Navigation/"+variant,family="Navigation",variant=variant,w=188,h=44,fill=C[fill],color=C[color],radius=6,size=14))
    for variant,fill,color in [("Ready","focus","forest"),("Offline","line","muted"),("Warning","caution","forest")]:
        result.append(dict(id="Status/"+variant,family="Status",variant=variant,w=144,h=30,fill=C[fill],color=C[color],radius=15,size=11))
    return result


def svg_layers(layers,defs,component_map):
    out=[]
    for n in layers:
        x,y,w,h=n['x'],n['y'],n['w'],n['h'];t=n['type'];a=[]
        if t=='rect':a=[f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{n.get("radius",0)}" fill="{n["fill"]}" opacity="{n.get("opacity",1)}"'+(f' stroke="{n["stroke"]}"' if n.get('stroke') else '')+'/>' ]
        elif t=='image':a=[f'<use href="#molar" x="{x}" y="{y}" width="{w}" height="{h}"/>' ]
        elif t=='svg':a=[f'<svg x="{x}" y="{y}" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'+n['svg'].split('>',1)[1]]
        elif t=='text':
            size=n['size'];a=[f'<text x="{x+w/2 if n.get("align")=="CENTER" else x}" y="{y+size}" fill="{n["color"]}" font-family="Arial,sans-serif" font-size="{size}" font-weight="{600 if n["bold"] else 400}" text-anchor="{ "middle" if n.get("align")=="CENTER" else "start"}">']
            for i,line in enumerate(n['text'].split('\n')):a.append(f'<tspan x="{x+w/2 if n.get("align")=="CENTER" else x}" dy="{0 if i==0 else size*1.5}">{html.escape(line)}</tspan>')
            a.append('</text>')
        elif t=='instance':
            c=component_map[n['component']];a=[f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{c["radius"]}" fill="{c["fill"]}"'+(f' stroke="{c["stroke"]}"' if c.get('stroke') else '')+'/>',f'<text x="{x+w/2}" y="{y+h/2+c["size"]*.35}" text-anchor="middle" font-family="Arial,sans-serif" font-size="{c["size"]}" fill="{c["color"]}">{html.escape(n["label"])}</text>']
        if n.get('to'):a=[f'<a href="#{n["to"]}">',*a,'</a>']
        out.extend(a)
    return '\n'.join(out)


def main():
    build_screens();OUT.mkdir(parents=True,exist_ok=True)
    model=(ROOT/'design/figma/assets/molar-preview.png').read_bytes()
    spec=dict(title="DentaVerse — Phase II",colors=C,components=components(),screens=SCREENS,provenance="Native editable UI primitives. Molar image is a static GLB render; no camera or participant data.")
    ids={s['id'] for s in SCREENS};assert len(ids)==len(SCREENS)
    for s in SCREENS:
        for n in s['children']:
            assert n['w']>0 and n['h']>0
            if n.get('to'):assert n['to'] in ids
    (OUT/'design-spec.json').write_text(json.dumps(spec,ensure_ascii=False,indent=2),encoding='utf-8')
    b64=base64.b64encode(model).decode();(OUT/'molar-preview.png').write_bytes(model)
    code=(ROOT/'design/figma/importer.js').read_text(encoding='utf-8')
    (OUT/'code.js').write_text('const DESIGN = '+json.dumps(spec,ensure_ascii=False)+';\nconst MOLAR_PNG = "'+b64+'";\n'+code,encoding='utf-8')
    (OUT/'manifest.example.json').write_text(json.dumps(dict(name="DentaVerse Phase II",id="COPY_YOUR_FIGMA_GENERATED_PLUGIN_ID",api="1.0.0",main="code.js",editorType=["figma"],documentAccess="dynamic-page",networkAccess={"allowedDomains":["none"]}),indent=2),encoding='utf-8')
    cols=4;rows=(len(SCREENS)+cols-1)//cols;groups=[];views={}
    cm={c['id']:c for c in spec['components']}
    for i,s in enumerate(SCREENS):
        x=36+(i%cols)*1490;y=65+(i//cols)*1040;views[s['id']]=[x,y,1440,960]
        groups.append(f'<g id="{s["id"]}" transform="translate({x},{y})"><rect width="1440" height="960" fill="{s["fill"]}"/>'+svg_layers(s['children'],[],cm)+'</g>')
        groups.append(f'<text x="{x}" y="{y-15}" fill="#253A30" font-family="Arial" font-size="22">{html.escape(s["name"])}</text>')
    svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="{cols*1490+36}" height="{rows*1040+40}" viewBox="0 0 {cols*1490+36} {rows*1040+40}"><defs><symbol id="molar" viewBox="0 0 700 760"><image width="700" height="760" href="data:image/png;base64,{b64}"/></symbol></defs><rect width="100%" height="100%" fill="#E6E7DE"/>'+''.join(groups)+'</svg>'
    (OUT/'DentaVerse-Editable-Screens.svg').write_text(svg,encoding='utf-8')
    options=''.join(f'<option value="{s["id"]}">{html.escape(s["name"])}</option>' for s in SCREENS)
    preview='<!doctype html><meta charset="utf-8"><title>DentaVerse Design Preview</title><style>body{margin:0;background:#e6e7de;font:14px Arial}header{padding:14px;background:#fcfcf8;position:sticky;top:0}select{padding:8px;min-width:330px}svg{display:block;width:100%;height:calc(100vh - 70px)}a{cursor:pointer}</style><header><b>DentaVerse / editable design source</b> &nbsp; <select id="screen">'+options+'</select> &nbsp; <button id="all">All screens</button></header>'+svg+'<script>const views='+json.dumps(views)+';const svg=document.querySelector("svg"),select=document.querySelector("select");function show(id){if(views[id]){svg.setAttribute("viewBox",views[id].join(" "));select.value=id;}}select.onchange=()=>{location.hash=select.value};document.querySelector("#all").onclick=()=>svg.setAttribute("viewBox","0 0 '+str(cols*1490+36)+' '+str(rows*1040+40)+'");window.onhashchange=()=>show(location.hash.slice(1));show(location.hash.slice(1)||"studio");</script>'
    (OUT/'preview.html').write_text(preview,encoding='utf-8')
    (OUT/'README_AR.md').write_text((ROOT/'design/figma/README_AR.md').read_text(encoding='utf-8'),encoding='utf-8')
    (OUT/'MODEL_ATTRIBUTION.md').write_text((ROOT/'frontend/public/models/ATTRIBUTION.md').read_text(encoding='utf-8'),encoding='utf-8')
    zip_path=OUT.parent/'DentaVerse_Figma_Kit.zip'
    with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(OUT.iterdir()):z.write(p,'DentaVerse_Figma_Kit/'+p.name)
    print(json.dumps({'screens':len(SCREENS),'components':len(spec['components']),'links':sum(bool(n.get('to')) for s in SCREENS for n in s['children']),'zip':str(zip_path),'svg':str(OUT/'DentaVerse-Editable-Screens.svg')}))


if __name__=='__main__':main()

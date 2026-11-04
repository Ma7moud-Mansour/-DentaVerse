const fields = [
  {q:1,label:"دورك إيه؟",key:"role",options:[["student","طالب أسنان"],["demonstrator","معيد / مدرس"],["other","غير كده"]]},
  {q:1,label:"السنة الدراسية — اختياري",key:"study_year",options:[1,2,3,4,5,6,7,8].map(n=>[String(n),String(n)])},
  {q:2,label:"بتستخدم أدوات رقمية أو موديلات ثلاثية الأبعاد لتعلّم التشريح قد إيه؟",key:"digital_tools_frequency",options:[["never","أبدًا"],["rarely","نادرًا"],["sometimes","أحيانًا"],["often","كتير"],["very_often","كتير جدًا"]]},
  {q:3,label:"ثقتك في تحديد الأسنان بترقيم FDI؟ (١ قليلة — ٥ كبيرة)",key:"fdi_confidence",rating:true},
  {q:4,label:"استخدمت تتبع الإيد أو التحكم بالحركات قبل كده؟",key:"gesture_experience",options:[["yes","أيوه"],["no","لأ"],["unsure","مش متأكد"]]},
  {q:5,label:"أنهي أنشطة تعليمية هتفيدك؟ اختار أي عدد",key:"useful_activities",multi:true,options:[["identify","تحديد السن"],["rotate","لف وفحص الموديل"],["layers","استكشاف الطبقات"],["instrument","أداة افتراضية"],["progress","مراجعة التقدم"],["notes","حفظ ملاحظات"]]},
  {q:6,label:"هتستخدمه على جهاز إيه غالبًا؟",key:"device",options:[["laptop","لابتوب"],["desktop","كمبيوتر مكتبي"],["tablet","تابلت"],["other","غير كده"]]},
  {q:6,label:"وفي أنهي أماكن؟ اختار أي عدد",key:"setting",multi:true,options:[["alone","مذاكرة فردية"],["classroom","قاعة تدريس"],["laboratory","معمل"],["other","غير كده"]]},
  {q:7,label:"إيه اللي ممكن يصعّب استخدامه؟ اختار أي عدد",key:"barriers",multi:true,options:[["instructions","تعليمات مش واضحة"],["camera","إعداد الكاميرا"],["accidental_gestures","حركات غير مقصودة"],["small_controls","أزرار صغيرة"],["visual_complexity","شكل معقّد"],["discomfort","إجهاد أو عدم راحة"],["privacy","الخصوصية"],["other","غير كده"]]},
  {q:8,label:"وجود بديل بالماوس ولوحة المفاتيح مهم قد إيه؟ (١ مش مهم — ٥ مهم جدًا)",key:"manual_controls_importance",rating:true},
  {q:9,label:"لو الحركة ما اشتغلتش، إيه اللي يساعدك؟",key:"recovery_preferences",multi:true,options:[["explanation","تفسير اللي حصل"],["fix_steps","خطوات الإصلاح"],["undo_reset","تراجع أو إعادة ضبط"],["pause_resume","إيقاف واستكمال"],["help","مساعدة"]]},
  {q:10,label:"إيه اللي لازم يفضل ظاهر أثناء الفحص؟",key:"persistent_information",multi:true,options:[["number","رقم السن"],["name","اسم السن"],["tool","الأداة المختارة"],["mode","وضع التحكم"],["instructions","التعليمات"],["progress","التقدم"]]},
  {q:11,label:"مرتاح لاستخدام كاميرا في مكان مذاكرتك قد إيه؟ (١ مش مرتاح — ٥ مرتاح جدًا)",key:"camera_comfort",rating:true},
  {q:12,label:"إيه تعديل واحد يخلي الأداة أسهل أو أفيد؟ من غير بيانات شخصية",key:"open_comment",text:true},
];
const form=document.querySelector("#survey"),host=document.querySelector("#questions"),result=document.querySelector("#result");
let code=crypto.randomUUID().slice(0,8);
for(const field of fields){
  const group=document.createElement("fieldset"),legend=document.createElement("legend");legend.textContent=`${field.q}. ${field.label}`;group.append(legend);
  if(field.text){const input=document.createElement("textarea");input.name=field.key;input.maxLength=1000;input.setAttribute("aria-label",field.label);group.append(input);}
  else if(field.multi){for(const [value,text] of field.options){const label=document.createElement("label"),input=document.createElement("input");input.type="checkbox";input.name=field.key;input.value=value;label.append(input,document.createTextNode(text));group.append(label);}}
  else {const select=document.createElement("select");select.name=field.key;select.setAttribute("aria-label",field.label);select.add(new Option("أفضل عدم الإجابة / لم أختر",""));for(const [value,text] of field.rating?[1,2,3,4,5].map(n=>[String(n),String(n)]):field.options)select.add(new Option(text,value));group.append(select);}
  host.append(group);
}
function cell(value){let text=String(value);if(/^[=+@-]/.test(text))text="'"+text;return '"'+text.replaceAll('"','""')+'"';}
form.addEventListener("submit",event=>{
  event.preventDefault();if(!form.reportValidity())return;
  const data=new FormData(form),headers=["anonymous_code","consented",...fields.map(f=>f.key)];
  const row=[code,"yes",...fields.map(f=>f.multi?data.getAll(f.key).join(";"):(data.get(f.key)||""))];
  const csv="\ufeff"+[headers,row].map(r=>r.map(cell).join(",")).join("\r\n")+"\r\n";
  const url=URL.createObjectURL(new Blob([csv],{type:"text/csv;charset=utf-8"})),link=document.createElement("a");link.href=url;link.download=`dentaverse-response-${code}.csv`;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  result.textContent=`اتجهّز ملف الإجابة برمز ${code}. نزّل الملف لنفسك، وتسليمه للباحث اختياري. كرّر التنزيل بنفس الرمز لو محتاج؛ التحليل بيرفض حسابه مرتين.`;
});
form.addEventListener("reset",()=>{code=crypto.randomUUID().slice(0,8);result.textContent="بدأت إجابة جديدة من غير حفظ الإجابة السابقة.";});

# تجربة UserID بموبايل أندرويد

هذه إعدادات مقترحة لجهاز حقيقي؛ وجودها لا يثبت نجاح تجربة BLE. يحتاج الهاتف دعم BLE advertising. يدعم nRF Connect على أندرويد تكوين GATT server والإعلان، حسب [صفحة Nordic الرسمية](https://www.nordicsemi.com/Products/Development-tools/nRF-Connect-for-mobile) و[دليل التطبيق](https://github.com/nordicsemi/Android-nRF-Connect/blob/main/documentation/README.md).

## إعداد الهاتف

1. ثبّت [nRF Connect for Mobile من Nordic Semiconductor](https://play.google.com/store/apps/details?id=no.nordicsemi.android.mcp)، وشغّل Bluetooth واسمح بصلاحياته المطلوبة.
2. من القائمة افتح **Configure GATT server**، وأنشئ إعدادًا باسم DentaVerse.
3. أضف **Custom / Primary service** بالـUUID التالي:

   `7d8f0001-9c7a-4b82-8f10-2da6d7e04a31`

4. أضف Characteristic بالـUUID التالي، وخاصية **Read** وصلاحية القراءة:

   `7d8f0002-9c7a-4b82-8f10-2da6d7e04a31`

5. اجعل قيمتها النصية UTF-8 هي `DV-STUDENT-01`. لو الحقل يقبل Hex فقط، القيمة:

   `44 56 2D 53 54 55 44 45 4E 54 2D 30 31`

6. من **Advertiser** أنشئ إعلانًا **Connectable**، وأضف **Service UUID** الخاص بالخدمة أعلاه. شغّل الإعلان واترك التطبيق مفتوحًا. اسم Bluetooth العادي وحده لا يكفي للاكتشاف.

## تجربة التطبيق وتبديل المحتوى

1. في DentaVerse افتح Session setup أو Preferences. شغّل خدمة Bluetooth ثم **Discover devices** واختر الهاتف ثم **Connect & read ID**.
2. لو فيه نشاط غير محفوظ، احفظه أو اختر تجاهله من الحوار قبل تبديل الهوية. تحقق من أن مصدر الهوية Bluetooth وأن المحتوى للمبتدئ.
3. احفظ ملاحظة للمستخدم الأول، ثم افصل الاتصال من DentaVerse.
4. غيّر القيمة في الهاتف إلى `DV-STUDENT-02` وأعد القراءة. Hex للقيمة الثانية ينتهي بـ`32` بدل `31`.
5. تحقق من محتوى المتمرس ومن فصل سجله. ارجع للهوية الأولى وتحقق من ملاحظتها.

لو الهاتف لا يظهر، تحقق من إعلان UUID الصحيح وتفعيل الاتصال وخدمة GATT معًا. لو ظهر وفشلت القراءة، راجع Characteristic وRead والقيمة النصية. لا تستخدم اسم الهاتف أو MAC كهوية طالب. قد تختلف أماكن الأزرار حسب إصدار التطبيق؛ لم نختبر هذه الخطوات على هاتف المستخدم بعد.

سجّل موديل الهاتف ونسخة أندرويد والـcommit والهوية المقروءة والنتيجة الفعلية في سجل الأدلة. لا تضع عناوين أجهزة أو سجلات شخصية في Git. تبقى S8-05 وS9-06 مفتوحتين حتى نجاح التجربة الفعلية.

# 🎟️ بوت تذاكر ديسكورد متقدم

بوت ديسكورد مبني بلغة Python باستخدام مكتبة `discord.py` لإدارة نظام تذاكر دعم فني متكامل داخل سيرفرك. يتيح للمستخدمين فتح تذاكر في أقسام محددة، ويتيح للمشرفين الرد عليها وإدارتها بسهولة، مع ميزات أرشفة وتواصل عبر الرسائل الخاصة.

## ✨ الميزات الرئيسية

*   **فتح تذاكر سهل:** يمكن للمستخدمين فتح تذاكر جديدة عبر زر مخصص وقائمة منسدلة لاختيار القسم المطلوب.
*   **نظام أقسام مرن:**
    *   إنشاء أقسام تذاكر متعددة باستخدام أمر `/ctc`.
    *   كل قسم له فئة (Category) خاصة به للتذاكر النشطة وفئة أخرى للتذاكر المؤرشفة.
    *   إمكانية تخصيص اسم وأيقونة (Emoji) لكل قسم.
*   **أرشفة متقدمة:** أمر `/close` يقوم بإغلاق التذكرة ونقلها إلى فئة الأرشيف المخصصة لقسمها، مع تعديل الصلاحيات لمنع إرسال رسائل جديدة (مع السماح بالقراءة للمشرفين وصاحب التذكرة).
*   **تكامل مع الرسائل الخاصة (DM):**
    *   يمكن للمستخدمين الرد على رسائل البوت في الخاص للتواصل داخل تذكرتهم المفتوحة.
    *   يمكن للمشرفين استخدام أمر `/r` للرد على صاحب التذكرة مباشرة في رسائله الخاصة من داخل قناة التذكرة.
    *   يتم إرسال إشعارات للمستخدم عند فتح أو إغلاق تذكرته.
*   **إعداد مرن:** أمر `/setup` لإنشاء رسالة تفاعلية تحتوي على زر فتح التذاكر، مع إمكانية تخصيص النص والـ Embed.
*   **إدارة الصلاحيات:** يتم تعيين صلاحيات محددة تلقائيًا عند إنشاء التذكرة (للمستخدم، للبوت، ولرتبة المشرفين إن وُجدت).
*   **تخزين البيانات:** يتم حفظ إعدادات البوت والأقسام في ملف `config.json` وبيانات التذاكر النشطة في `tickets.json`.
*   **أوامر سلاش (Slash Commands):** يعتمد البوت بشكل كامل على أوامر السلاش لتجربة استخدام حديثة وسلسة.
*   **أوامر إضافية:** أمر `/ping` لمعرفة سرعة استجابة البوت.

## ⚙️ المتطلبات

*   **Python:** إصدار 3.8 أو أحدث.
*   **حساب بوت ديسكورد:** تحتاج إلى إنشاء بوت عبر بوابة مطوري ديسكورد.
*   **توكن البوت:** ستحتاج إلى توكن البوت الخاص بك.
*   **Privileged Gateway Intents:** يجب تفعيل الخيارات التالية في صفحة البوت على بوابة المطورين:
    *   `Server Members Intent`
    *   `Message Content Intent`

## 🚀 التثبيت والتشغيل

1.  **استنساخ المستودع (Clone):**
    ```bash
    git clone https://github.com/your-username/your-repo-name.git
    cd your-repo-name
    ```
    *(استبدل `your-username/your-repo-name` باسم المستخدم واسم المستودع الخاص بك)*

2.  **تثبيت المكتبات المطلوبة:**
    قم بإنشاء ملف باسم `requirements.txt` وضع بداخله السطر التالي:
    ```txt
    discord.py>=2.0.0
    ```
    ثم قم بتشغيل الأمر التالي في الطرفية (Terminal/CMD):
    ```bash
    pip install -r requirements.txt
    ```
    *(قد تحتاج لاستخدام `pip3` بدلاً من `pip` حسب نظام التشغيل وإعدادات Python لديك)*

3.  **إعداد ملف `config.json`:**
    *   قم بإنشاء ملف جديد في نفس مجلد البوت باسم `config.json`.
    *   انسخ والصق الهيكل التالي داخل الملف:
        ```json
        {
            "bot_token": "التوكن_الحقيقي_بتاعك_هنا",
            "guild_id": 0,
            "moderator_role_id": null,
            "ticket_prefix": "ticket-",
            "active_categories": {}
        }
        ```
    *   **قم بتعديل القيم:**
        *   `"bot_token"`: استبدل `"التوكن_الحقيقي_بتاعك_هنا"` بتوكن البوت الفعلي الخاص بك (حافظ على علامات الاقتباس). **هذا ضروري!**
        *   `"guild_id"`: استبدل `0` بالـ ID الرقمي للسيرفر الذي سيعمل فيه البوت. **هذا ضروري!** (يمكنك الحصول عليه بتفعيل وضع المطور في ديسكورد والنقر كليك يمين على اسم السيرفر واختيار "Copy Server ID").
        *   `"moderator_role_id"`: (اختياري ولكن موصى به) استبدل `null` بالـ ID الرقمي لرتبة المشرفين أو فريق الدعم. إذا لم تضع ID، لن يتم منح صلاحيات خاصة تلقائية لهذه الرتبة في التذاكر.
        *   `"ticket_prefix"`: (اختياري) البادئة التي ستظهر في بداية اسم كل قناة تذكرة يتم إنشاؤها (الافتراضي هو `"ticket-"`).
        *   `"active_categories"`: اتركه فارغًا `{}` في البداية. سيقوم البوت بتعبئته عند استخدامك لأمر `/ctc` لإنشاء أقسام التذاكر.

4.  **تشغيل البوت:**
    افتح الطرفية في مجلد البوت وقم بتشغيل الأمر:
    ```bash
    python Ticket.py
    ```
    *(أو `python3 Ticket.py`)*

5.  **دعوة البوت للسيرفر:**
    *   استخدم الرابط الذي يظهر في الطرفية عند تشغيل البوت بنجاح (عادة يبدأ بـ `https://discord.com/api/oauth2/authorize?...`).
    *   أو قم بإنشاء رابط دعوة بنفسك من بوابة المطورين، مع التأكد من منح البوت الصلاحيات اللازمة (على الأقل: `Send Messages`, `Manage Channels`, `Manage Messages`, `Embed Links`, `Attach Files`, `Read Message History`, `View Channel`). صلاحية `Administrator` تمنح كل الصلاحيات المطلوبة.

## 🛠️ الأوامر المتاحة (Slash Commands)

*   `/setup`: (للمشرفين - يتطلب `Manage Server`) يقوم بإرسال رسالة تحتوي على زر لفتح التذاكر في القناة الحالية.
*   `/ctc <internal_key> <display_name> [emoji]`: (للمشرفين - يتطلب `Manage Server`) يقوم بإنشاء قسم تذاكر جديد مع فئة نشطة وفئة أرشيف خاصة به.
    *   `internal_key`: معرف داخلي فريد للقسم (يفضل بالإنجليزية بدون مسافات).
    *   `display_name`: الاسم الذي سيظهر للمستخدمين في قائمة اختيار الأقسام.
    *   `emoji`: (اختياري) الأيقونة التي ستظهر بجانب اسم القسم.
*   `/close`: (للمشرفين - يتطلب `Manage Messages`) يقوم بإغلاق وأرشفة التذكرة الحالية ونقلها إلى فئة الأرشيف المخصصة لقسمها.
*   `/r <message>`: (للمشرفين - يتطلب `Manage Messages`) يقوم بإرسال رسالة إلى صاحب التذكرة الحالي في رسائله الخاصة.
*   `/ping`: (للجميع) يعرض سرعة استجابة البوت (البنج).

## 📝 كيفية الاستخدام

1.  **الإعداد الأولي (مرة واحدة):**
    *   شغل البوت وتأكد من وجوده في السيرفر.
    *   استخدم أمر `/ctc` لإنشاء قسم تذاكر واحد على الأقل (مثال: `/ctc support الدعم 🆘`).
    *   اذهب إلى القناة التي تريد أن يظهر فيها زر فتح التذاكر واستخدم أمر `/setup`. قم بتعبئة الحقول المطلوبة في النافذة المنبثقة.
2.  **المستخدمون:**
    *   اضغط على الزر الذي تم إنشاؤه بواسطة أمر `/setup`.
    *   اختر القسم المطلوب من القائمة المنسدلة.
    *   سيتم إنشاء قناة تذكرة خاصة بك وسيتم عمل منشن لك فيها.
    *   اشرح مشكلتك في القناة أو قم بالرد على رسالة البوت التي وصلتك في الخاص.
3.  **المشرفون:**
    *   سيتم عمل منشن لرتبة المشرفين (إذا تم تحديدها في `config.json`) في قناة التذكرة الجديدة.
    *   تفاعل مع المستخدم داخل قناة التذكرة.
    *   استخدم `/r <رسالتك>` للرد على المستخدم في الخاص إذا لزم الأمر.
    *   عند حل المشكلة، استخدم `/close` لأرشفة التذكرة.

## 📁 الملفات الهامة

*   `Ticket.py`: الكود المصدري الرئيسي للبوت.
*   `config.json`: ملف الإعدادات الأساسية للبوت (التوكن، آي دي السيرفر، رتبة المشرفين، إلخ).
*   `tickets.json`: ملف يتم إنشاؤه وتحديثه تلقائيًا بواسطة البوت لتخزين بيانات التذاكر النشطة حاليًا (مثل ID المستخدم المرتبط بكل قناة تذكرة).
*   `requirements.txt`: قائمة بالمكتبات المطلوبة لتشغيل البوت.

---

*نتمنى أن يكون هذا البوت مفيدًا لسيرفرك!*

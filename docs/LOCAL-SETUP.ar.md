# التشغيل الحالي على هذا الجهاز

التطبيق يعمل محليًا على `http://127.0.0.1:8000/` باستخدام PostgreSQL وRedis وعامل Celery ومجدول beat، مع نموذج Qwen محلي حقيقي. لا يعتمد هذا التشغيل على SQLite أو على تنفيذ المهام داخل طلب HTTP.

| الخدمة | العنوان المحلي |
| --- | --- |
| واجهة الويب | `127.0.0.1:8000` |
| PostgreSQL 18.6 | `127.0.0.1:55432` |
| Redis 8.10.3 | `127.0.0.1:6389` |
| خادم النموذج المحلي | `127.0.0.1:8081` |

لا توجد منافذ مكشوفة للشبكة الخارجية. بيانات الاتصال في `.env`، وحسابات العرض المولدة في `.local/demo-credentials.txt`. بقيت كلمات مرور العرض كما كانت قبل النقل إلى PostgreSQL.

يمكن تغيير اللغة من زر **العربية / English** في رأس الصفحة. لمراجعة التحليل والمسودة، سجّل الدخول بحساب `demo_employee` أو `demo_admin`؛ العميل لا يرى المسودات أو الملاحظات الداخلية.

## إعادة التشغيل بعد إعادة تشغيل الجهاز

أدوات هذا الإعداد المحمول موجودة داخل `.local` ومقصودة لهذا الجهاز فقط. إذا كانت الخدمات تعمل بالفعل، فلا تبدأ نسخة ثانية من عامل Celery أو المجدول.

```powershell
cd C:\Users\User\smart
.\.venv\Scripts\python .local\start_native_stack.py
.\.venv\Scripts\python .local\start_local_ai.py
.\.venv\Scripts\python .local\start_application.py
```

الأدوات المحمولة لا تُرفع إلى GitHub. من يستنسخ المستودع يستخدم خطوات README، أو Docker على جهاز تتوفر فيه بيئة Docker/Linux.

## إعادة التحقق

```powershell
.\.venv\Scripts\python manage.py test --settings=config.ci_settings
.\.venv\Scripts\python scripts\smoke_http.py
.\.venv\Scripts\python scripts\smoke_http.py --language ar
.\.venv\Scripts\python scripts\verify_worker_stack.py
.\.venv\Scripts\python scripts\verify_worker_stack.py --with-ai
```

يتطلب آخر أمرين أدوات التطوير من `requirements-dev.txt`. ينشئ فحص التكامل عاملًا مؤقتًا على قائمة معزولة وخادم SMTP محليًا، ثم يزيل بياناته التجريبية. لا يرسل بريدًا خارجيًا. النموذج الصغير للعرض، ولا يغني عن مراجعة الموظف للنتائج.

## البيانات والنسخ المحلية

- `.local/migration-result.json`: نتيجة مطابقة أعداد السجلات وبصمات كلمات المرور بعد النقل.
- `.local/db-before-postgres.sqlite3`: نسخة SQLite قبل النقل؛ قاعدة `db.sqlite3` الأصلية باقية أيضًا.
- `.local/.env.before-postgres`: إعداد التطوير السابق.
- `.local/postgres-tests.log`: سجل اختبارات PostgreSQL.
- `.local/portfolio-checks.log`: آخر مراجعة للجودة وHTTP والتكامل مع العامل والنموذج وSMTP.
- `.local/backups/portfolio-before-review.dump`: نسخة PostgreSQL خاصة قبل مراجعة Portfolio؛ اختُبرت استعادتها في قاعدة منفصلة.
- `.local/preservation-review.json`: إثبات تطابق السجلات وكلمات المرور بعد المراجعة.
- `.local/worker-stack-result.log`: نتيجة فحص العامل والنموذج وSMTP.
- `.local/real-ai-analysis.json`: نتائج نموذج حقيقية لطلبات اختبارية مصطنعة بالإنجليزية والعربية.
- `.local/web.log`, `.local/worker.log`, `.local/beat.log`: سجلات الخدمات المحلية.

هذه ملفات محلية مستثناة من Git. تحتوي بعض النسخ على بيانات حسابات أو إعدادات خاصة، فلا تنشرها.

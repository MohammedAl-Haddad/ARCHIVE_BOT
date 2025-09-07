# خريطة الاختبارات

يوضح الجدول التالي التغطية الحالية للاختبارات وما ينقصها.

| الاختبار | ما الذي يتحقق منه | الملفات المعنية | what's missing |
|---|---|---|---|
| tests/test_navigation_cards.py | التحقق من نسخ المواد عند الضغط على بطاقة مادة | bot/handlers/navigation_tree.py; bot/navigation/nav_stack.py; bot/db/materials.py | لا يغطي أنواع البطاقات الأخرى أو حالات الفشل |
| tests/test_navigation_categories.py | أزرار تصنيفات القسم ترسل المواد الصحيحة لكل فئة | bot/handlers/navigation_tree.py; bot/navigation/nav_stack.py; bot/db/materials.py; bot/db/subjects.py | لا يختبر غياب التصنيفات أو أقسام بديلة |
| tests/test_duplicate_permissions.py | صلاحيات إلغاء التكرارات أثناء الإدخال | bot/handlers/ingestion.py | لا يختبر إجراءات أخرى مثل الاستبدال أو رسائل الرفض |
| tests/test_exam_ingestion.py | تحويل الوسوم الخاصة بالامتحانات إلى التصنيف الصحيح أثناء الإدخال | bot/handlers/ingestion.py | لا يغطي الوسوم الخاطئة أو وجود أكثر من ملف |
| tests/test_formatting.py | تنسيق الأسماء وإزالة المحارف غير المرغوبة | bot/utils/formatting.py | لا يختبر الحالات الحديّة مثل الأرقام أو علامات الترقيم |
| tests/test_hashtags.py | تحليل الوسوم لمحتويات المحاضرات والأقسام والبطاقات وموارد الفصل | bot/parser/hashtags.py | لا يختبر التسلسلات الخاطئة أو الوسوم المتضاربة |
| tests/test_last_children_cache.py | التخزين المؤقت لقائمة العناصر في شجرة التصفح وانتهاء صلاحيتها | bot/handlers/navigation_tree.py | لا يغطي تعدد المستخدمين أو الإبطال اليدوي |
| tests/test_navigation_section_skip.py | سلوك التصفح عند وجود قسم واحد أو عدة أقسام مع تخطي أو عدمه | bot/handlers/navigation_tree.py; bot/navigation/nav_stack.py; bot/db/materials.py; bot/db/rbac.py | لا يختبر اختلاف صلاحيات المستخدم أو حالات خاصة أخرى |
| tests/test_navigation_syllabus.py | إرسال مادة التوصيف عند اختيار البطاقة | bot/handlers/navigation_tree.py; bot/db/materials.py | لا يغطي تعدد ملفات التوصيف أو غيابها |
| tests/test_navigation_term_exclusions.py | إخفاء أنواع محددة من الموارد في قائمة الفصل وإتاحتها داخل الأقسام | bot/navigation/tree.py | لا يتحقق من التفاعل مع نظام الصلاحيات أو التحديثات الديناميكية |
| tests/test_navigation_tree.py | وظائف شجرة التصفح: بناء المسار، الأزرار الخلفية، التصفية بالصلاحيات، تحميل العناصر، ترجمات الأقسام | bot/navigation/nav_stack.py; bot/handlers/navigation_tree.py; bot/navigation/tree.py | لا يختبر حالات الخطأ أو حدود الأداء القصوى |
| tests/test_nav_stack.py | عمليات مكدس التصفح الأساسية (push/pop/path) | bot/navigation/nav_stack.py | لا يختبر التخزين المستمر أو الحالات غير الصالحة |
| tests/test_paginated_keyboard.py | بناء لوحات أزرار مقسمة إلى صفحات | bot/keyboards/builders/paginated.py | لا يغطي الصفحة الأخيرة أو أحجام لوحات مختلفة |
| tests/test_parser.py | استخراج السنة الهجرية من النصوص | bot/parser/__init__.py | لا يختبر صيغاً متعددة أو مدخلات غير صالحة |
| tests/test_single_hashtag_ingestion.py | معالجة منشور بوسم واحد في المواضيع أو الدردشة العامة مع/بدون ربط | bot/handlers/ingestion.py | لا يختبر تعدد الوسوم أو كشف التكرار |
| tests/test_subject_sections.py | استرجاع الأقسام والبطاقات المتاحة لمادة معينة بما فيها التوصيف | bot/db/subjects.py; bot/db/materials.py | لا يغطي مواد متعددة أو عدة أقسام |
| tests/test_term_options.py | عرض خيارات الفصل حسب توفر الموارد | bot/handlers/navigation_tree.py; bot/navigation/tree.py | لا يختبر المستخدمين غير المصرح لهم أو الموارد المفقودة |
| tests/test_term_resource_ingestion.py | إدخال موارد الفصل عبر الوسوم، وتسجيل المجموعات غير المعروفة، وتصنيف "misc" | bot/handlers/ingestion.py | لا يتحقق من فشل الإدخال أو أخطاء الصلاحيات |
| tests/test_term_resources.py | وظائف قاعدة بيانات موارد الفصل (إدخال، تحقق، استرجاع، سرد) | bot/db/term_resources.py | لا يغطي التحديث أو الحذف أو حالات الخطأ |

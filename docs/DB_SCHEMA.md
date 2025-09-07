# مخطط قاعدة البيانات (DB_SCHEMA)

يوضح هذا المستند بنية قاعدة البيانات المستخدمة في البوت، بما في ذلك الجداول، الأعمدة، الفهارس، والعلاقات فيما بينها.

## الجداول

### levels
- **الوصف:** مستويات الدراسة.
- **الأعمدة:**
  - `id` INTEGER مفتاح أساسي تلقائي التزايد.
  - `name` TEXT غير فارغ وفريد.

### terms
- **الوصف:** الفصول الدراسية.
- **الأعمدة:**
  - `id` INTEGER مفتاح أساسي.
  - `name` TEXT غير فارغ وفريد.

### subjects
- **الوصف:** المقررات الدراسية المرتبطة بمستوى وترم.
- **الأعمدة:**
  - `id` INTEGER مفتاح أساسي.
  - `code` TEXT رمز المقرر.
  - `name` TEXT اسم المقرر.
  - `level_id` INTEGER مرجع إلى `levels(id)`.
  - `term_id` INTEGER مرجع إلى `terms(id)`.
  - `sections_mode` TEXT مع قيد CHECK للقيم:
    `theory_only`, `theory_discussion`, `theory_discussion_lab` (افتراضيًا الأخيرة).
- **الفهارس:** `idx_subjects_level`, `idx_subjects_term`, `idx_subjects_term_name` على الحقول المشار إليها.

### years
- **الوصف:** سنوات التقويم (هجري/ميلادي).
- **الأعمدة:**
  - `id` INTEGER مفتاح أساسي.
  - `name` TEXT غير فارغ وفريد.

### lecturers
- **الوصف:** المحاضرون أو المناقشون.
- **الأعمدة:**
  - `id` INTEGER مفتاح أساسي.
  - `name` TEXT غير فارغ وفريد.
  - `role` TEXT مع قيد CHECK للقيم `lecturer`, `ta`, `lab` (افتراضيًا `lecturer`).

### admins
- **الوصف:** الحسابات الإدارية.
- **الأعمدة:**
  - `id` INTEGER مفتاح أساسي.
  - `tg_user_id` INTEGER فريد.
  - `name` TEXT.
  - `role` TEXT غير فارغ.
  - `permissions_mask` INTEGER غير فارغ.
  - `level_scope` TEXT افتراضيًا `all`.
  - `is_active` INTEGER افتراضيًا 1.
- **الفهارس:** `idx_admins_tg_user_id`.

### groups
- **الوصف:** مجموعات تيليجرام المرتبطة بمستوى وترم.
- **الأعمدة:**
  - `id` INTEGER مفتاح أساسي.
  - `tg_chat_id` INTEGER فريد وغير فارغ.
  - `title` TEXT.
  - `level_id` INTEGER مرجع إلى `levels(id)`.
  - `term_id` INTEGER مرجع إلى `terms(id)`.
- **الفهارس:** `idx_groups_level`, `idx_groups_term`.

### topics
- **الوصف:** Topics داخل المجموعات تربط الموضوع بمادة وقسم.
- **الأعمدة:**
  - `id` INTEGER مفتاح أساسي.
  - `group_id` INTEGER مرجع إلى `groups(id)`.
  - `tg_topic_id` INTEGER معرف الـTopic داخل المجموعة.
  - `subject_id` INTEGER مرجع إلى `subjects(id)`.
  - `section` TEXT مع قيد CHECK للقيم `theory`, `discussion`, `lab`, `field_trip`.
- **القيود:** مفتاح فريد مركب على `(group_id, tg_topic_id)`.
- **الفهارس:** `idx_topics_chat` (فريد)، `idx_topics_subject`.

### ingestions
- **الوصف:** سجلات عمليات الإدخال/الرفع.
- **الأعمدة:**
  - `id` INTEGER مفتاح أساسي.
  - `material_id` INTEGER مرجع إلى `materials(id)`.
  - `status` TEXT حالة العملية.
  - `tg_message_id` INTEGER معرف رسالة المصدر.
  - `admin_id` INTEGER مرجع إلى `admins(id)`.
  - `action` TEXT نوع العملية (افتراضيًا `add`).
  - `file_unique_id` TEXT معرف الملف الفريد.
  - `created_at` TEXT طابع زمني افتراضي.
- **الفهارس:** `idx_ingestions_material`, `idx_ingestions_admin`, `idx_ingestions_status`.

### materials
- **الوصف:** المواد التعليمية المرتبطة بمادة وقسم وتصنيف محتوى.
- **الأعمدة (مختصرة):**
  - `id` INTEGER مفتاح أساسي.
  - `subject_id` INTEGER مرجع إلى `subjects(id)`.
  - `section` TEXT مع قيد CHECK للقيم `theory`, `discussion`, `lab`, `field_trip`, `syllabus`, `apps`.
  - `category` TEXT مع قيد CHECK يشمل قيمًا مثل `lecture`, `slides`, `exam`, `booklet`, `video`, `summary`, `applications`, `references`, `practical` وغيرها.
  - `title` TEXT غير فارغ.
  - `url` TEXT (اختياري).
  - `year_id` INTEGER مرجع إلى `years(id)` (اختياري).
  - `lecturer_id` INTEGER مرجع إلى `lecturers(id)` (اختياري).
  - `tg_storage_chat_id`, `tg_storage_msg_id`, `file_unique_id` لتخزين الرسالة في القناة.
  - `source_chat_id`, `source_topic_id`, `source_message_id` لمصدر الرسالة.
  - `created_by_admin_id` INTEGER مرجع إلى `admins(id)`.
  - `created_at` TEXT طابع زمني افتراضي.
- **الفهارس:** `idx_materials_subject`, `idx_materials_year`, `idx_materials_lecturer`,
  `idx_materials_admin`, `idx_materials_section_created_at`, `idx_materials_core`, `idx_materials_storage`.

### term_resources
- **الوصف:** موارد عامة مرتبطة بمستوى وترم محددين.
- **الأعمدة:**
  - `id` INTEGER مفتاح أساسي.
  - `level_id` INTEGER مرجع إلى `levels(id)`.
  - `term_id` INTEGER مرجع إلى `terms(id)`.
  - `kind` TEXT مع قيد CHECK للقيم مثل `attendance`, `study_plan`, `channels`, `outcomes`, `tips`,
    `projects`, `programs`, `apps`, `forums`, `sites`, `misc`.
  - `tg_storage_chat_id`, `tg_storage_msg_id` لتحديد مكان التخزين.
  - `created_at` TEXT طابع زمني افتراضي.
- **الفهارس:** `idx_term_resources_level_term_kind`.

## العلاقات والقيود البارزة
- كل من `subjects.level_id` و`groups.level_id` و`term_resources.level_id` يرتبط بـ `levels(id)`.
- `subjects.term_id`, `groups.term_id` و`term_resources.term_id` ترتبط بـ `terms(id)`.
- `topics.group_id` يشير إلى `groups.id`، و`topics.subject_id` إلى `subjects.id` مع قيد فريد على `(group_id, tg_topic_id)`.
- `materials.subject_id`، `materials.year_id`، `materials.lecturer_id` و`materials.created_by_admin_id` ترتبط بالجداول المناظرة.
- `ingestions.material_id` و`ingestions.admin_id` ترتبط بـ `materials` و`admins` على التوالي.
- أعمدة متعددة تقيّد قيمها باستخدام CHECK مثل `topics.section`, `subjects.sections_mode`,
  `materials.section`, `materials.category`, `lecturers.role`، و`term_resources.kind`.



## ملخص العمليات

| العملية | الجداول المتأثرة | الأعمدة المكتوبة | المفاتيح/القيود |
|---------|------------------|------------------|-----------------|
| ربط مجموعة (`upsert_group`) | `groups` | `tg_chat_id`, `title`, `level_id`, `term_id` | `tg_chat_id` فريد؛ مفاتيح خارجية: `level_id`→`levels.id`, `term_id`→`terms.id` |
| ربط Topic (`bind`) | `topics`, `subjects`* | `group_id`, `tg_topic_id`, `subject_id`, `section` | مفتاح فريد `(group_id, tg_topic_id)`؛ مفاتيح خارجية إلى `groups` و`subjects`; قيد CHECK على `section` |
| إدخال مادة (`insert_material`) | `materials` | `subject_id`, `section`, `category`, `title`, `url`, `year_id`, `lecturer_id`, `source_*`, `created_by_admin_id` | مفاتيح خارجية إلى `subjects`, `years`, `lecturers`, `admins`; قيود CHECK على `section` و`category` |
| تسجيل الإدخال (`insert_ingestion`) | `ingestions` | `tg_message_id`, `admin_id`, `status`, `action`, `file_unique_id`, `material_id` | مفاتيح خارجية إلى `admins` و`materials` |
| تحديث التخزين (`update_material_storage`) | `materials` | `tg_storage_chat_id`, `tg_storage_msg_id`, `file_unique_id` | يعتمد على المفتاح الأساسي `id` |
| رفع مورد فصل (`insert_term_resource`) | `term_resources` | `level_id`, `term_id`, `kind`, `tg_storage_chat_id`, `tg_storage_msg_id` | مفاتيح خارجية إلى `levels` و`terms`; قيد CHECK على `kind` |

*تُحدَّث مادة موجودة في `subjects.sections_mode` عند اختيار «نظري فقط».


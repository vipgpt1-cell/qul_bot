"""Uzbek (Latin) messages. Texts are Telegram HTML; parameters are escaped by the caller."""

MESSAGES: dict[str, str] = {
    # ---- help & onboarding --------------------------------------------------------------
    "help.main": (
        "👋 <b>Qul Bot</b> — jamoaviy vazifalar yordamchisi.\n"
        "\n"
        "⚡ <b>Eng tez yo'l:</b> biror xabarga <b>javob berib</b> /task yuboring — "
        "xabar vazifaga aylanadi.\n"
        "\n"
        "Yoki bir qatorda:\n"
        "<code>/task Login xatosi #mobile @username !yuqori muddat:juma</code>\n"
        "\n"
        "Bo'limni tanlang 👇"
    ),
    "help.btn.create": "🆕 Vazifa qo'shish",
    "help.btn.workflow": "🔄 Jarayon",
    "help.btn.view": "🔍 Ko'rish va qidirish",
    "help.btn.team": "👥 Jamoa va sozlamalar",
    "help.page.create": (
        "🆕 <b>Vazifa qo'shish</b>\n"
        "\n"
        "<code>/task Sarlavha #nom @username !daraja muddat:ertaga</code>\n"
        "\n"
        "Faqat sarlavha shart, qolganlari ixtiyoriy:\n"
        "• <code>#nom</code> — yo'nalish (ro'yxat: /areas)\n"
        "• <code>@username</code> — mas'ul (bir nechta bo'lishi mumkin)\n"
        "• <code>!yuqori</code> — shoshilinch, yuqori, o'rta, past\n"
        "• <code>muddat:ertaga</code> — bugun, ertaga, juma, 25.10, 3d, 2w\n"
        "\n"
        "Ko'p qatorli xabarda 1-qator sarlavha, qolgani tavsif bo'ladi.\n"
        "💡 Xabarga <b>javob berib</b> /task yozsangiz, o'sha xabar vazifaga aylanadi."
    ),
    "help.page.workflow": (
        "🔄 <b>Jarayon</b>\n"
        "\n"
        "Kutilmoqda → Jarayonda → Tekshiruvda → Bajarildi\n"
        "\n"
        "/doing 12 — boshladim\n"
        "/done 12 — tugatdim (tekshiruvga ketadi)\n"
        "/approve 12 — tasdiqlash <i>(tekshiruvchi)</i>\n"
        "/reject 12 sabab — qaytarish <i>(tekshiruvchi)</i>\n"
        "/block 12 sabab — to'siq bor\n"
        "/cancel 12 · /reopen 12\n"
        "\n"
        "💡 Raqam yozmasdan, vazifa xabariga <b>javob berib</b> ham bo'ladi: "
        "<code>/done</code>, <code>/comment matn</code>.\n"
        "Vazifa kartasidagi tugmalar ham xuddi shuni qiladi."
    ),
    "help.page.view": (
        "🔍 <b>Ko'rish va qidirish</b>\n"
        "\n"
        "/my — mening vazifalarim\n"
        "/list — ochiq vazifalar: <code>/list mobile !yuqori</code>, "
        "<code>/list @username</code>, <code>/list all</code>\n"
        "/review — tekshiruv kutayotganlar\n"
        "/mobile — yo'nalish nomi bilan\n"
        "/find login — qidirish\n"
        "/digest — xulosa\n"
        "/info 12 yoki /t12 — vazifa tafsiloti\n"
        "/history 12 — vazifa tarixi"
    ),
    "help.page.team": (
        "👥 <b>Jamoa va sozlamalar</b>\n"
        "\n"
        "/team — jamoa (mutaxassislik bo'yicha)\n"
        "/specialty — o'z mutaxassisligingiz\n"
        "/edit 12 … · /assign 12 @user · /comment 12 matn\n"
        "\n"
        "<b>Adminlar:</b>\n"
        "/addarea nom · /delarea nom · /areas\n"
        "/role @user reviewer · /specialty @user qa\n"
        "/digest 09:00 — avtomatik xulosa vaqti · /digest off"
    ),
    "chatid.text": (
        "🆔 Chat ID: <code>{chat_id}</code>\n"
        "👤 Sizning ID: <code>{user_id}</code>\n"
        "\n"
        "Botni shu guruhda ishlatish uchun chat ID ni <code>ALLOWED_CHAT_IDS</code> ga, "
        "admin bo'lish uchun o'z ID ingizni <code>ADMIN_USER_IDS</code> ga qo'shing."
    ),
    # ---- statuses, priorities, roles ----------------------------------------------------
    "status.todo": "Kutilmoqda",
    "status.doing": "Jarayonda",
    "status.review": "Tekshiruvda",
    "status.testing": "Testda",
    "status.blocked": "Bloklangan",
    "status.done": "Bajarildi",
    "status.cancelled": "Bekor qilingan",
    "priority.urgent": "Shoshilinch",
    "priority.high": "Yuqori",
    "priority.normal": "O'rta",
    "priority.low": "Past",
    "role.admin": "Admin",
    "role.reviewer": "Tekshiruvchi",
    "role.member": "A'zo",
    # ---- task card ----------------------------------------------------------------------
    "created.header": "✅ <b>Vazifa yaratildi</b>",
    "edited.header": "✏️ <b>#{number}</b> yangilandi",
    "restored.header": "♻️ <b>#{number}</b> qayta tiklandi",
    "card.priority": "🚦 Ustuvorlik: {value}",
    "card.area": "📂 Yo'nalish: {label}",
    "card.due": "📅 Muddat: {date}{overdue}",
    "card.overdue": " — ⚠️ muddati o'tgan",
    "card.assignees": "👤 Mas'ul: {users}",
    "card.unassigned": "hali tayinlanmagan",
    "card.reporter": "✍️ Muallif: {user}",
    "card.source": '🔗 <a href="{url}">Xabarga o\'tish</a>',
    "card.comments": "💬 <b>Izohlar</b>",
    "card.release": "🏷 Reliz: {release}",
    "card.checklist": "☑️ Tekshiruv ro'yxati: {done}/{total} — /check {number}",
    "card.files": "📎 Ilovalar: {count} — /files {number}",
    "kind.bug": "🐞 Bug",
    # ---- buttons ------------------------------------------------------------------------
    "btn.start": "▶️ Boshlash",
    "btn.resume": "▶️ Davom ettirish",
    "btn.ready": "👀 Tekshiruvga",
    "btn.block": "⛔ Bloklash",
    "btn.approve": "✅ Tasdiqlash",
    "btn.reject": "↩️ Qaytarish",
    "btn.test_pass": "✅ Testdan o'tdi",
    "btn.test_fail": "🐞 Testdan o'tmadi",
    "btn.checklist": "☑️ Tekshiruv ro'yxati",
    "btn.cancel": "🚫 Bekor qilish",
    "btn.reopen": "🔄 Qayta ochish",
    "btn.me": "🙋 Menga",
    "btn.assign": "👥 Tayinlash",
    "btn.picker_done": "✔️ Tayyor",
    "btn.back": "⬅️ Orqaga",
    "btn.specialty_clear": "🚫 Tozalash",
    "btn.priority": "🚦 Ustuvorlik",
    "btn.delete_yes": "🗑 Ha, o'chirilsin",
    "btn.delete_no": "Yo'q",
    "toast.assigned_me": "Siz mas'ul etib belgilandingiz",
    "toast.unassigned": "Mas'uliyatdan olindi",
    "toast.specialty_saved": "Saqlandi",
    # ---- status change notices ----------------------------------------------------------
    "changed.todo": "🔄 <b>#{number}</b> qayta ochildi — {actor}\n{title}",
    "changed.doing": "🔵 <b>#{number}</b> ustida ish boshlandi — {actor}\n{title}",
    "changed.review": "👀 <b>#{number}</b> tekshiruvga yuborildi — {actor}\n{title}",
    "changed.blocked": "⛔ <b>#{number}</b> bloklandi — {actor}\n{title}",
    "changed.done": "✅ <b>#{number}</b> bajarildi va tasdiqlandi — {actor}\n{title}",
    "changed.cancelled": "🚫 <b>#{number}</b> bekor qilindi — {actor}\n{title}",
    "changed.testing": "🧪 <b>#{number}</b> testga o'tdi — {actor}\n{title}",
    "changed.test_failed": "🐞 <b>#{number}</b> testdan o'tmadi — {actor}\n{title}",
    "changed.rejected": "↩️ <b>#{number}</b> qayta ishlash uchun qaytarildi — {actor}\n{title}",
    "changed.reason": "💬 Sabab: {reason}",
    "notify.reviewers": "🔍 Tekshiruvchilar: {users}",
    "notify.testers": "🧪 Testerlar: {users}",
    "notify.assignees": "👤 Mas'ullar: {users}",
    "notify.assigned": "🔔 Mas'ul etib belgilandi: {users}",
    "notify.auto_assigned": "👤 {user} mas'ul etib belgilandi",
    "assigned.done": "👤 <b>#{number}</b> — mas'ul: {users}",
    "unassigned.done": "👤 <b>#{number}</b> — {users} mas'uliyatdan olindi",
    "comment.done": "💬 <b>#{number}</b> — {user}: {text}",
    "delete.confirm": "🗑 <b>#{number}</b> vazifasi o'chirilsinmi?\n{title}",
    "delete.done": "🗑 <b>#{number}</b> o'chirildi. Admin uni /restore {number} bilan tiklay oladi.",
    "delete.cancelled": "<b>#{number}</b> o'chirilmadi.",
    # ---- lists & digest -----------------------------------------------------------------
    "list.title": "📋 <b>Vazifalar</b>",
    "list.total": "Jami: {count}",
    "list.empty": "Hozircha vazifa yo'q 🎉",
    "list.with_closed": "yopilganlar bilan",
    "list.bugs": "🐞 Buglar",
    "digest.title": "🗓 <b>Xulosa</b> — {date}",
    "digest.all_clear": (
        "Hammasi joyida: muddati o'tgan, tekshiruv kutayotgan yoki egasiz vazifalar yo'q 🎉"
    ),
    "digest.overdue": "⚠️ Muddati o'tgan",
    "digest.due_today": "📅 Bugun muddati",
    "digest.in_review": "👀 Tekshiruv kutmoqda",
    "digest.in_testing": "🧪 Testda",
    "digest.blocked": "⛔ Bloklangan",
    "digest.unassigned": "🙋 Mas'ulsiz",
    "digest.more": "… yana {count} ta",
    "digest.enabled": "✅ Avtomatik xulosa yoqildi: har ish kuni {time} ({tz}).",
    "digest.disabled": "🔕 Avtomatik xulosa o'chirildi. Yoqish: /digest on",
    "digest.schedule_on": "🕘 Avtomatik xulosa: har ish kuni {time} ({tz})",
    "digest.schedule_off": "🔕 Avtomatik xulosa o'chirilgan (admin yoqishi mumkin: /digest on)",
    "find.title": "🔎 <b>Qidiruv:</b> «{query}»",
    "find.empty": "🔎 «{query}» bo'yicha hech narsa topilmadi.",
    "find.more": "… yana {count} ta. Aniqroq so'z yozing.",
    # ---- history ----------------------------------------------------------------------
    "history.title": "🕘 <b>#{number}</b> tarixi\n{title}",
    "history.created": "🆕 {actor} yaratdi",
    "history.status": "🔄 {actor}: {source} → {target}",
    "history.reason": " — «{reason}»",
    "history.assigned": "👤 {actor} → {user} tayinlandi",
    "history.auto_assigned": "👤 {actor} mas'ul bo'ldi",
    "history.unassigned": "👤 {actor} → {user} mas'uliyatdan olindi",
    "history.edited": "✏️ {actor} o'zgartirdi: {fields}",
    "history.commented": "💬 {actor} izoh qoldirdi",
    "history.checklist": "☑️ {actor} tekshiruv ro'yxatini yangiladi",
    "history.deleted": "🗑 {actor} o'chirdi",
    "history.restored": "♻️ {actor} qayta tikladi",
    "history.field.title": "nom",
    "history.field.description": "tavsif",
    "history.field.priority": "ustuvorlik",
    "history.field.area": "yo'nalish",
    "history.field.due": "muddat",
    "history.field.release": "reliz",
    # ---- assignee picker ----------------------------------------------------------------
    "picker.menu": "👥 <b>Kimga tayinlaymiz?</b> Guruhni tanlang:",
    "picker.group": "👥 <b>{specialty}</b> — ismni bosing (qayta bossangiz olib tashlanadi)",
    # ---- specialties --------------------------------------------------------------------
    "specialty.mobile": "Mobile",
    "specialty.frontend": "Frontend",
    "specialty.backend": "Backend",
    "specialty.pm": "PM",
    "specialty.qa": "QA",
    "specialty.devops": "DevOps",
    "specialty.other": "Boshqa",
    "specialty.none": "Belgilanmagan",
    "specialty.choose": "Mutaxassisligingizni tanlang:",
    "specialty.saved": "✅ Mutaxassislik: {specialty}",
    "specialty.changed": "✅ {users} — mutaxassislik: {specialty}",
    # ---- bug reports ------------------------------------------------------------------
    "bug.intro": "🐞 <b>Bug hisoboti</b> — savollarga <b>javob berib</b> yozing. "
    "O'tkazib yuborish: <code>-</code>, bekor qilish: /cancel",
    "bug.ask.title": "1/6. Qisqacha: nima ishlamayapti?",
    "bug.ask.steps": "2/6. Qanday takrorlash mumkin? (qadamlar)",
    "bug.ask.expected": "3/6. Nima bo'lishi kerak edi?",
    "bug.ask.actual": "4/6. Aslida nima bo'ldi?",
    "bug.ask.device": "5/6. Qurilma va versiya (masalan: iPhone 13, iOS 18; ilova 1.4.0)",
    "bug.ask.severity": "Jiddiylik darajasi:",
    "bug.ask.screenshot": "6/6. Skrinshot yoki video yuboring (javob qilib) — yoki <code>-</code>",
    "bug.severity.critical": "🔴 Kritik",
    "bug.severity.major": "🟠 Jiddiy",
    "bug.severity.minor": "🟡 O'rtacha",
    "bug.severity.trivial": "🟢 Kichik",
    "bug.severity_chosen": "Jiddiylik: {severity}",
    "bug.field.steps": "🔁 Qadamlar",
    "bug.field.expected": "✅ Kutilgan natija",
    "bug.field.actual": "❌ Haqiqiy natija",
    "bug.field.device": "📱 Qurilma",
    "bug.created": "🐞 <b>Bug qayd etildi</b>",
    "bug.assign_hint": "👥 Mas'ulni tanlang: kartadagi <b>Tayinlash</b> tugmasi.",
    "bug.cancelled": "Bug hisoboti bekor qilindi.",
    "bug.not_your_form": "Bu boshqa odamning bug hisoboti.",
    # ---- checklists -------------------------------------------------------------------
    "check.title": "☑️ <b>#{number}</b> tekshiruv ro'yxati ({done}/{total})",
    "check.empty": (
        "Ro'yxat bo'sh. Qo'shish: <code>/check {number} Login ishlaydi; Dark mode</code>"
    ),
    "check.hint": "Bandni bosing — belgilanadi. Qo'shish: <code>/check {number} matn</code>, "
    "o'chirish: <code>/check {number} -2</code>",
    # ---- releases ---------------------------------------------------------------------
    "release.none": "Hali reliz yo'q. Vazifaga reliz qo'shing: <code>/edit 12 v:1.4.0</code> "
    "yoki <code>/task ... v:1.4.0</code>",
    "release.list_title": "🏷 <b>Relizlar</b>",
    "release.list_row": "{mark} <b>{release}</b> — {done}/{total} tayyor · /release {release}",
    "release.list_hint": "Hisobot: <code>/release 1.4.0</code>",
    "release.title": "🏷 <b>Reliz {release}</b> — {verdict}",
    "release.ready": "✅ chiqarishga tayyor",
    "release.not_ready": "⛔ hali tayyor emas",
    "release.totals": "Jami: {total} · ✅ {done} bajarildi · 🚫 {cancelled} bekor",
    "release.open_bugs": "🐞 Ochiq buglar: {count} ({breakdown})",
    "release.open_checks": "☑️ Belgilanmagan tekshiruv bandlari: {count}",
    "release.pending": "<b>Qolgan ishlar:</b>",
    # ---- QA settings & files ----------------------------------------------------------
    "qa.on": "🧪 QA bosqichi <b>yoqilgan</b>. Tekshiruvdan o'tgan vazifa testga o'tadi.\n"
    "Testerlar: {users}",
    "qa.no_testers": "🧪 QA bosqichi yoqilgan, lekin jamoada QA yo'q — vazifalar "
    "to'g'ridan-to'g'ri bajarildi bo'ladi. Tester qo'shish: <code>/specialty @username qa</code>",
    "qa.off": "🧪 QA bosqichi <b>o'chirilgan</b>: tasdiqlangan vazifa darhol bajarildi bo'ladi.",
    "qa.hint": "Admin: <code>/qa on</code> yoki <code>/qa off</code>",
    "files.none": "📎 <b>#{number}</b> da ilova yo'q.",
    "files.caption": "📎 #{number} — {title}",
    # ---- areas & team -------------------------------------------------------------------
    "areas.title": "📂 <b>Yo'nalishlar</b>",
    "areas.empty": (
        "Hali yo'nalish yo'q. Admin qo'shishi mumkin: <code>/addarea mobile Mobil ilova</code>"
    ),
    "areas.hint": "Ro'yxat uchun yo'nalish nomini bosing. Vazifada: <code>#nom</code>",
    "area.added": "📂 Yo'nalish qo'shildi: #{slug} — {name}",
    "area.removed": "🗑 Yo'nalish o'chirildi: #{slug}. Vazifalar saqlanib qoldi.",
    "team.title": "👥 <b>Jamoa</b>",
    "team.hint": (
        "Mutaxassislik: <code>/specialty</code> (o'zingiz uchun, tugmalar bilan) yoki admin: "
        "<code>/specialty @username qa</code>.\n"
        "Rol berish (admin): <code>/role @username reviewer</code> yoki a'zo xabariga "
        "javob berib <code>/role reviewer</code>.\n"
        "Rollar: admin, reviewer (tekshiruvchi), member (a'zo)."
    ),
    "role.changed": "✅ {users} — endi: {role}",
    # ---- menu (Telegram's "/" list) -----------------------------------------------------
    "menu.task": "Yangi vazifa qo'shish",
    "menu.list": "Vazifalar ro'yxati",
    "menu.my": "Mening vazifalarim",
    "menu.review": "Tekshiruv kutayotganlar",
    "menu.info": "Vazifa tafsilotlari",
    "menu.doing": "Vazifani boshlash",
    "menu.done": "Vazifani tugatish",
    "menu.digest": "Kunlik xulosa",
    "menu.help": "Yordam",
    "menu.find": "Vazifa qidirish",
    "menu.bug": "Bug haqida xabar berish",
    "menu.bugs": "Ochiq buglar",
    "menu.check": "Tekshiruv ro'yxati",
    "menu.release": "Reliz hisoboti",
    "menu.qa": "QA bosqichi sozlamasi",
    "menu.specialty": "Mutaxassislik tanlash",
    "menu.approve": "Vazifani tasdiqlash",
    "menu.reject": "Vazifani qaytarish",
    "menu.assign": "Mas'ul biriktirish",
    "menu.edit": "Vazifani tahrirlash",
    "menu.areas": "Yo'nalishlar",
    "menu.addarea": "Yo'nalish qo'shish",
    "menu.team": "Jamoa a'zolari",
    "menu.role": "Rol berish",
    # ---- errors -------------------------------------------------------------------------
    "err.addarea_usage": "Foydalanish: <code>/addarea mobile Mobil ilova</code>",
    "err.admin_required": "🔒 Bu amal faqat adminlar uchun.",
    "err.already_assigned": "ℹ️ <b>#{number}</b> allaqachon shu odamga biriktirilgan.",
    "err.approver_required": (
        "🔒 Tekshiruvdagi yoki bajarilgan vazifani faqat tekshiruvchi yoki admin o'zgartira oladi."
    ),
    "err.area_exists": "ℹ️ #{slug} yo'nalishi allaqachon mavjud.",
    "err.area_name_too_long": "Yo'nalish nomi {max} belgidan oshmasligi kerak.",
    "err.bad_area_slug": (
        "Yo'nalish nomi lotin harfidan boshlanib, 2–20 ta harf, raqam yoki _ dan iborat "
        "bo'lishi kerak (masalan: mobile, backend)."
    ),
    "err.bad_filter": "Tushunmadim: <code>{word}</code>. Misol: <code>/list mobile !yuqori</code>",
    "err.comment_too_long": "Izoh {max} belgidan oshmasligi kerak.",
    "err.delarea_usage": "Foydalanish: <code>/delarea mobile</code>",
    "err.delete_denied": "🔒 Vazifani faqat muallifi yoki admin o'chira oladi.",
    "err.due_in_past": "📅 Muddat o'tgan sana bo'lishi mumkin emas: <code>{value}</code>",
    "err.empty_comment": "Izoh matnini yozing: <code>/comment 12 matn</code>",
    "err.empty_title": (
        "Vazifa nomini yozing: <code>/task Login xatosini tuzatish #mobile !yuqori</code>\n"
        "Yoki biror xabarga javob berib /task yuboring."
    ),
    "err.invalid_due": (
        "📅 Muddatni tushunmadim: <code>{value}</code>.\n"
        "Misollar: <code>muddat:ertaga</code>, <code>muddat:juma</code>, "
        "<code>muddat:25.10</code>, <code>muddat:3d</code>"
    ),
    "err.invalid_transition": (
        "Vazifani «{source}» holatidan «{target}» holatiga o'tkazib bo'lmaydi."
    ),
    "err.last_admin": "🔒 Oxirgi adminni olib bo'lmaydi.",
    "err.no_workspace": (
        "Bu buyruq vazifalar guruhi uchun. Guruhda ishlating yoki avval guruhda bot bilan "
        "muloqot qiling."
    ),
    "err.not_assigned": "ℹ️ Bu odam <b>#{number}</b> ga biriktirilmagan.",
    "err.not_deleted": "ℹ️ <b>#{number}</b> o'chirilmagan.",
    "err.not_involved": (
        "🔒 Bu vazifa boshqalarga biriktirilgan. O'zgartirish uchun mas'ul, muallif, "
        "tekshiruvchi yoki admin bo'lishingiz kerak."
    ),
    "err.not_member": "🔒 Siz bu guruh a'zosi sifatida topilmadingiz. Guruhda biror buyruq yozing.",
    "err.nothing_changed": "ℹ️ Hech narsa o'zgarmadi.",
    "err.nothing_to_edit": (
        "Nimani o'zgartirish kerak? Misol: "
        "<code>/edit 12 Yangi nom !yuqori muddat:juma #backend</code>"
    ),
    "err.reserved_area_slug": "«{slug}» nomi buyruq sifatida band. Boshqa nom tanlang.",
    "err.role_usage": (
        "Foydalanish: <code>/role @username reviewer</code> yoki a'zo xabariga javob berib "
        "<code>/role member</code>.\nRollar: admin, reviewer, member."
    ),
    "err.specialty_usage": (
        "Foydalanish: <code>/specialty backend</code> (o'zingiz uchun) yoki "
        "<code>/specialty @username qa</code> (admin). O'chirish: <code>/specialty -</code>"
    ),
    "err.bad_specialty": (
        "Mutaxassislik topilmadi: <code>{word}</code>.\n"
        "Mavjud: mobile, frontend, backend, pm, qa, devops, other."
    ),
    "err.bad_time": (
        "🕘 Vaqtni tushunmadim: <code>{value}</code>. "
        "Misol: <code>/digest 09:00</code>, <code>/digest off</code>"
    ),
    "err.find_usage": "Qidirish uchun kamida 2 ta belgi yozing: <code>/find login</code>",
    "err.bad_release": (
        "🏷 Reliz nomini tushunmadim: <code>{value}</code>. Misol: <code>v:1.4.0</code>"
    ),
    "err.release_not_found": "🏷 <b>{release}</b> relizida vazifa yo'q. Ro'yxat: /release",
    "err.check_usage": "Band matnini yozing: <code>/check 12 Login ishlaydi; Dark mode</code>",
    "err.check_not_found": "☑️ Bunday band topilmadi.",
    "err.checklist_full": "☑️ Ro'yxatda ko'pi bilan {max} ta band bo'lishi mumkin.",
    "err.checklist_incomplete": (
        "☑️ Tekshiruv ro'yxatida {count} ta belgilanmagan band bor. Avval ularni tugating: /check"
    ),
    "err.qa_inactive": "🧪 QA bosqichi faol emas (jamoada QA yo'q yoki /qa off).",
    "err.qa_required": "🧪 Bu vazifa avval testdan o'tishi kerak (QA bosqichi yoqilgan).",
    "err.tester_required": "🧪 Testdagi vazifani faqat QA yoki admin o'tkazadi yoki qaytaradi.",
    "err.qa_usage": "Foydalanish: <code>/qa on</code> yoki <code>/qa off</code>",
    "err.same_status": "ℹ️ Vazifa allaqachon shu holatda: {status}.",
    "err.self_approval": (
        "🔒 O'zingiz bajargan vazifani o'zingiz tasdiqlay olmaysiz. "
        "Boshqa tekshiruvchi tasdiqlashi kerak."
    ),
    "err.stale_button": "Bu tugma eskirgan. Vazifani /info 12 kabi buyruq bilan qayta oching.",
    "err.task_gone": "🔎 Vazifa topilmadi (o'chirilgan bo'lishi mumkin).",
    "err.task_not_found": "🔎 <b>#{number}</b> raqamli vazifa topilmadi.",
    "err.task_ref_required": (
        "Vazifa raqamini yozing, masalan: <code>/done 12</code> — "
        "yoki vazifa xabariga javob bering."
    ),
    "err.title_too_long": "Sarlavha {max} belgidan oshmasligi kerak.",
    "err.unexpected": "⚠️ Kutilmagan xatolik yuz berdi. Keyinroq urinib ko'ring.",
    "err.unknown_area": "📂 «{slug}» yo'nalishi topilmadi. Ro'yxat: /areas",
    "err.unknown_user": (
        "👤 @{username} topilmadi. U guruhda kamida bitta buyruq ishlatgan bo'lishi kerak "
        "yoki uning xabariga javob berib yozing."
    ),
}

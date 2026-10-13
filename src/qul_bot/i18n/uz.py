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
    # ---- buttons ------------------------------------------------------------------------
    "btn.start": "▶️ Boshlash",
    "btn.resume": "▶️ Davom ettirish",
    "btn.ready": "👀 Tekshiruvga",
    "btn.block": "⛔ Bloklash",
    "btn.approve": "✅ Tasdiqlash",
    "btn.reject": "↩️ Qaytarish",
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
    "changed.rejected": "↩️ <b>#{number}</b> qayta ishlash uchun qaytarildi — {actor}\n{title}",
    "changed.reason": "💬 Sabab: {reason}",
    "notify.reviewers": "🔍 Tekshiruvchilar: {users}",
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
    "digest.title": "🗓 <b>Xulosa</b> — {date}",
    "digest.all_clear": (
        "Hammasi joyida: muddati o'tgan, tekshiruv kutayotgan yoki egasiz vazifalar yo'q 🎉"
    ),
    "digest.overdue": "⚠️ Muddati o'tgan",
    "digest.due_today": "📅 Bugun muddati",
    "digest.in_review": "👀 Tekshiruv kutmoqda",
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
    "history.deleted": "🗑 {actor} o'chirdi",
    "history.restored": "♻️ {actor} qayta tikladi",
    "history.field.title": "nom",
    "history.field.description": "tavsif",
    "history.field.priority": "ustuvorlik",
    "history.field.area": "yo'nalish",
    "history.field.due": "muddat",
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

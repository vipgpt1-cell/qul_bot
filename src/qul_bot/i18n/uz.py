"""Uzbek (Latin) messages. Texts are Telegram HTML; parameters are escaped by the caller."""

MESSAGES: dict[str, str] = {
    # ---- help & onboarding --------------------------------------------------------------
    "help.text": (
        "👋 <b>Qul Bot</b> — jamoaviy vazifalar yordamchisi.\n"
        "\n"
        "<b>Vazifa qo'shish</b>\n"
        "<code>/task Login xatosini tuzatish #mobile @username !yuqori muddat:juma</code>\n"
        "Yoki biror xabarga <b>javob berib</b> /task yuboring — xabar vazifaga aylanadi.\n"
        "\n"
        "<b>Belgilar</b> (hammasi ixtiyoriy):\n"
        "• <code>#nom</code> — yo'nalish\n"
        "• <code>@username</code> — mas'ul\n"
        "• <code>!yuqori</code> — ustuvorlik: shoshilinch, yuqori, o'rta, past\n"
        "• <code>muddat:ertaga</code> — yoki juma, 25.10, 3d (3 kun), 2w (2 hafta)\n"
        "\n"
        "<b>Ro'yxatlar</b>\n"
        "/my — mening vazifalarim\n"
        "/list — ochiq vazifalar (masalan: <code>/list mobile !yuqori</code>)\n"
        "/review — tekshiruv kutayotganlar\n"
        "/digest — kunlik xulosa\n"
        "Yo'nalish nomi ham ishlaydi, masalan /mobile (yo'nalishlar: /areas)\n"
        "\n"
        "<b>Jarayon</b>\n"
        "/doing 12 — boshladim\n"
        "/done 12 — tugatdim (tekshiruvga ketadi)\n"
        "/approve 12 — tasdiqlash <i>(tekshiruvchi)</i>\n"
        "/reject 12 sabab — qaytarish <i>(tekshiruvchi)</i>\n"
        "/block 12 sabab — to'siq bor\n"
        "/info 12 · /edit 12 · /assign 12 · /comment 12 matn\n"
        "\n"
        "<b>Jamoa</b>: /team · /areas · /addarea · /role"
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
    "btn.priority": "🚦 Ustuvorlik",
    "btn.delete_yes": "🗑 Ha, o'chirilsin",
    "btn.delete_no": "Yo'q",
    "toast.assigned_me": "Siz mas'ul etib belgilandingiz",
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
    "err.same_status": "ℹ️ Vazifa allaqachon shu holatda: {status}.",
    "err.self_approval": (
        "🔒 O'zingiz bajargan vazifani o'zingiz tasdiqlay olmaysiz. "
        "Boshqa tekshiruvchi tasdiqlashi kerak."
    ),
    "err.stale_button": "Bu tugma eskirgan. Vazifani /info 12 kabi buyruq bilan qayta oching.",
    "err.task_gone": "🔎 Vazifa topilmadi (o'chirilgan bo'lishi mumkin).",
    "err.task_not_found": "🔎 <b>#{number}</b> raqamli vazifa topilmadi.",
    "err.task_ref_required": "Vazifa raqamini yozing, masalan: <code>/done 12</code>",
    "err.title_too_long": "Sarlavha {max} belgidan oshmasligi kerak.",
    "err.unexpected": "⚠️ Kutilmagan xatolik yuz berdi. Keyinroq urinib ko'ring.",
    "err.unknown_area": "📂 «{slug}» yo'nalishi topilmadi. Ro'yxat: /areas",
    "err.unknown_user": (
        "👤 @{username} topilmadi. U guruhda kamida bitta buyruq ishlatgan bo'lishi kerak "
        "yoki uning xabariga javob berib yozing."
    ),
}

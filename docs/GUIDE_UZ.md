# Qul Bot — jamoa uchun qo'llanma

Qul Bot guruhdagi vazifalarni yozib boradi: kim nima ustida ishlayapti, nima tekshiruvda,
nima bajarilgan. Barcha buyruqlarni **guruhda** yozasiz.

## 1. Vazifa qo'shish

```
/task Login xatosini tuzatish #mobile @username !yuqori muddat:juma
```

Faqat nomi shart, qolganlari ixtiyoriy:

| Belgi | Ma'nosi | Misol |
|---|---|---|
| `#nom` | yo'nalish | `#mobile`, `#backend` |
| `@username` | mas'ul (bir nechta bo'lishi mumkin) | `@alisher` |
| `!daraja` | ustuvorlik | `!shoshilinch`, `!yuqori`, `!o'rta`, `!past` |
| `muddat:…` | tugash vaqti | `muddat:bugun`, `ertaga`, `juma`, `25.10`, `3d` (3 kun), `2w` (2 hafta) |

**Eng qulay usul:** biror xabarga **javob (reply) berib** faqat `/task` yozing — o'sha xabar vazifaga
aylanadi va bot unga havola qoldiradi.

## 2. Vazifa yo'li

```
Kutilmoqda → Jarayonda → Tekshiruvda → Bajarildi
```

| Kim | Nima qiladi | Buyruq |
|---|---|---|
| Dasturchi | ishni boshlaydi | `/doing 12` |
| Dasturchi | ishni tugatadi → **tekshiruvga** ketadi | `/done 12` |
| Tekshiruvchi | qabul qiladi → **Bajarildi** | `/approve 12` (yoki `/done 12`) |
| Tekshiruvchi | qaytaradi (sabab bilan) | `/reject 12 testlar yo'q` |
| Istalgan | to'siq bor | `/block 12 API kutilmoqda` |

Dasturchi vazifani o'zi "Bajarildi" qila olmaydi — buni faqat tekshiruvchi yoki admin qiladi.
Har bir vazifa xabarida tugmalar ham bor (▶️ Boshlash, 👀 Tekshiruvga, ✅ Tasdiqlash, ↩️ Qaytarish...).

## 2.1. Raqam yozmasdan ishlash

Vazifa xabariga (kartaga) **javob berib** (reply) buyruq yozing — raqam shart emas:
`/done`, `/doing`, `/comment matn`, `/assign @username`, `/info`, `/history`.
Raqamni o'zingiz yozsangiz (`/done 12`), aynan o'sha vazifa olinadi.

## 3. Ko'rish

| Buyruq | Nima ko'rsatadi |
|---|---|
| `/my` | mening vazifalarim (botga shaxsiy yozsangiz ham ishlaydi) |
| `/list` | barcha ochiq vazifalar. Filtr: `/list mobile !yuqori`, `/list @alisher`, `/list all` |
| `/review` | tekshiruv kutayotganlar |
| `/mobile` | yo'nalish nomi bilan — o'sha yo'nalish vazifalari |
| `/find login` | vazifalarni qidirish (nom va tavsif bo'yicha, bajarilganlar ham) |
| `/history 12` | vazifa tarixi: kim, qachon, nima qilgan |
| `/digest` | muddati o'tgan, bugungi, tekshiruvdagi, bloklangan, egasiz vazifalar |
| `/info 12` yoki `/t12` | bitta vazifa to'liq (ro'yxatdagi `/t12` ni bossangiz ham ochiladi) |

## 4. O'zgartirish

* `/edit 12 Yangi nom #backend !shoshilinch muddat:ertaga`
* `/assign 12 @username` — mas'ul qo'shish (yoki odamning xabariga javob bering; `/assign 12` — o'zingizga)
* `/unassign 12 @username`
* `/comment 12 matn` — izoh
* `/delete 12` — o'chirish (muallif yoki admin), `/restore 12` — tiklash (admin)

## 5. Mutaxassislik va tayinlash

Har kim o'z mutaxassisligini belgilaydi: `/specialty` (tugmalar) yoki `/specialty backend`.
Mavjud: **mobile, frontend, backend, pm, qa, devops, other**. Admin boshqalarga ham belgilay oladi:
`/specialty @username qa`. `/team` jamoani mutaxassislik bo'yicha guruhlab ko'rsatadi.

Vazifa kartasidagi **👥 Tayinlash** tugmasi: avval guruhni (Mobile, Backend...), keyin odamni
tanlaysiz. Ismni bossangiz — tayinlanadi va unga xabar boradi; yana bossangiz — olib tashlanadi.

## 6. Adminlar uchun

* `/addarea mobile Mobil ilova` — yo'nalish qo'shish, `/delarea mobile`, `/areas`
* `/digest 09:00` — avtomatik xulosa vaqti, `/digest off` — o'chirish. Xulosa har **ish kuni** ertalab
  o'zi yuboriladi (faqat yozadigan narsa bo'lsa)
* `/role @username reviewer` — tekshiruvchi qilish (yoki xabariga javob bering: `/role reviewer`)
* Rollar: `admin`, `reviewer` (tekshiruvchi), `member` (a'zo). `/team` — kim qaysi rolda

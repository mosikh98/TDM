# Twitch Drops Miner

[English](./README.md) · **فارسی**

<div dir="rtl">

> استخراج خودکار درآپ‌های زمان‌دار توییچ، بدون پخش ویدیو و صدا.

</div>

![Python 3.12+](https://img.shields.io/badge/Python-3.12+-blue?style=flat-square&logo=python)
![License MIT](https://img.shields.io/badge/License-MIT-green?style=flat-square)

<div dir="rtl">

ماینر سبک و بدون رابط گرافیکیِ درآپ‌های توییچ: کمپین‌های قابل‌دریافت را پیدا می‌کند، یک کانال
زنده انتخاب می‌کند و پیشرفت درآپ‌ها را از طریق یک داشبورد وب نشان می‌دهد — بدون اینکه استریم را
دانلود کند.

</div>

<table>
  <tr>
    <td align="center"><img src="./docs/screenshots/dashboard-overview.jpg" width="260" alt="نمای کلی داشبورد"><br><sub>نمای کلی و پیشرفت زنده</sub></td>
    <td align="center"><img src="./docs/screenshots/dashboard-activity.jpg" width="260" alt="کانال‌ها، موجودی و ورود"><br><sub>کانال‌ها، موجودی و ورود</sub></td>
    <td align="center"><img src="./docs/screenshots/dashboard-menu.jpg" width="260" alt="منوی ناوبری"><br><sub>منوی ناوبری</sub></td>
  </tr>
</table>

<div dir="rtl">

## ویژگی‌ها

- استخراج کم‌حجم — بدون دانلود ویدیو و صدا
- پیدا کردن خودکار کمپین‌ها و انتخاب هوشمند کانال
- داشبورد وب: کمپین‌ها، کانال‌ها، موجودی، تنظیمات و تاریخچه
- رابط انگلیسی و **فارسی** با چیدمان کامل راست‌به‌چپ
- تم روشن و تیره
- رمز عبور اختیاری برای داشبورد (از رابط، API و اتصال‌های زنده محافظت می‌کند) و یک بنر هشدار تا
  وقتی داشبورد عمومی است و رمز ندارد
- دکمه‌ی **ریست اتصال** برای گرفتن کد ورود تازه وقتی ورود به توییچ گیر می‌کند
- تاریخچه‌ی درآپ‌ها با آمار و خروجی CSV
- اعلان تلگرام برای هر درآپ دریافت‌شده
- ماندگاری نشست ورود به توییچ
- اجرای Docker / بدون رابط، آماده‌ی Railway

## شروع سریع

### Docker Compose

</div>

```bash
git clone https://github.com/mosikh98/TDM
cd TDM
docker compose up -d --build
```

<div dir="rtl">

### اجرا از سورس

به Python نسخه‌ی ۳.۱۲ به بالا و [`uv`](https://docs.astral.sh/uv/) نیاز دارد:

</div>

```bash
uv sync
uv run main.py
```

<div dir="rtl">

آدرس <http://localhost:8080> را باز کنید و با توییچ وارد شوید.

## استقرار روی Railway

مخزن یک `Dockerfile` دارد، پس [Railway](https://railway.com) می‌تواند مستقیم از GitHub آن را بسازد و
اجرا کند. حدود چند دقیقه طول می‌کشد.

1. **سرویس را بسازید.** در Railway گزینه‌ی **New Project ← Deploy from GitHub repo** را بزنید و این
   مخزن را انتخاب کنید. Railway همان `Dockerfile` را می‌سازد و با هر push روی شاخه‌ی متصل، خودکار
   دوباره دیپلوی می‌کند.
2. **دامنه بسازید.** وارد سرویس شوید ← **Settings ← Networking ← Generate Domain**. اگر Railway
   پورت را پرسید، عدد **`8080`** را وارد کنید — داشبورد روی همین پورت اجرا می‌شود.

![Railway: Settings → Networking → Generate Domain](./docs/screenshots/railway-networking.jpg)

3. **دامنه‌ی ساخته‌شده را کپی کنید**، مثلاً `your-app-production.up.railway.app`، و `https://` را
   اول آن بگذارید: `https://your-app-production.up.railway.app`.
4. **آن را به‌عنوان متغیر اضافه کنید.** وارد سرویس شوید ← **Variables ← New Variable**، اسمش را
   **`PUBLIC_BASE_URL`** بگذارید و آدرسِ `https://…` مرحله‌ی ۳ را به‌عنوان مقدار وارد کنید. Railway
   خودش دوباره دیپلوی می‌کند.

![Railway: Variables → PUBLIC_BASE_URL](./docs/screenshots/railway-variables.jpg)

5. **آدرس را باز کنید و با توییچ وارد شوید** (داشبورد یک کد کوتاه نشان می‌دهد که باید در
   `twitch.tv/activate` وارد کنید)، سپس بازی‌هایتان را در **Games to Watch** اضافه کنید.
6. **همان لحظه یک رمز برای داشبورد بگذارید** (**Settings ← Dashboard password**). دامنه‌ی Railway از
   اینترنت در دسترس همه است؛ تا رمز نگذارید، هر کسی که لینک را بداند می‌تواند ماینر شما را کنترل
   کند. تا وقتی رمز نگذاشته‌اید، داشبورد یک بنر هشدار نشان می‌دهد.
7. **پیشنهادی — ماندگاری داده‌ها بین دیپلوی‌ها.** فایل‌سیستم کانتینر Railway با هر دیپلوی دوباره
   ساخته می‌شود. یک **Volume** به سرویس اضافه کنید و آن را روی **`/app/data`** مانت کنید تا ورود
   توییچ، تنظیمات و رمز داشبورد از بین نروند.

> [!NOTE]
> متغیر `PUBLIC_BASE_URL` آدرس عمومیِ HTTPS واقعیِ داشبورد را به برنامه می‌گوید؛ به این ترتیب کوکی‌های
> ورود با ویژگی `Secure` ساخته می‌شوند و درخواست‌های مرورگر با آن تطبیق داده می‌شوند. فقط **آدرس
> ریشه** را بنویسید — بدون مسیر و بدون متن اضافه؛ مقدار نامعتبر باعث می‌شود برنامه بالا نیاید و
> پیامی که با `PUBLIC_BASE_URL must be…` شروع می‌شود نشان بدهد. اگر این متغیر نباشد، برنامه از
> دامنه‌ای که Railway خودش تزریق می‌کند (`RAILWAY_PUBLIC_DOMAIN`) استفاده می‌کند، ولی بهتر است
> صریح تنظیمش کنید.

## نحوه‌ی استفاده

1. از طریق جریان Smart TV (`twitch.tv/activate`) وارد شوید — نشست ذخیره می‌شود.
2. صبر کنید کمپین‌ها بارگذاری شوند، سپس بازی‌هایتان را در **Games to Watch** اضافه کنید
   (اولویت `1` بالاترین است).
3. بگذارید در حال اجرا بماند — انتخاب کانال و پیگیری پیشرفت خودکار است.

> [!WARNING]
> تا وقتی ماینر در حال اجراست، با همان حساب توییچ تماشا نکنید — ممکن است پیشرفت درآپ به‌هم بریزد.
> حساب توییچ شما باید به حساب‌های بازی‌تان لینک باشد:
> [twitch.tv/drops/campaigns](https://www.twitch.tv/drops/campaigns)

> [!TIP]
> روی بعضی گوشی‌ها اپ توییچ نصب‌شده در ورود اختلال ایجاد می‌کند. اگر ورود مدام شکست می‌خورد،
> **ریست اتصال** را بزنید، اپ توییچ را حذف کنید، از داخل داشبورد دوباره وصل شوید و بعدش اپ توییچ را
> دوباره نصب کنید.

## به‌روزرسانی و اعلان «Update Available»

پایین صفحه، نسخه‌ی [`src/version.py`](./src/version.py) با **آخرین Release گیت‌هابِ همین مخزن**
([`mosikh98/TDM`](https://github.com/mosikh98/TDM)) مقایسه می‌شود. اگر نسخه‌ی جدیدتری باشد،
داشبورد عبارت **Update Available** را با لینکی به آن نشان می‌دهد. مخزنی که هنوز Release ندارد،
هیچ اعلانی نشان نمی‌دهد.

برای انتشار نسخه‌ی جدید:

1. نسخه را در `src/version.py` و `pyproject.toml` بالا ببرید و دستور `uv lock` را بزنید — این سه
   باید یکی باشند (یک تست این را بررسی می‌کند).
2. روی GitHub push کنید (Railway خودکار دوباره دیپلوی می‌کند).
3. در GitHub: **Releases ← Draft a new release**، تگ را `v1.0.1` (نسخه‌ی جدید) بگذارید و منتشر کنید.

مخزن فقط در یک جا تعریف شده است: `GITHUB_REPO` در
[`src/config/constants.py`](./src/config/constants.py)؛ لینک‌های پایین صفحه و بخش راهنما هم از همان
می‌آیند. اگر مخزن را تغییر نام دادید یا جابه‌جا کردید، همان‌جا عوضش کنید.

## اعلان تلگرام

**Settings ← Telegram Notifications** ← توکن ربات از [@BotFather](https://t.me/BotFather)
+ شناسه‌ی چت (Chat ID) ← **Test Connection**.

## رمز عبور داشبورد

**Settings ← Dashboard password** (۸ تا ۱۰۲۴ کاراکتر). رمز را فراموش کردید؟ ماینر را متوقف کنید،
فایل `data/web_auth.json` را پاک کنید، دوباره اجرا کنید و رمز جدید بگذارید.

## داده‌ها و لاگ‌ها

- Docker داده‌ها را در `./data` نگه می‌دارد (مانت‌شده روی `/app/data`)
- نصب از سورس هم داده‌ها را در `./data` نگه می‌دارد
- لاگ‌ها: مسیر `./logs:/app/logs` را مانت کنید
- روی Railway یک Volume روی `/app/data` وصل کنید (بخش «استقرار روی Railway» را ببینید)

## مشارکت

[CONTRIBUTING.md](./CONTRIBUTING.md) را ببینید. ایجنت‌های کدنویس باید از [AGENTS.md](./AGENTS.md)
پیروی کنند.

## مجوز

MIT — فایل [LICENSE](./LICENSE) را ببینید.

## سازندگان و قدردانی

این پروژه یک فورک است و بدون کار کسانی که قبل از آن بودند وجود نداشت:

- **[DevilXD/TwitchDropsMiner](https://github.com/DevilXD/TwitchDropsMiner)** — پروژه‌ی اصلیِ
  Twitch Drops Miner و سازنده‌ی آن [@DevilXD](https://github.com/DevilXD) (مجوز MIT).
- **[rangermix/TwitchDropsMiner](https://github.com/rangermix/TwitchDropsMiner)** — فورکِ دارای
  داشبورد وب که این مخزن از آن گرفته شده است.

از سازندگان اصلی و همه‌ی مشارکت‌کنندگان و مترجم‌ها ممنونیم.

</div>

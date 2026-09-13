# Iran Market AI — اتصال داده واقعی

این نسخه، Gateway را از حالت Demo به اتصال مستقیم به منابع واقعی ارتقا می‌دهد.

## منابع واقعی
- **بورس:** TSETMC — شاخص‌های منتخب از `cdn.tsetmc.com` با هدرهای لازم.
- **طلا ۱۸، دلار آزاد و نقره:** TGJU profile pages.
- تاریخچه‌ی دریافتی در SQLite محلی Gateway ذخیره می‌شود تا با هر polling، سری زمانی واقعی ساخته شود.

مرجع فنی endpointهای TSETMC در پروژه توسعه استفاده شده و endpoint شاخص منتخب و الزامات هدر/واسط بک‌اند در آن مستند شده‌اند.

## متغیرهای محیطی
```bash
ENABLE_REAL_DATA=1
ALLOW_DEMO_FALLBACK=1
IRAN_MARKET_DB=market_history.sqlite3
```

برای استفاده از Gateway اختصاصی به‌عنوان منبع جایگزین:
```bash
IRAN_MARKET_LIVE_URL=https://YOUR-GATEWAY
```

در این حالت Gateway باید `GET /market/candles/{symbol}?limit=N` را برگرداند.

## اجرا
```bash
pip install -r backend/requirements.txt
uvicorn backend.main:app --host 0.0.0.0 --port 8080
```

## نکته مهم درباره دسترسی
برخی endpointهای TSETMC از IP خارج ایران محدود می‌شوند؛ بنابراین برای حالت LIVE بهتر است این Gateway روی سرور/سیستمی با دسترسی شبکه مناسب داخل ایران اجرا شود. در صورت شکست منبع، برنامه فقط در صورت فعال بودن `ALLOW_DEMO_FALLBACK` به Demo برمی‌گردد.

## وضعیت
- TSETMC: LIVE connector
- TGJU: LIVE connector
- SQLite history: فعال
- RSI/EMA/Momentum/Volume: فعال
- BUY/HOLD/SELL: فعال
- News: هنوز provider واقعی متصل نشده و خبر ساختگی تولید نمی‌شود.

این نرم‌افزار ابزار تحلیل است و سیگنال‌ها توصیه قطعی سرمایه‌گذاری نیستند.


## نسخه 2.0 Production
- جمع‌آوری خودکار Snapshot داده‌های بازار هر ۶۰ ثانیه در Gateway فعال است.
- اپ اندروید بدون StrictMode و با درخواست‌های شبکه در پس‌زمینه کار می‌کند.
- Workflow رسمی GitHub Actions برای ساخت APK اضافه شده است.
- نسخه APK فعلاً باید در GitHub Actions ساخته شود؛ محیط فعلی ChatGPT Android SDK/Gradle ندارد.

### مسیر نهایی از گوشی
1. این ZIP را دانلود و روی GitHub به‌عنوان Repository آپلود کنید.
2. در تب Actions، workflow با نام Build Iran Market AI APK را اجرا کنید.
3. فایل APK از بخش Artifacts قابل دریافت خواهد بود.
4. Backend را روی Render/Railway اجرا کنید و آدرس HTTPS آن را داخل Settings اپ قرار دهید.

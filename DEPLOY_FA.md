# استقرار Gateway نسخه 1.8

این پروژه Gateway را به‌صورت Docker آماده کرده است. منابع واقعی:
- TSETMC برای شاخص بورس
- TGJU برای طلای ۱۸، دلار و نقره

## متغیرهای مهم
- `ENABLE_REAL_DATA=1`
- `ALLOW_DEMO_FALLBACK=0` برای اینکه قطع منبع واقعی به Demo تبدیل نشود.
- `IRAN_MARKET_DB=/tmp/market_history.sqlite3`

## بعد از Deploy
آدرس HTTPS سرویس را داخل اپ در Settings > Gateway قرار بده.
سپس `/health` باید `live: true` و provider=`real-composite` برگرداند.

## نکته
TGJU برای استفاده رسمی/تجاری API و وب‌سرویس ارائه می‌کند؛ در محیط تولید بهتر است دسترسی مجاز/کلید رسمی تهیه شود. این Gateway برای MVP از صفحات عمومی TGJU استفاده می‌کند و ممکن است با تغییر سایت نیاز به به‌روزرسانی parser داشته باشد.

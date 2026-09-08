# Astro App

Рабочий локальный MVP Telegram Mini App для самопознания: натальная карта, нумерология, психоматрица, прогнозы, совместимость, кэш интерпретаций, подписка и удаление данных.

## Запуск

```powershell
python app.py
```

Открыть `http://127.0.0.1:8000`.

## Что работает локально

- адаптивный тёмный интерфейс со звёздным небом;
- форма полного имени, даты, времени и города рождения;
- расчёт жизненного пути, числа души, имени и психоматрицы;
- планеты, дома, аспекты и SVG-подобное колесо карты;
- ежедневный прогноз и разделы «Главная», «Карта», «Числа», «Профиль»;
- демонстрационная активация подписки за Stars;
- кеширование AI-интерпретаций в `astro_data.json`;
- аналитические события;
- удаление пользовательских данных;
- endpoint `/api/geocode` с Nominatim;
- endpoint `/api/compatibility`.
- раздел «Таро»: полная колода 78 карт, схемы «Три карты», «Кельтский крест» и «Выбор»;
- персональные Арканы Личности, Судьбы и Дополнительный по дате рождения;
- «Карта дня», история раскладов и структурированный AI-prompt с учётом позиций, перевёрнутых карт и сочетаний.

### Tarot API

- `GET /api/tarot/topics` — темы, схемы раскладов и доступные дизайны колоды;
- `POST /api/tarot/spread` — `topicId`, `spreadType`, `question`, `userId`; возвращает карты, персональные Арканы и prompt;
- `GET /api/tarot/card-of-day?userId=...` — стабильная карта дня;
- `GET /api/tarot/history?userId=...` — история раскладов пользователя.

Карточка карты хранит `id`, `number`, `suit`, `arcana`, `element`, краткие и полные значения для прямого и перевёрнутого положения. В production эти поля следует перенести в таблицы `tarot_cards`, `tarot_spreads`, `tarot_spread_cards`, `personal_arcana` и `tarot_readings` PostgreSQL; текущий MVP сохраняет историю в `astro_data.json`.

## Запуск в Telegram

1. В `@BotFather` выполните `/newbot` и получите токен.
2. Скопируйте `.env.example` в `.env`, укажите `BOT_TOKEN` и публичный HTTPS `WEB_APP_URL`.
3. Для теста локального приложения используйте tunnel, например `cloudflared tunnel --url http://127.0.0.1:8000`.
4. Установите зависимости: `pip install -r requirements.txt`.
5. Запустите веб-приложение: `python app.py`.
6. Во втором окне запустите бота: `python bot.py`.
7. В Telegram откройте `/start` и нажмите кнопку Mini App.
8. Для проверки Stars используйте `/subscribe`. В production обработчик `successful_payment` должен записывать charge ID и подписку в PostgreSQL.

Быстрый запуск всего стека Windows:

```powershell
.\start-telegram.ps1
```

Скрипт запускает приложение, создаёт Cloudflare Quick Tunnel, показывает URL и запускает бота. В `@BotFather` укажите выведенный URL в Menu Button. Quick Tunnel создаёт новый URL при каждом запуске; для постоянного адреса нужен обычный Cloudflare Tunnel.

Telegram принимает Mini App только по HTTPS (кроме специальных локальных сценариев Telegram Desktop), поэтому публичный tunnel обязателен.

## Production-переход

`requirements.txt` содержит зависимости для FastAPI, aiogram 3, PostgreSQL/SQLAlchemy, Swiss Ephemeris, шифрования, OpenAI и APScheduler. В production необходимо:

1. вынести storage в PostgreSQL;
2. заменить локальную авторизацию на проверку Telegram `initData`;
3. включить `pyswisseph` и корректную timezone-конвертацию (текущий local fallback помечен `calculationMode=demo-fallback`);
4. подключить webhook aiogram и Telegram Stars;
5. хранить секреты в окружении;
6. использовать Fernet/AES для профилей и HTTPS;
7. запустить ежедневный worker уведомлений.

Переменные окружения: `BOT_TOKEN`, `AI_API_KEY`, `DATABASE_URL`, `ENCRYPTION_KEY`, `PORT`.

## Проверка текущего экземпляра

Бот `@astrologNm_bot` отвечает через Bot API, команды `/start` и `/subscribe` настроены, кнопка Menu Button настроена, а invoice Telegram Stars создаётся через `createInvoiceLink`. Локальная проверка Swiss Ephemeris возвращает `calculationMode=swiss-ephemeris`.

На текущем компьютере сеть Cloudflare Quick Tunnel нестабильна: Telegram URL может отдавать Cloudflare `1033`. Это ограничение внешнего туннеля, а не приложения. Для реального теста в Telegram используйте постоянный HTTPS-домен (Render/Railway/Vercel + backend или Cloudflare Named Tunnel) и замените `WEB_APP_URL` в `.env`. После передачи токена в чат его следует перевыпустить через `@BotFather`.

## Деплой на Railway

Проект уже содержит [Dockerfile](./Dockerfile), [railway.toml](./railway.toml) и production-запускатель [start_production.py](./start_production.py). Один Railway-сервис запускает API и polling бота, а Railway выдаёт HTTPS автоматически.

1. Создайте пустой GitHub-репозиторий и загрузите проект:

   ```powershell
   git init
   git add .
   git commit -m "Prepare Railway deployment"
   git branch -M main
   git remote add origin https://github.com/YOUR_LOGIN/astro-app.git
   git push -u origin main
   ```

2. В Railway нажмите **New Project → Deploy from GitHub Repo** и выберите репозиторий.
3. В **Variables** добавьте:

   ```text
   BOT_TOKEN=<новый токен из BotFather>
   WEB_APP_URL=https://<домен Railway>
   APP_API_URL=https://<домен Railway>
   MONTHLY_STARS=300
   PORT=${{PORT}}
   HOST=0.0.0.0
   ```

4. Скопируйте домен из **Settings → Networking → Generate Domain**.
5. Вставьте этот домен в `WEB_APP_URL` и `APP_API_URL`, после чего сделайте redeploy.
6. Проверьте `https://<домен>/api/health`.
7. Выполните `@BotFather → /setmenubutton` и укажите тот же HTTPS URL.

### Важно перед production

- Не загружайте `.env` и `astro_data.json` в GitHub.
- Токен, который уже был раскрыт в чате, перевыпустите через BotFather.
- Railway filesystem эфемерный: для реальных пользователей подключите Railway PostgreSQL и перенесите `astro_data.json` в базу.
- Для ежедневных уведомлений лучше вынести бота в отдельный Railway worker, чтобы web-сервис и polling масштабировались независимо.

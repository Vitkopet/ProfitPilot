# Одноразове підключення Google Drive

Код завантаження готовий, але авторизацію Google ще потрібно виконати.
Без неї сканер продовжує зберігати звіти в GitHub Artifacts і показує попередження
AWAITING_GOOGLE_AUTHORIZATION. Це не підтвердження запису на Google Drive.

Папка призначення: https://drive.google.com/drive/folders/1VIdtc5NasgXTuQGBGUPA8MbVWRUncNzx

## Авторизація на власному комп'ютері

1. У https://console.cloud.google.com/ створіть або виберіть проєкт для AICH.
2. Увімкніть Google Drive API. У Google Auth Platform налаштуйте OAuth consent screen
   для власного акаунта. Створіть OAuth client типу Desktop app та завантажте JSON.
3. Збережіть цей JSON локально як private_google/client_secret.json усередині
   завантаженого проєкту ProfitPilot. Ця папка виключена з git.
4. На своєму комп'ютері встановіть бібліотеку й запустіть авторизацію:

```bash
python -m pip install google-auth-oauthlib
python setup_google_drive.py
```

5. У браузері увійдіть у Google-акаунт власника папки та перегляньте запит доступу.
   Використовується scope `drive`: він надає широкий доступ до Google Drive.
   Сам скрипт записує лише до зазначеної папки, але це не технічне обмеження токена.
   Вузький `drive.file` не дає доступу до цієї вже створеної іншим додатком папки
   без окремого вибору через Google Picker. Доступ можна відкликати в Google Account.
6. Якщо OAuth app має статус Testing, refresh token для Drive зазвичай спливає
   через 7 днів. Для тривалого використання налаштуйте відповідний production status;
   дотримуйтеся вимог, які показує Google. Не ігноруйте несподіваних попереджень.
7. Відкрийте https://github.com/Vitkopet/ProfitPilot/settings/secrets/actions
   → New repository secret. Назва: GOOGLE_DRIVE_AUTH_JSON.
   Значення: вміст локального private_google/github_drive_auth.json.
   Не надсилайте його в чат і не додавайте до файлів репозиторію.
8. Actions → AICH Acceleration test → Run workflow. Після успішного завантаження
   у звіті drive_status.json має бути UPLOADED_AND_VERIFIED, а у папці — JSON-звіт.

## Що архівується

Кожний запуск створює acceleration-<GitHub run id>.json з усім latest.json:
час, пороги, перевірені пари, сигнали та помилки. Час перевірки є всередині файлу.
Повторний запуск того самого run оновлює його файл. Сирі свічки не архівуються.
Кожні 5 хвилин — до 288 файлів на добу. Видалення старих файлів на Drive не ввімкнене.
Звіти на GitHub залишаються резервною копією протягом 7 днів.

Помилка завантаження позначає запуск як невдалий; звіт сканера все одно надсилається
в Artifacts. Відсутність авторизації явно позначається попередженням.

Документація Google:
- https://developers.google.com/identity/protocols/oauth2/native-app
- https://developers.google.com/identity/protocols/oauth2
- https://developers.google.com/workspace/drive/api/guides/manage-uploads

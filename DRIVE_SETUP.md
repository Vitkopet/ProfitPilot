# Підключення Google Drive з iPhone — без Python

Код архівації вже готовий. Потрібно один раз дозволити доступ Google та додати
секрет у GitHub. Авторизація у ChatGPT не передається GitHub.
Поки цього немає, звіти зберігаються лише в GitHub Artifacts.

Папка: https://drive.google.com/drive/folders/1VIdtc5NasgXTuQGBGUPA8MbVWRUncNzx

## 1. Створити Google OAuth client

1. Відкрийте https://console.cloud.google.com/ у Safari. За потреби ввімкніть
   «Версія для комп'ютера». Увійдіть в акаунт власника папки.
2. Створіть або виберіть проєкт AICH Scanner. У APIs & Services → Library
   знайдіть Google Drive API й натисніть Enable.
3. У Google Auth Platform налаштуйте Branding, Audience та контактну адресу.
   Для особистого Gmail використовується External. Якщо застосунок у Testing,
   додайте свій Google-акаунт до Test users.
4. У Clients → Create client виберіть **Web application**, назвіть AICH Drive.
   У Authorized redirect URIs додайте точну адресу:
   https://developers.google.com/oauthplayground
5. Збережіть Client ID та Client secret приватно. Не публікуйте їх і не надсилайте в чат.

## 2. Авторизація через офіційну сторінку Google

1. Відкрийте https://developers.google.com/oauthplayground/ у Safari.
2. Натисніть шестерню. Обов'язково ввімкніть **Use your own OAuth credentials**.
   Введіть свій Client ID і Client secret із попереднього кроку.
   OAuth flow: Server-side; Access type: Offline; за наявності — Prompt: Consent.
3. У Step 1, Input your own scopes, введіть:
   https://www.googleapis.com/auth/drive
4. Натисніть Authorize APIs. Виберіть акаунт власника папки й перегляньте доступ.
   Це **широкий доступ до Drive**. Завантажувач у репозиторії використовує лише
   вказану папку, але сам токен технічно має ширші права.
   Не ігноруйте неочікувані попередження; перевірте, що це ваш застосунок.
5. У Step 2 натисніть **Exchange authorization code for tokens**.
   Збережіть **Refresh token** приватно. Access token для налаштування не потрібен.

Власні OAuth credentials обов'язкові: стандартні токени Playground автоматично
відкликаються через 24 години. У режимі Testing власний refresh token для Drive
зазвичай має строк 7 днів. Для тривалої роботи налаштуйте production status
відповідно до вимог Google перед остаточною авторизацією.
Не відкликайте доступ Playground після видачі токена: це може вимкнути цей токен.

## 3. Додати секрет у GitHub

1. Відкрийте https://github.com/Vitkopet/ProfitPilot/settings/secrets/actions
2. New repository secret → Name: **GOOGLE_DRIVE_AUTH_JSON**.
3. У Secret вставте JSON нижче, замінивши три значення власними.
   Лапки й коми залиште. Не використовуйте сторонні онлайн-редактори для токенів.

```json
{
  "client_id": "ВАШ_CLIENT_ID",
  "client_secret": "ВАШ_CLIENT_SECRET",
  "refresh_token": "ВАШ_REFRESH_TOKEN"
}
```

4. Натисніть Add secret. Не додавайте цей JSON до файлів репозиторію й не надсилайте в чат.
5. Дочекайтеся наступного запуску за розкладом або запустіть Actions →
   AICH Acceleration test → Run workflow.
6. Перевірте крок Archive report to Google Drive і файл у папці.
   У drive_status.json успішний результат — **UPLOADED_AND_VERIFIED**.
   Зелений статус без цього результату ще не підтверджує запис на Drive:
   відсутній секрет створює попередження AWAITING_GOOGLE_AUTHORIZATION.

## Що зберігається

Кожен запуск створює acceleration-<GitHub run id>.json: час, пороги, перевірені пари,
кандидати та помилки. Повторний запуск того самого run оновлює його файл.
Сирі свічки не архівуються. До 288 файлів на добу; автоматичного видалення на Drive
немає. GitHub Artifacts залишаються резервною копією на 7 днів.
У разі помилки Drive запуск позначається невдалим, а звіт залишається в Artifacts.

## Альтернатива на комп'ютері

За бажанням можна створити окремий OAuth client типу Desktop app,
зберегти його JSON як private_google/client_secret.json, встановити
google-auth-oauthlib і запустити setup_google_drive.py локально.
Для способу з iPhone це не потрібно.

Офіційні джерела:
- https://developers.google.com/oauthplayground/
- https://developers.google.com/identity/protocols/oauth2
- https://developers.google.com/workspace/drive/api/guides/manage-uploads

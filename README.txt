МОЙ ДНЕВНИК (вариант с библиотекой netschoolpy внутри приложения). Android, без Termux.

Как это устроено: внутри приложения работает настоящий Python (Chaquopy) и библиотека netschoolpy.
Интерфейс (app/src/main/assets/index.html) вызывает её через мост. Пароль хранится в зашифрованном
хранилище Android, при запуске вход выполняется автоматически, при истёкшей сессии: повторно.

СБОРКА (в облаке GitHub, один раз). Создайте НОВЫЙ репозиторий и загрузите файлы с этими путями:
  settings.gradle.kts
  build.gradle.kts
  gradle.properties
  .gitignore
  .github/workflows/build.yml
  app/build.gradle.kts
  app/src/main/AndroidManifest.xml
  app/src/main/java/app/mydiary/MainActivity.kt
  app/src/main/python/nsbridge.py
  app/src/main/assets/index.html
Удобнее всего с компьютера: распакуйте архив и перетащите содержимое папки на страницу репозитория
(Add file -> Upload files). С телефона: Add file -> Create new file, в поле имени вписывайте путь
целиком (папки создаются сами) и вставляйте содержимое.

Дальше: вкладка Actions -> Build APK (Python) -> Run workflow (или любой коммит в main).
Сборка идёт 10-15 минут. Готовый app-debug.apk будет в разделе Releases.

ЕСЛИ СБОРКА УПАЛА: откройте красный шаг и пришлите последние 30 строк. Самое вероятное место:
установка зависимостей netschoolpy под Android (шаг, где Chaquopy выполняет pip).

Лицензия: netschoolpy распространяется под GPLv3. Для личного использования это не мешает; если
будете раздавать APK другим, приложение тоже нужно публиковать под GPLv3 с исходным кодом.
Используйте только свой аккаунт и соблюдайте правила школы.

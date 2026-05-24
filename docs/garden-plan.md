# План приложения для полива цветов

## Стек

- Django 6
- Django Templates
- Небольшой JavaScript без SPA
- SQLite на этапе MVP
- Poetry
- DRF можно подключить позже, если понадобится отдельный API

## Цель MVP

Сделать мобильную веб-страницу, где пользователь после входа видит свои цветы и уровень оставшейся влаги. По двойному тапу на цветок пользователь отмечает полив, после чего уровень влаги становится 100%.

Приложение должно сразу учитывать нескольких пользователей: каждый пользователь видит и меняет только свои цветы.

## Текущая структура проекта

Проект уже создан как `skybreaker` с Django-проектом `config` и приложением `garden`.

Актуальная целевая структура:

```text
skybreaker/
  config/
    settings.py
    urls.py
    asgi.py
    wsgi.py

  garden/
    migrations/
    __init__.py
    admin.py
    apps.py
    forms.py
    models.py
    urls.py
    views.py

  users/
    migrations/
    __init__.py
    admin.py
    apps.py
    forms.py
    models.py
    urls.py
    views.py

  templates/
    base.html
    garden/
      plant_list.html
      plant_form.html
      plant_confirm_delete.html
      plant_detail.html
    users/
      login.html
      signup.html

  static/
    garden/
      css/
        garden.css
      js/
        garden.js

  media/
    plant_photos/

  docs/
    garden-plan.md

  manage.py
  pyproject.toml
```

Важно: приложение для цветов называется `garden`, не `plants`. В коде, URL names и шаблонах лучше использовать единый нейминг `garden`/`plant`.

## Приложения

### `garden`

Доменное приложение для цветов:

- модели цветов и фотоистории;
- CRUD цветов;
- расчет влаги;
- endpoint для полива;
- шаблоны списка, формы и деталей цветка.

### `users`

Приложение для авторизации и пользовательской модели:

- кастомная модель пользователя;
- регистрация;
- вход;
- выход;
- пользовательские формы, если стандартных Django forms будет недостаточно.

Кастомную модель пользователя нужно добавить до первых реальных миграций, чтобы не мигрировать позже с `auth.User` на собственную модель.

## Настройки Django

В `config/settings.py` нужно добавить приложение `users` до `garden`:

```python
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "users.apps.UsersConfig",
    "garden.apps.GardenConfig",
]
```

Также нужно сразу указать кастомную модель пользователя:

```python
AUTH_USER_MODEL = "users.User"
```

Для логина/логаута:

```python
LOGIN_URL = "users:login"
LOGIN_REDIRECT_URL = "garden:plant_list"
LOGOUT_REDIRECT_URL = "users:login"
```

Для загрузки фото позже понадобится media-настройка:

```python
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"
```

## Модель пользователя

Для MVP достаточно кастомной модели на базе `AbstractUser` без дополнительных обязательных полей.

```python
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    pass
```

Почему так:

- сохраняем совместимость со стандартной Django auth;
- можно использовать username/password без усложнения;
- позже можно добавить email-login, аватар, настройки уведомлений или timezone;
- проект сразу использует `settings.AUTH_USER_MODEL`, а не жесткую ссылку на `auth.User`.

В админке пользователя можно зарегистрировать через `UserAdmin`:

```python
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


admin.site.register(User, UserAdmin)
```

## Модель данных

Итоговый набор моделей:

- `users.User` - кастомный пользователь на базе `AbstractUser`.
- `garden.Plant` - цветок пользователя.
- `garden.PlantPhoto` - история фотографий цветка для будущей карусели на детальной странице.

`moisture_percent` не хранится в базе, потому что это вычисляемое свойство `Plant`.

### `Plant`

Основная модель цветка:

```python
from django.conf import settings
from django.db import models
from django.utils import timezone


class Plant(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="plants",
    )
    name = models.CharField(max_length=100)
    watering_interval_days = models.PositiveIntegerField()
    last_watered_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def moisture_percent(self):
        elapsed = timezone.now() - self.last_watered_at
        elapsed_days = elapsed.total_seconds() / 86400
        percent = 100 - elapsed_days / self.watering_interval_days * 100
        return max(0, min(100, round(percent)))
```

Поля:

- `user` - владелец цветка.
- `name` - название цветка, например `Монстера`.
- `watering_interval_days` - как часто нужно поливать, например `3`, `7`, `14`.
- `last_watered_at` - когда цветок последний раз поливали.
- `created_at` - когда цветок добавлен.

Все запросы к `Plant` должны фильтроваться по `request.user`.

### `PlantPhoto`

Будущая фича: на детальной карточке цветка нужно показывать карусель с историей фотографий, которые были сделаны ранее.

Для этого стоит сразу заложить отдельную модель:

```python
class PlantPhoto(models.Model):
    plant = models.ForeignKey(
        Plant,
        on_delete=models.CASCADE,
        related_name="photos",
    )
    image = models.ImageField(upload_to="plant_photos/%Y/%m/")
    taken_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-taken_at", "-created_at"]
```

Поля:

- `plant` - цветок, к которому относится фото.
- `image` - файл изображения.
- `taken_at` - когда фото было сделано.
- `created_at` - когда фото добавлено в приложение.

Для `ImageField` понадобится зависимость `Pillow`.

На первом шаге фото можно не загружать через UI, но модель и место в детальной карточке стоит учитывать в архитектуре.

### DBML

Доменные таблицы приложения в нотации DBML:

```dbml
Table users_user {
  id bigint [pk, increment]

  password varchar(128) [not null]
  last_login datetime
  is_superuser boolean [not null, default: false]

  username varchar(150) [not null, unique]
  first_name varchar(150) [not null, default: ""]
  last_name varchar(150) [not null, default: ""]
  email varchar(254) [not null, default: ""]

  is_staff boolean [not null, default: false]
  is_active boolean [not null, default: true]
  date_joined datetime [not null]

  indexes {
    username [unique]
  }
}

Table garden_plant {
  id bigint [pk, increment]

  user_id bigint [not null, ref: > users_user.id]

  name varchar(100) [not null]
  watering_interval_days int [not null]
  last_watered_at datetime [not null]
  created_at datetime [not null]

  indexes {
    user_id
  }
}

Table garden_plant_photo {
  id bigint [pk, increment]

  plant_id bigint [not null, ref: > garden_plant.id]

  image varchar(100) [not null]
  taken_at datetime [not null]
  created_at datetime [not null]

  indexes {
    plant_id
    taken_at
  }
}
```

Стандартные M2M-таблицы Django auth для `AbstractUser`:

```dbml
Table auth_group {
  id int [pk, increment]
  name varchar(150) [not null, unique]
}

Table auth_permission {
  id int [pk, increment]
  name varchar(255) [not null]
  content_type_id int [not null]
  codename varchar(100) [not null]
}

Table users_user_groups {
  id bigint [pk, increment]
  user_id bigint [not null, ref: > users_user.id]
  group_id int [not null, ref: > auth_group.id]

  indexes {
    (user_id, group_id) [unique]
  }
}

Table users_user_user_permissions {
  id bigint [pk, increment]
  user_id bigint [not null, ref: > users_user.id]
  permission_id int [not null, ref: > auth_permission.id]

  indexes {
    (user_id, permission_id) [unique]
  }
}
```

## Расчет уровня влаги

Уровень влаги лучше вычислять, а не хранить в базе.

Логика:

```text
если цветок нужно поливать раз в 7 дней,
и последний полив был 3.5 дня назад,
значит уровень влаги примерно 50%.
```

Формула:

```text
moisture_percent = 100 - elapsed_days / watering_interval_days * 100
```

С ограничениями:

```text
минимум: 0%
максимум: 100%
```

В шаблоне:

```django
{{ plant.moisture_percent }}
```

## Авторизация

MVP сразу делается с пользователями.

Обязательные правила:

- анонимный пользователь не видит список цветов;
- все страницы `garden` защищены через `LoginRequiredMixin` или `@login_required`;
- создание цветка автоматически проставляет `plant.user = request.user`;
- список показывает только `Plant.objects.filter(user=request.user)`;
- детали, редактирование, удаление и полив должны искать цветок только среди цветов текущего пользователя;
- нельзя отдавать 403/404 детали чужого цветка через обычный `Plant.objects.get(pk=...)` без фильтра по пользователю.

Пример безопасного получения цветка:

```python
plant = get_object_or_404(Plant, pk=pk, user=request.user)
```

## Основные страницы

### Регистрация

URL:

```text
/users/signup/
```

Форма:

- username;
- password;
- password confirmation.

После регистрации можно сразу логинить пользователя и отправлять на главную страницу.

### Вход

URL:

```text
/users/login/
```

Использует стандартную Django auth-логику или тонкую обертку над `LoginView`.

### Выход

URL:

```text
/users/logout/
```

Лучше делать через POST-форму, чтобы выход не был GET-действием.

### Главная страница

URL:

```text
/
```

Показывает сетку цветов текущего пользователя.

Каждая карточка:

- круглая иконка;
- уровень воды внутри;
- название цветка.

Действия:

- одиночный тап: открыть страницу цветка;
- двойной тап: отметить полив.

Если у пользователя нет цветов, показываем пустое состояние и ссылку `Добавить цветок`.

### Добавление цветка

URL:

```text
/plants/new/
```

Форма:

- название;
- интервал полива в днях.

После создания:

```text
user = request.user
last_watered_at = now()
```

То есть новый цветок считается только что политым.

### Детальная страница цветка

URL:

```text
/plants/<id>/
```

Показывает:

- название;
- текущий уровень влаги;
- интервал полива;
- дату последнего полива;
- кнопку `Полил`;
- ссылку `Редактировать`;
- карусель предыдущих фотографий цветка.

На этой странице лучше иметь явную кнопку `Полил`, чтобы двойной тап не был единственным способом отметить полив.

### Карусель фото на детальной странице

Карусель должна показывать историю фото цветка из `plant.photos.all`.

Минимальная версия без библиотек:

```html
<section class="plant-photo-history">
  <h2>История фото</h2>

  {% if plant.photos.exists %}
    <div class="photo-carousel" data-photo-carousel>
      {% for photo in plant.photos.all %}
        <figure class="photo-slide">
          <img src="{{ photo.image.url }}" alt="{{ plant.name }}">
          <figcaption>{{ photo.taken_at|date:"d.m.Y" }}</figcaption>
        </figure>
      {% endfor %}
    </div>
  {% else %}
    <p>Фото пока нет.</p>
  {% endif %}
</section>
```

Для мобильного MVP достаточно горизонтального scroll-snap:

```css
.photo-carousel {
  display: flex;
  gap: 12px;
  overflow-x: auto;
  scroll-snap-type: x mandatory;
}

.photo-slide {
  flex: 0 0 85%;
  scroll-snap-align: center;
}

.photo-slide img {
  display: block;
  width: 100%;
  border-radius: 16px;
}
```

Позже можно добавить:

- форму загрузки нового фото;
- подписи/заметки к фото;
- сравнение прогресса растения по датам;
- удаление фото.

## Django views

Можно начать с class-based views.

Минимальный набор для `garden`:

```text
PlantListView
PlantDetailView
PlantCreateView
PlantUpdateView
PlantDeleteView
water_plant
```

Минимальный набор для `users`:

```text
SignUpView
LoginView
LogoutView
```

`water_plant` будет отдельным endpoint:

```text
POST /plants/<id>/water/
```

Он делает:

```python
plant = get_object_or_404(Plant, pk=pk, user=request.user)
plant.last_watered_at = timezone.now()
plant.save(update_fields=["last_watered_at"])
```

И возвращает JSON:

```json
{
  "ok": true,
  "moisture_percent": 100
}
```

Так как у нас не SPA, но JS все равно нужен для двойного тапа, удобно сделать именно маленький JSON endpoint.

## URL-структура

`config/urls.py`:

```python
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("users/", include("users.urls")),
    path("", include("garden.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

`garden/urls.py`:

```python
from django.urls import path

from . import views

app_name = "garden"

urlpatterns = [
    path("", views.PlantListView.as_view(), name="plant_list"),
    path("plants/new/", views.PlantCreateView.as_view(), name="plant_create"),
    path("plants/<int:pk>/", views.PlantDetailView.as_view(), name="plant_detail"),
    path("plants/<int:pk>/edit/", views.PlantUpdateView.as_view(), name="plant_update"),
    path("plants/<int:pk>/delete/", views.PlantDeleteView.as_view(), name="plant_delete"),
    path("plants/<int:pk>/water/", views.water_plant, name="plant_water"),
]
```

`users/urls.py`:

```python
from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = "users"

urlpatterns = [
    path("signup/", views.SignUpView.as_view(), name="signup"),
    path("login/", auth_views.LoginView.as_view(template_name="users/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
]
```

## Фронтенд на Django templates

Главный шаблон:

```text
templates/base.html
```

В нем:

- viewport для мобильной верстки;
- подключение CSS;
- подключение JS;
- навигация с состоянием пользователя;
- общая оболочка страницы;
- CSRF meta-тег для JS-запросов.

Важный meta-тег:

```html
<meta name="viewport" content="width=device-width, initial-scale=1">
```

CSRF-токен:

```html
<meta name="csrf-token" content="{{ csrf_token }}">
```

В навигации:

```django
{% if request.user.is_authenticated %}
  <span>{{ request.user.username }}</span>
  <form method="post" action="{% url 'users:logout' %}">
    {% csrf_token %}
    <button type="submit">Выйти</button>
  </form>
{% else %}
  <a href="{% url 'users:login' %}">Войти</a>
  <a href="{% url 'users:signup' %}">Регистрация</a>
{% endif %}
```

## Визуализация уровня воды

Карточка цветка может быть примерно такой:

```html
<a class="plant-card" href="/plants/1/" data-water-url="/plants/1/water/">
  <div class="plant-icon">
    <div class="plant-water" style="height: 65%"></div>
  </div>
  <div class="plant-name">Монстера</div>
</a>
```

Идея CSS:

```css
.plant-icon {
  position: relative;
  width: 96px;
  height: 96px;
  border: 4px solid #ddd;
  border-radius: 50%;
  overflow: hidden;
}

.plant-water {
  position: absolute;
  left: 0;
  bottom: 0;
  width: 100%;
  background: #4aa3ff;
  transition: height 0.3s ease;
}
```

Для штриховки:

```css
.plant-water {
  background: repeating-linear-gradient(
    135deg,
    #4aa3ff 0 6px,
    transparent 6px 14px
  );
}
```

## JS для одиночного и двойного тапа

Логика:

```text
одиночный тап: перейти на страницу цветка
двойной тап: отменить переход и отправить POST-запрос "полил"
```

Общая идея:

```js
let tapTimer = null;
const doubleTapDelay = 300;

card.addEventListener("pointerup", (event) => {
  event.preventDefault();

  if (tapTimer) {
    clearTimeout(tapTimer);
    tapTimer = null;
    waterPlant(card);
    return;
  }

  tapTimer = setTimeout(() => {
    tapTimer = null;
    window.location.href = card.href;
  }, doubleTapDelay);
});
```

POST-запрос должен отправлять CSRF-токен:

```js
fetch(waterUrl, {
  method: "POST",
  headers: {
    "X-CSRFToken": csrfToken,
  },
});
```

Если сервер вернул 403 или редирект на логин, JS должен не ломать страницу. Для MVP достаточно оставить стандартное поведение и обновлять UI только при `response.ok`.

## Django admin

В админке нужно зарегистрировать:

- `users.User`;
- `garden.Plant`;
- `garden.PlantPhoto`.

Для `Plant` удобно показывать:

- `name`;
- `user`;
- `watering_interval_days`;
- `last_watered_at`;
- `created_at`.

Для `PlantPhoto` удобно показывать:

- `plant`;
- `taken_at`;
- `created_at`.

## Что не делать в первом MVP

Пока не добавлять:

- DRF для всего приложения;
- React/Vue;
- push-уведомления;
- историю всех поливов отдельной таблицей;
- сложные графики;
- категории;
- комнату/локацию;
- PWA service worker;
- сложную обработку изображений;
- распознавание растений по фото.

Фотоисторию не считаем частью самого первого CRUD, но учитываем ее в модели и детальной странице как ближайшую будущую фичу.

## Порядок разработки

1. Создать приложение `users`.
2. Добавить кастомную модель `users.User` на базе `AbstractUser`.
3. Указать `AUTH_USER_MODEL = "users.User"` до первых миграций.
4. Добавить `users` в `INSTALLED_APPS` до `garden`.
5. Создать модели `Plant` и, если сразу нужна заготовка под фотоисторию, `PlantPhoto`.
6. Добавить метод расчета `moisture_percent`.
7. Настроить `MEDIA_URL` и `MEDIA_ROOT`, если добавляется `PlantPhoto.image`.
8. Добавить зависимость `Pillow`, если используется `ImageField`.
9. Сделать миграции.
10. Зарегистрировать `User`, `Plant` и `PlantPhoto` в Django admin.
11. Настроить `users.urls`, регистрацию, вход и выход.
12. Настроить `garden.urls` и подключить его в `config.urls`.
13. Сделать главную страницу со списком цветов текущего пользователя.
14. Сделать CSS-круг с уровнем воды.
15. Сделать форму добавления цветка с автоматическим `user = request.user`.
16. Сделать страницу деталей цветка.
17. Добавить на детальную страницу блок карусели фотоистории.
18. Сделать endpoint `POST /plants/<id>/water/` с проверкой владельца.
19. Добавить JS для двойного тапа.
20. Добавить кнопку `Полил` на детальной странице.
21. Проверить, что один пользователь не видит цветы другого.
22. Проверить в мобильном браузере.
23. Потом думать про загрузку новых фото через UI, уведомления и PWA.

## Рекомендуемый MVP

Самая практичная первая версия:

- кастомный `users.User` на базе `AbstractUser`;
- Django auth для регистрации, входа и выхода;
- Django templates для страниц;
- `garden.Plant` с привязкой к пользователю;
- CSS для отображения влаги;
- маленький JS для double tap;
- SQLite как база;
- Django admin для ручного контроля;
- заготовка под `PlantPhoto` и карусель на детальной странице;
- без DRF на первом этапе.

DRF можно подключить позже, если появится отдельный фронтенд, мобильное приложение или более сложный API.

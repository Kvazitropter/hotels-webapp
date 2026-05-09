# API Документация

Base URL: `/api`

Аутентификация: http header `Authorization: Bearer <access_token>`

---

## Содержание

- [Аутентификация](#аутентификация)
- [Профиль](#профиль)
- [Пользователи](#пользователи)
- [Гости](#гости)
- [Модераторы](#модераторы)
- [Администраторы](#Только администраторы)
- [Отели](#отели)
- [Номера](#номера)
- [Бронирования](#бронирования)
- [Мои бронирования](#мои-бронирования)
- [Мои отзывы](#мои-отзывы)

---

## Аутентификация

### Регистрация

```
POST /api/auth/register/
```

Доступ: Публичный

**Тело запроса:**
```json
{
  "email": "user@example.com",
  "first_name": "Иван",
  "last_name": "Иванов",
  "phone_number": "+79123456789",
  "password": "GoodPassword432+",
  "password_confirm": "GoodPassword432+"
}
```

**Ответ `201`:**
```json
{
  "user": {
    "email": "user@example.com",
    "phone_number": "+79123456789",
    "first_name": "Иван",
    "last_name": "Иванов",
    "full_name": "Иванов Иван",
    "short_name": "Иванов И.",
    "role": "GUEST"
  },
  "access": "<access_token>",
  "refresh": "<refresh_token>"
}
```

---

### Вход

```
POST /api/auth/login/
```

Доступ: Публичный

**Тело запроса:**
```json
{
  "email": "user@example.com",
  "password": "GoodPassword432+"
}
```

**Ответ `200`:**
```json
{
  "access": "<access_token>",
  "refresh": "<refresh_token>"
}
```

---

### Обновление access-токена

```
POST /api/auth/token/refresh/
```

Доступ: Публичный

**Тело запроса:**
```json
{
  "refresh": "<refresh_token>"
}
```

**Ответ `200`:**
```json
{
  "access": "<access_token>"
}
```

---

### Выход

```
POST /api/auth/logout/
```

Доступ: Авторизованный пользователь

**Тело запроса:**
```json
{
  "refresh": "<refresh_token>"
}
```

**Ответ `204`:** нет тела

---

### Запрос сброса пароля

```
POST /api/auth/password-reset/
```

Доступ: Публичный

**Тело запроса:**
```json
{
  "email": "user@example.com"
}
```

**Ответ `200`:**
```json
{
  "detail": "Если такой email зарегистрирован, письмо отправлено."
}
```

---

### Подтверждение сброса пароля

```
POST /api/auth/password-reset/confirm/
```

Доступ: Публичный

**Тело запроса:**
```json
{
  "uid": "<uid>",
  "token": "<token>",
  "new_password": "NewGoodPassword432+",
  "new_password_confirm": "NewGoodPassword432+"
}
```

**Ответ `200`:**
```json
{
  "detail": "Пароль успешно изменён."
}
```

---

## Профиль (Me)

### Получить профиль

```
GET /api/me
```

Доступ: Авторизованный пользователь

**Ответ `200`:**
```json
{
  "email": "user@example.com",
  "phone_number": "+79123456789",
  "first_name": "Иван",
  "middle_name": null,
  "last_name": "Иванов",
  "full_name": "Иванов Иван",
  "short_name": "Иванов И.",
  "date_of_birth": "2000-01-11",
  "last_login": "2025-01-01T00:00:00Z",
  "date_joined": "2024-01-01T00:00:00Z",
  "role": "GUEST"
}
```

---

### Обновить профиль

```
PATCH /api/me
```

Доступ: Только гость

Email и телефон через этот эндпоинт не меняются (только через `/me/contact-change/`).

**Тело запроса:**
```json
{
  "first_name": "Иван",
  "middle_name": "Петрович",
  "last_name": "Иванов",
  "date_of_birth": "2001-01-01"
}
```

**Ответ `200`:** обновлённый объект пользователя

---

### Деактивировать аккаунт

```
DELETE /api/me
```

Доступ: Только гость

**Ответ `204`:** нет тела

---

### Запросить смену email или телефона

```
PATCH /api/me/contact-change/
```

Доступ: Только гость

Отправить можно либо `email`, либо `phone_number` (не оба сразу).

**Тело запроса (смена email):**
```json
{
  "email": "newemail@example.com"
}
```

**Тело запроса (смена телефона):**
```json
{
  "phone_number": "+79987654321"
}
```

**Ответ `200` (смена email):**
```json
{
  "detail": "Письмо с подтверждением отправлено на newemail@example.com"
}
```

**Ответ `200` (смена телефона):**
```json
{
  "detail": "Письмо с подтверждением отправлено на email@example.com"
}
```

---

### Подтвердить смену контактных данных

```
POST /api/me/contact-change/confirm/
```

Доступ: Публичный (ссылка из письма)

**Тело запроса:**
```json
{
  "uid": "<uid>",
  "token": "<token>"
}
```

**Ответ `200`:**
```json
{
  "detail": "Данные успешно обновлены"
}
```

---

## Пользователи

### Назначить роль пользователю

```
POST /api/users/{id}/assign-role/
```

Доступ: Только администратор

**Тело запроса:**
```json
{
  "role": "MODERATOR"
}
```

**Ответ `200`:**
```json
{
  "detail": "Роль \"MODERATOR\" успешно добавлена пользователю user@example.com."
}
```

---

### Снять роль с пользователя

```
DELETE /api/users/{id}/remove-role/
```

Доступ: Только администратор

**Тело запроса:**
```json
{
  "role": "MODERATOR"
}
```

**Ответ `204`:** нет тела

---

### Деактивировать пользователя

```
POST /api/users/{id}/deactivate/
```

Доступ: Только администратор

**Ответ `200`:**
```json
{
  "detail": "Аккаунт успешно деактивирован"
}
```

---

### Активировать пользователя

```
POST /api/users/{id}/activate/
```

Доступ: Только администратор

**Ответ `200`:**
```json
{
  "detail": "Аккаунт успешно активирован"
}
```

---

## Гости

### Список гостей

```
GET /api/guests/
```

Доступ: Модератор или администратор

**Параметры фильтрации:**

| Параметр | Тип | Описание |
|---|---|---|
| `is_active` | boolean | Активен ли аккаунт |
| `guest__bookings__status` | string | Статус бронирования (`A`, `M`, `CA`, `CL`) |
| `search` | string | Поиск по email, телефону, фамилии |

**Ответ `200`:**
```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "email": "guest@example.com",
      "phone_number": "+79123456789",
      "first_name": "Иван",
      "last_name": "Иванов",
      "full_name": "Иванов Иван",
      "short_name": "Иванов И.",
      "role": "GUEST"
    }
  ]
}
```

---

### Детали гостя

```
GET /api/guests/{id}/
```

Доступ: Модератор или администратор

---

## Модераторы

### Список модераторов

```
GET /api/moderators/
```

Доступ: Модератор или администратор

**Параметры фильтрации:**

| Параметр | Тип | Описание |
|---|---|---|
| `is_active` | boolean | Активен ли аккаунт |
| `search` | string | Поиск по email, телефону, фамилии |

---

### Детали модератора

```
GET /api/moderators/{id}/
```

Доступ: Модератор или администратор

---

## Администраторы

### Список Только администраторов

```
GET /api/admins/
```

Доступ: Только администратор

**Параметры фильтрации:**

| Параметр | Тип | Описание |
|---|---|---|
| `is_active` | boolean | Активен ли аккаунт |
| `search` | string | Поиск по email, телефону, фамилии |

---

### Детали Только администратора

```
GET /api/admins/{id}/
```

Доступ: Только администратор

---

## Отели

### Список отелей

```
GET /api/hotels/
```

Доступ: Публичный. Возвращает только активные отели (`is_active=true`).

**Параметры фильтрации:**

| Параметр | Тип | Описание |
|---|---|---|
| `search` | string | Поиск по стране, городу, названию |

**Ответ `200`:**
```json
{
  "count": 2,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "name": "Гранд Отель",
      "email": "hotel@example.com",
      "phone_number": "+79123456789",
      "check_in_time": "14:00:00",
      "check_out_time": "12:00:00",
      "country": "Россия",
      "city": "Москва",
      "address": "ул. Тверская, д. 1",
      "floor_count": 10
    }
  ]
}
```

---

### Детали отеля

```
GET /api/hotels/{id}/
```

Доступ: Публичный

**Ответ `404`:**
```json
{
  "detail": "No Hotel matches the given query."
}
```

---

## Номера

### Список номеров отеля

```
GET /api/hotels/{hotel_id}/rooms/
```

Доступ: Публичный

**Параметры фильтрации:**

| Параметр | Тип | Описание |
|---|---|---|
| `floor` | integer | Номер этажа |
| `bed_count` | integer | Количество спальных мест |
| `is_pets_allowed` | boolean | Можно с животными |
| `is_smoking_allowed` | boolean | Можно курить |
| `min_capacity` | integer | Минимальная вместимость |
| `is_premium` | boolean | Премиум-категория |
| `is_standard` | boolean | Стандартная категория |
| `check_in` | date (`YYYY-MM-DD`) | Дата заезда (вместе с `check_out`) |
| `check_out` | date (`YYYY-MM-DD`) | Дата выезда (вместе с `check_in`) |
| `search` | string | Поиск по названию типа номера |

Фильтры `check_in` и `check_out` передаются только вместе — вернёт только свободные номера на указанный период.

**Пример запроса с фильтрами:**
```
GET /api/hotels/1/rooms/?check_in=2025-06-01&check_out=2025-06-07&is_pets_allowed=true&min_capacity=2
```

**Ответ `200`:**
```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 5,
      "category": "Первая категория (стандарт)",
      "room_type_name": "Стандартный Двухместный",
      "room_type_description": "Уютный номер с видом на город",
      "is_premium": false,
      "is_standard": true,
      "standard_capacity": 2,
      "cover_photo": {
        "id": 1,
        "photo": "http://localhost:8000/media/hotels/1/rooms/5/photo.jpg",
        "order_number": 1
      },
      "price_per_night": "3500.00"
    }
  ]
}
```

**Ответ `400` (только одна дата):**
```json
{
  "detail": "Необходимо указать обе даты: заселения и выселения"
}
```

**Ответ `404` (отель не найден):**
```json
{
  "detail": "Отель с ID \"99\" не найден"
}
```

---

### Детали номера

```
GET /api/hotels/{hotel_id}/rooms/{id}/
```

Доступ: Публичный

**Ответ `200`:**
```json
{
  "id": 5,
  "room_number": "205A",
  "floor": 2,
  "category": "Первая категория (стандарт)",
  "is_premium": false,
  "is_standard": true,
  "size": 25,
  "standard_capacity": 2,
  "bed_count": 2,
  "is_pets_allowed": true,
  "is_smoking_allowed": false,
  "price_per_night": "3500.00",
  "extra_pay_per_person": "500.00",
  "room_type": {
    "id": 2,
    "name": "Стандартный Двухместный",
    "description": "Уютный номер с видом на город",
    "size": 25,
    "standard_capacity": 2,
    "bedroom_count": 1,
    "living_room_count": 0,
    "bathroom_count": 1,
    "bathroom_type": "F",
    "has_kitchen": false,
    "has_balcony": true
  },
  "photos": [
    {
      "id": 1,
      "photo": "http://localhost:8000/media/hotels/1/rooms/5/photo1.jpg",
      "order_number": 1
    },
    {
      "id": 2,
      "photo": "http://localhost:8000/media/hotels/1/rooms/5/photo2.jpg",
      "order_number": 2
    }
  ]
}
```

---

## Бронирования

### Создать бронирование

```
POST /api/bookings/
```

Доступ: Только гость

**Тело запроса:**
```json
{
  "room_id": 5,
  "check_in_date": "2025-06-01",
  "check_out_date": "2025-06-07",
  "adults_count": 2,
  "children_count": 1,
  "pets_count": 0,
  "type": "G"
}
```

Тип бронирования: `G` — гарантированное (с предоплатой), `N` — негарантированное.

**Ответ `201`:**
```json
{
  "id": 42,
  "hotel_name": "Гранд Отель",
  "room_number": "205A",
  "room_type_name": "Стандартный Двухместный",
  "check_in_date": "2025-06-01",
  "check_out_date": "2025-06-07",
  "days_count": 6,
  "adults_count": 2,
  "children_count": 1,
  "pets_count": 0,
  "status": "A",
  "status_display": "Активно",
  "type": "G",
  "created_at": "2025-05-01T12:00:00Z"
}
```

**Ответ `400` (номер занят или другие ошибки валидации модели):**
```json
{
  "detail": "Номер уже забронирован на выбранные даты"
}
```

---

## Мои бронирования

### Список моих бронирований

```
GET /api/me/bookings/
```

Доступ: Только гость

**Параметры фильтрации:**

| Параметр | Тип | Описание |
|---|---|---|
| `status` | string | Статус: `A` (активно), `M` (перенесено), `CA` (отменено), `CL` (завершено) |
| `hotel` | integer | ID отеля |
| `check_in_from` | date | Дата заезда от |
| `check_in_to` | date | Дата заезда до |
| `ordering` | string | Сортировка: `check_in_date`, `-check_in_date`, `created_at`, `-created_at` |

**Пример:**
```
GET /api/me/bookings/?status=A&ordering=-check_in_date
```

**Ответ `200`:**
```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 42,
      "hotel_name": "Гранд Отель",
      "room_number": "205A",
      "room_type_name": "Стандартный Двухместный",
      "check_in_date": "2025-06-01",
      "check_out_date": "2025-06-07",
      "days_count": 6,
      "adults_count": 2,
      "children_count": 1,
      "pets_count": 0,
      "status": "A",
      "status_display": "Активно",
      "type": "G",
      "created_at": "2025-05-01T12:00:00Z"
    }
  ]
}
```

---

### Детали бронирования

```
GET /api/me/bookings/{id}/
```

Доступ: Только гость

**Ответ `200`:**
```json
{
  "id": 42,
  "hotel_name": "Гранд Отель",
  "room_number": "205A",
  "room_type_name": "Стандартный Двухместный",
  "check_in_date": "2025-06-01",
  "check_out_date": "2025-06-07",
  "days_count": 6,
  "adults_count": 2,
  "children_count": 1,
  "pets_count": 0,
  "status": "A",
  "status_display": "Активно",
  "type": "G",
  "created_at": "2025-05-01T12:00:00Z",
  "cancellation": null,
  "moved_to_id": null
}
```

---

### Отменить бронирование

```
POST /api/me/bookings/{id}/cancel/
```

Доступ: Только гость

**Тело запроса:**
```json
{
  "reason": "Изменились планы"
}
```

**Ответ `200`:**
```json
{
  "detail": "Бронирование отменено."
}
```

**Ответ `400` (бронирование уже отменено или завершено):**
```json
{
  "detail": "Нельзя отменить уже завершенное или отмененное бронирование"
}
```

---

### Перенести бронирование

```
POST /api/me/bookings/{id}/move/
```

Доступ: Только гость

Старое бронирование получает статус `MOVED`, создаётся новое с новыми датами.

**Тело запроса:**
```json
{
  "check_in_date": "2025-07-10",
  "check_out_date": "2025-07-15"
}
```

**Ответ `200`:** объект нового бронирования (`BookingDetailSerializer`)

**Ответ `400`:**
```json
{
  "detail": "Нельзя перенести неактивное бронирование"
}
```

---

## Мои отзывы

### Список моих отзывов

```
GET /api/me/reviews/
```

Доступ: Только гость

**Параметры фильтрации:**

| Параметр | Тип | Описание |
|---|---|---|
| `status` | string | `D` (черновик), `M` (на модерации), `P` (опубликован), `R` (отклонён), `A` (архив) |
| `rating` | integer | Точная оценка |
| `rating_gte` | integer | Оценка не ниже указанной |
| `ordering` | string | `created_at`, `-created_at`, `published_at`, `-published_at` |

**Ответ `200`:**
```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 7,
      "hotel_name": "Гранд Отель",
      "room_type_name": "Стандартный Двухместный",
      "rating": 5,
      "status": "D",
      "status_display": "Черновик",
      "created_at": "2025-05-01T15:00:00Z"
    }
  ]
}
```

---

### Детали отзыва

```
GET /api/me/reviews/{id}/
```

Доступ: Только гость

**Ответ `200`:**
```json
{
  "id": 7,
  "booking_id": 42,
  "rating": 5,
  "comment": "Отличный отель, рекомендую!",
  "status": "D",
  "status_display": "Черновик",
  "moderated_by": null,
  "rejection_reason": null,
  "created_at": "2025-05-01T15:00:00Z",
  "published_at": null
}
```

---

### Создать отзыв (черновик)

```
POST /api/me/reviews/
```

Доступ: Только гость

Отзыв можно оставить только на завершённое бронирование (`status=CL`), принадлежащее текущему пользователю. Создаётся со статусом `DRAFT`.

**Тело запроса:**
```json
{
  "booking_id": 42,
  "rating": 5,
  "comment": "Отличный отель, рекомендую!"
}
```

**Ответ `201`:**
```json
{
  "id": 7,
  "booking_id": 42,
  "rating": 5,
  "comment": "Отличный отзыв, рекомендую!",
  "created_at": "2025-05-01T15:00:00Z"
}
```

**Ответ `400` (нет подходящего бронирования):**
```json
{
  "booking_id": ["У пользователя нет записи о закрытом бронировании с ID \"42\""]
}
```

---

### Редактировать черновик

```
PATCH /api/me/reviews/{id}/
```

Доступ: Только гость. Редактировать можно только отзыв со статусом `DRAFT`.

**Тело запроса:**
```json
{
  "rating": 4,
  "comment": "Хороший отель, но есть замечания."
}
```

**Ответ `200`:** обновлённый объект отзыва

**Ответ `400` (не черновик):**
```json
{
  "non_field_errors": ["Редактировать можно только черновик"]
}
```

---

### Отправить на модерацию

```
POST /api/me/reviews/{id}/submit/
```

Доступ: Только гость. Переводит черновик в статус `ON_MODERATION` и назначает модератора с наименьшей нагрузкой.

**Ответ `200`:**
```json
{
  "detail": "Отзыв отправлен на модерацию."
}
```

**Ответ `400`:**
```json
{
  "detail": "Отправить на модерацию можно только черновик"
}
```

**Ответ `503` (нет активных модераторов):**
```json
{
  "detail": "Нет доступных модераторов"
}
```

---

### Архивировать опубликованный отзыв

```
POST /api/me/reviews/{id}/archive/
```

Доступ: Только гость. Переводит опубликованный отзыв в статус `ARCHIVED` (скрывает из публичного доступа).

**Ответ `200`:**
```json
{
  "detail": "Отзыв скрыт из публичного доступа."
}
```

**Ответ `400`:**
```json
{
  "detail": "Нельзя убрать из публичного доступа неопубликованный отзыв."
}
```

---

### Удалить отзыв

```
DELETE /api/me/reviews/{id}/
```

Доступ: Только гость. Физически удаляет только отзывы со статусом `DRAFT` или `ON_MODERATION`. Опубликованные и архивные удалить нельзя — используй `/archive/`.

**Ответ `204`:** нет тела

**Ответ `403` (опубликован или уже в архиве):**
```json
{
  "detail": "Нельзя удалить отзыв со статусом \"Опубликован\""
}
```

---

## Справочник статусов

### Бронирование (`Booking.Status`)

| Код | Описание |
|---|---|
| `A` | Активно |
| `M` | Перенесено |
| `CA` | Отменено |
| `CL` | Завершено |

### Тип бронирования (`Booking.Type`)

| Код | Описание |
|---|---|
| `G` | Гарантированное (с предоплатой) |
| `N` | Негарантированное |

### Отзыв (`Review.Status`)

| Код | Описание |
|---|---|
| `D` | Черновик |
| `M` | На модерации |
| `P` | Опубликован |
| `R` | Отклонён |
| `A` | Архив |

### Категория номера (`RoomCategory.Tier`)

| Код | Описание |
|---|---|
| `SU` | Сюит |
| `A` | Апартамент |
| `L` | Люкс |
| `JSU` | Джуниор сюит |
| `ST` | Студия |
| `1` | Первая категория (стандарт) |
| `2` | Вторая категория |
| `3` | Третья категория |
| `4` | Четвёртая категория |
| `5` | Пятая категория |

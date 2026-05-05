# Значения по умолчанию
# Путь к фикстурам
FIXTURES_PATH = fixtures
# Тестовые пользователи
GUEST_ROLE_NAME = 'guest'
MOD_ROLE_NAME = 'moderator'
ADMIN_ROLE_NAME = 'admin'
USER_COUNT = 10
ROLE_NAME = $(GUEST_ROLE_NAME)
# Параметры удаления пользователей
USER_LOOKUP = 'admin__isnull=True,moderator_isnull=True'
# Тестовые отели
HOTEL_NAME = 'ИмяСетиОтелей'
HOTEL_COUNT = 5
ROOM_TYPE_COUNT = 15
ROOM_PER_HOTEL = 24
WITHOUT_PHOTO = ''
# Параметры удаления отелей
HOTEL_LOOKUP = 'is_active=False'
ROOM_TYPE_LOOKUP = ''
# Тестовые бронирования
BOOKING_COUNT = 30
REVIEW_COUNT = 5
# Параметры удаления бронирований
BOOKING_LOOKUP = ''

# Функции
define dump_to_file
	uv run python manage.py dumpdata --settings=config.settings \
		--indent 2 --format json --output $(FIXTURES_PATH)/$(2).json $(1)
endef

define load_from_file
	uv run python manage.py loaddata $(FIXTURES_PATH)/$(1).json
endef

define docker_dump_to_file
	docker compose exec backend $(call dump_to_file,$(1),$(2))
endef

define docker_load_from_file
	docker compose exec backend $(call load_from_file,$(1))
endef

define create_group
	docker compose exec backend uv run python manage.py create_group --name=$(1) --priority=$(2)
endef

list-commands:
	@echo Доступные make-команды:
	@echo   migrate                     - Применить миграции
	@echo   shell                       - Запустить Django shell
	@echo   superuser                   - Создать администратора
	@echo   test                        - Запустить pytest
	@echo   lint                        - Проверить код ruff
	@echo   lint-fix                    - Исправить ошибки ruff
	@echo   gen-secret                  - Сгенерировать SECRET_KEY
	@echo   load-data                   - Загрузить фикстуры
	@echo   save-data                   - Сохранить фикстуры
	@echo   create-guests               - Создать тестовых гостей (USER_COUNT)
	@echo   create-moderators           - Создать тестовых модераторов (USER_COUNT)
	@echo   create-admins               - Создать тестовых администраторов (USER_COUNT)
	@echo   create-users                - Создать пользователей с указанной ролью (USER_COUNT, ROLE_NAME)
	@echo   gen-users                   - Создать набор пользователей (30 гостей, 5 модераторов, 2 админа)
	@echo   delete-all-users            - Удалить ВСЕХ пользователей
	@echo   delete-users                - Удалить пользователей по фильтру (USER_LOOKUP)
	@echo   create-hotels               - Сгенерировать отели и номера (HOTEL_NAME, HOTEL_COUNT, ROOM_TYPE_COUNT, ROOM_PER_HOTEL)
	@echo   create-room-types           - Создать только типы номеров (ROOM_TYPE_COUNT)
	@echo   create-rooms                - Создать только комнаты (ROOM_PER_HOTEL)
	@echo   delete-hotels               - Удалить отели по фильтру (HOTEL_LOOKUP)
	@echo   delete-room-types           - Удалить типы номеров по фильтру (ROOM_TYPE_LOOKUP)
	@echo   delete-hotels-all           - Удалить все отели и типы номеров
	@echo   create-bookings             - Сгенерировать бронирования и отзывы (BOOKING_COUNT, REVIEW_COUNT)
	@echo   delete-bookings-all         - Удалить все бронирования и отзывы (BOOKING_LOOKUP)
	@echo   gen-test-data               - Создать полный набор тестовых данных (пользователи, отели, бронирования)
	@echo   list-commands               - Показать эту справку

migrate:
	docker compose exec backend uv run python manage.py makemigrations
	docker compose exec backend uv run python manage.py migrate

shell:
	docker compose exec backend uv run python manage.py shell

superuser:
	docker compose exec backend uv run python manage.py createsuperuser

test:
	docker compose exec backend uv run python manage.py test $(TEST_NAME)

lint:
	docker compose exec backend uv run ruff check .

lint-fix:
	docker compose exec backend uv run ruff check --fix .

gen-secret:
	docker compose exec backend uv run python -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(32))"
	@echo "Замените строку с SECRET_KEY в .env на сгенерированную"

# Тестовые данные
load-data:
	$(call docker_load_from_file,hotels_data)
	$(call docker_load_from_file,users_data)
	$(call docker_load_from_file,bookings_data)

save-data:
	$(call docker_dump_to_file,hotels,hotels_data)
	$(call docker_dump_to_file,accounts,users_data)
	$(call docker_dump_to_file,bookings,bookings_data)

## Пользователи
create-guests:
	@echo "Доступен параметр USER_COUNT=<число>"
	docker compose exec backend uv run python manage.py create_test_users --users $(USER_COUNT) --role $(GUEST_ROLE_NAME)

create-moderators:
	@echo "Доступен параметр USER_COUNT=<число>"
	docker compose exec backend uv run python manage.py create_test_users --users $(USER_COUNT) --role $(MOD_ROLE_NAME)

create-admins:
	@echo "Доступен параметр USER_COUNT=<число>"
	docker compose exec backend uv run python manage.py create_test_users --users $(USER_COUNT) --role $(ADMIN_ROLE_NAME)

create-users:
	@echo "Доступны параметры USER_COUNT=<число>, ROLE_NAME=<роль>"
	@echo "Роли:"
	docker compose exec backend uv run python manage.py create_test_users --role --help
	docker compose exec backend uv run python manage.py create_test_users --users $(USER_COUNT) --role $(ROLE_NAME)

gen-users: USER_COUNT=30 create-guests USER_COUNT=5 create-moderators USER_COUNT=2 create-admins

delete-all-users:
	docker compose exec backend uv run python manage.py delete_users

delete-users:
	@echo "Доступен параметр USER_LOOKUP=<параметр1=значение1,параметр2=значение2>"
	docker compose exec backend uv run python manage.py delete_users --user-lookup $(USER_LOOKUP)

## Отели
create-hotels:
	@echo "Доступны параметры HOTEL_NAME=<название сети> HOTEL_COUNT=<число> ROOM_TYPE_COUNT=<число> ROOM_PER_HOTEL=<число> WITHOUT_PHOTO='--without-photos'"
	docker compose exec backend uv run python manage.py create_test_hotels --name $(HOTEL_NAME) \
		--hotel-count $(HOTEL_COUNT) --room-type-count $(ROOM_TYPE_COUNT) --room-per-hotel $(ROOM_PER_HOTEL) $(WITHOUT_PHOTO)

create-room-types:
	@echo "Доступны параметры HOTEL_NAME=<название сети> ROOM_TYPE_COUNT=<число>"
	docker compose exec backend uv run python manage.py create_test_hotels --name $(HOTEL_NAME) \
		--hotel-count 0 --room-type-count $(ROOM_TYPE_COUNT) --room-per-hotel 0

create-rooms:
	@echo "Доступны параметры HOTEL_NAME=<название сети> ROOM_PER_HOTEL=<число> WITHOUT_PHOTO='--without-photos'"
	docker compose exec backend uv run python manage.py create_test_hotels --name=$(HOTEL_NAME) \
		--hotel-count=0 --room-type-count=0 --room-per-hotel=$(ROOM_PER_HOTEL) $(WITHOUT_PHOTO)

delete-hotels:
	@echo "Доступен параметр HOTEL_LOOKUP=<параметр1=значение1,параметр2=значение2>"
	docker compose exec backend uv run python manage.py delete_hotels --hotel-lookup=$(HOTEL_LOOKUP)

delete-room-types:
	@echo "Доступен параметр ROOM_TYPE_LOOKUP=<параметр1=значение1,параметр2=значение2>"
	docker compose exec backend uv run python manage.py delete_room_types --room-type-lookup=$(ROOM_TYPE_LOOKUP)

delete-hotels-all: delete-hotels delete-room-types

# Бронирование
create-bookings:
	@echo "Доступны параметры BOOKING_COUNT=<число> REVIEW_COUNT=<число>"
	docker compose exec backend uv run python manage.py create_test_bookings \
		--bookings=$(BOOKING_COUNT) --reviews=$(REVIEW_COUNT)

delete-bookings-all:
	@echo "Доступен параметр BOOKING_LOOKUP=<параметр1=значение1,параметр2=значение2>"
	docker compose exec backend uv run python manage.py delete_bookings --booking-lookup=$(BOOKING_LOOKUP)

gen-test-data: gen-users create-hotels create-bookings

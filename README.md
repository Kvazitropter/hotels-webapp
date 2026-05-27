[![project check](https://github.com/kotovann/hotels-webapp/actions/workflows/check.yml/badge.svg?branch=main)](https://github.com/kotovann/hotels-webapp/actions/workflows/check.yml)

[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=kotovann_hotels-webapp&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=kotovann_hotels-webapp)

[![Coverage](https://sonarcloud.io/api/project_badges/measure?project=kotovann_hotels-webapp&metric=coverage)](https://sonarcloud.io/summary/new_code?id=kotovann_hotels-webapp)

!Для запуска Docker используйте команды Makefile!

####  Первый запуск (с загрузкой фикстур):

```bash
make init
```

#### Запуск с пересборкой + миграции (без загрузки фикстур):

```bash
make dev
```

#### Просто запуск сущесвуещих контейнеров:
```bash
make up
```

#### Пересоздать БД:

```bash
make db-redo
```

#### Остановить:

```bash
make down
```

Остановить и удалить данные БД:

```bash
make down-v
```

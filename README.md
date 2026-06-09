# HotelsWeb

<p align="center">
  <a href="https://github.com/kotovann/hotels-webapp/actions/workflows/check.yml">
    <img src="https://github.com/kotovann/hotels-webapp/actions/workflows/check.yml/badge.svg?branch=main" alt="project check">
  </a>
  <a href="https://sonarcloud.io/summary/new_code?id=kotovann_hotels-webapp">
    <img src="https://sonarcloud.io/api/project_badges/measure?project=kotovann_hotels-webapp&metric=alert_status" alt="Quality Gate Status">
  </a>
  <a href="https://sonarcloud.io/summary/new_code?id=kotovann_hotels-webapp">
    <img src="https://sonarcloud.io/api/project_badges/measure?project=kotovann_hotels-webapp&metric=coverage" alt="Coverage">
  </a>
</p>

Веб-приложение сети гостиниц доступно по [ссылке](https://тутати.рф/)

    - frontend: React
    - backend: Django + Django REST Framework
    - database: PostgreSQL
    - reverse proxy: Nginx
    - deployment: GitHub Actions + GHCR + Ansible
    - monitoring: Uptime Kuma


###  Локальный запуск

**Требования:**

- Docker
- Make

Файлы `.env` не хранятся в репозитории. Пример наполнения -  `.env.example` и `backend/.env.example`

1. Склонировать репозиторий
2. Запуск с созданием env-файлов, сборкой контейнеров, применением миграций и загрузкой фикстур:

```bash
make init
```
**Основные команды Makefile:**

| Команда  | Действие |
| --- | --- |
| make dev | пересборка + миграции (без загрузки фикстур) |
| make up | запуск существуещих контейнеров |
| make db-redo | пересоздать БД |
| make down | остановить |
| make down-v | остановить + удалить данные БД|

# dongmoon

1인 개발로 빠르게 제품을 만들기 위한 Django 기반 웹앱 템플릿입니다.

## Stack

- Python 3.12+
- Django 5.2 LTS
- htmx 2.x
- Tailwind CSS CDN
- SQLite for local development
- uv for dependency and virtualenv management

Django 경험을 그대로 살리면서, 프론트엔드는 별도 SPA 없이 서버 렌더링과 htmx로 시작합니다. 화면이 복잡해지거나 실시간 협업, 무거운 클라이언트 상태가 필요해질 때 React/Next.js를 별도 프론트로 분리하는 것을 추천합니다.

## Getting Started

```powershell
uv sync
Copy-Item .env.example .env
uv run python manage.py migrate
uv run python manage.py import_schools "path\to\학교기본정보(고)_전체.csv"
uv run python manage.py runserver
```

Open http://127.0.0.1:8000

## Useful Commands

```powershell
uv run python manage.py test
uv run python manage.py createsuperuser
uv run python manage.py import_schools "path\to\학교기본정보(고)_전체.csv"
uv run python manage.py collectstatic
```

## Accounts

- `/accounts/signup/`: 회원가입
- `/accounts/login/`: 로그인
- `/accounts/logout/`: 로그아웃

## Project Layout

```text
config/             Django project settings
apps/core/          First local Django app
templates/          Shared and app templates
static/             Project static assets
```

## Next Decisions

1. Decide the first user workflow and model it in `apps/core/models.py`.
2. Keep the first screen server-rendered in Django templates.
3. Add htmx only where a full page reload feels clumsy.
4. Move to PostgreSQL when deployment or relational data volume makes SQLite limiting.

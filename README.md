# dongmoon

고등학교를 중심으로 동문을 찾고, 학교별 커뮤니티를 운영하는 Django 기반 웹 애플리케이션입니다.

## 주요 기능

### 학교 탐색

- 학교명, 지역, 도로명 주소로 고등학교를 검색할 수 있습니다.
- 학교 상세 화면에서 기본 정보, 주소, 연락처, 홈페이지, 설립 정보 등을 확인할 수 있습니다.
- 로그인 사용자는 관심 학교를 즐겨찾기에 추가하거나 해제할 수 있습니다.
- 내 인증 학교와 즐겨찾기 학교를 검색 화면에서 빠르게 확인할 수 있습니다.

### 회원과 프로필

- 회원가입, 로그인, 로그아웃 기능을 제공합니다.
- 마이페이지에서 닉네임, 자기소개, 프로필 이미지를 관리할 수 있습니다.
- 사용자 프로필에서 작성한 글, 댓글, 방명록, 추천 내역을 확인할 수 있습니다.

### 학교 인증

- 사용자는 재학 또는 졸업 증빙 파일을 제출해 학교 인증을 요청할 수 있습니다.
- 관리자 승인 시 사용자 프로필에 인증 학교가 연결됩니다.
- 인증된 사용자는 해당 학교의 인증 게시판에 접근할 수 있습니다.

### 학교별 커뮤니티

- 학교 상세 화면에서 방명록과 게시판을 사용할 수 있습니다.
- 방명록은 사용자당 하루 한 번 작성할 수 있습니다.
- 게시글은 일반 게시판과 인증 게시판으로 구분됩니다.
- 게시글에는 이미지 첨부, 댓글 작성, 추천, 삭제 기능이 포함됩니다.
- 인증 게시판은 해당 학교 인증 사용자만 열람하고 작성할 수 있습니다.

### 신고와 커뮤니티 관리

- 사용자는 게시글과 댓글을 신고할 수 있습니다.
- 학교 운영자 또는 스태프는 학교별 관리 대시보드에서 신고 내역을 확인할 수 있습니다.
- 관리자는 게시글과 댓글을 숨김, 복구, 삭제 처리할 수 있습니다.
- 숨김 처리된 게시글은 작성자와 관리 권한자만 확인할 수 있습니다.

### 유명 동문

- 학교별 유명 동문 목록을 표시할 수 있습니다.
- 나무위키 학교 문서에서 유명 동문 후보를 수집하는 관리 명령을 제공합니다.
- 수집된 후보는 관리자 검수 후 공개하거나, 옵션을 통해 자동 승인할 수 있습니다.

### 운영자 관리

- Django Admin에서 학교, 프로필, 학교 인증 요청, 학교 운영자, 방명록, 게시글, 댓글, 신고, 유명 동문 데이터를 관리할 수 있습니다.
- 학교 운영자를 지정해 특정 학교 커뮤니티의 신고와 콘텐츠를 관리하게 할 수 있습니다.

## 기술 스택

- Python 3.12+
- Django 5.2
- SQLite
- Pillow
- WhiteNoise
- uv
- Ruff

## 시작하기

```powershell
uv sync
Copy-Item .env.example .env
uv run python manage.py migrate
uv run python manage.py runserver
```

브라우저에서 `http://127.0.0.1:8000`으로 접속합니다.

## 데이터 적재

학교 기본 정보 CSV를 가져옵니다.

```powershell
uv run python manage.py import_schools "path\to\school.csv"
```

나무위키에서 유명 동문 후보를 수집합니다.

```powershell
uv run python manage.py crawl_namuwiki_alumni --school-name "학교명"
uv run python manage.py crawl_namuwiki_alumni --school-code "학교코드"
uv run python manage.py crawl_namuwiki_alumni --all --limit 100
```

후보를 바로 공개 데이터로 저장하려면 `--auto-approve`를 함께 사용합니다.

```powershell
uv run python manage.py crawl_namuwiki_alumni --all --auto-approve
```

## 주요 URL

| 경로 | 기능 |
| --- | --- |
| `/` | 학교 검색 |
| `/schools/` | 학교 검색 |
| `/schools/<code>/` | 학교 상세, 방명록, 게시판, 유명 동문 |
| `/schools/<code>/moderation/` | 학교별 관리 대시보드 |
| `/accounts/signup/` | 회원가입 |
| `/accounts/login/` | 로그인 |
| `/accounts/logout/` | 로그아웃 |
| `/accounts/me/` | 마이페이지 |
| `/accounts/users/<id>/` | 사용자 프로필 |
| `/admin/` | Django Admin |
| `/health/` | 헬스 체크 |

## 유용한 명령

```powershell
uv run python manage.py test
uv run python manage.py createsuperuser
uv run python manage.py collectstatic
uv run ruff check .
```

## 프로젝트 구조

```text
config/                         Django 프로젝트 설정
apps/accounts/                  회원, 프로필, 학교 인증
apps/core/                      학교, 커뮤니티, 신고, 유명 동문
apps/core/management/commands/  데이터 적재와 크롤링 명령
templates/                      공통 및 앱 템플릿
static/                         정적 파일
media/                          업로드 파일
```

## 개발 메모

- 로컬 개발 기본 데이터베이스는 SQLite입니다.
- 업로드 파일은 개발 환경에서 `media/` 아래에 저장됩니다.
- 운영 배포 시에는 `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, 정적 파일, 미디어 파일 저장소 설정을 환경에 맞게 조정해야 합니다.

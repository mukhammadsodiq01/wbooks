# WBooks — Wonder Books

Interactive reading platform for kids and teens. Phase 1 delivers accounts,
guardian-linked family profiles, the story/page schema and a fully styled
Django front end. Phase 2 adds the immersive, auto-saving reader with four
switchable visual atmospheres. Phase 3 adds the post-reading flow (recap →
quiz → badges). Phase 4 adds the guardian dashboard with real reading-time
reporting and the `seed_wbooks` demo library.

## Stack

- Python 3.12+ / Django 6.1 / Django REST Framework
- PostgreSQL (default) with optional SQLite preview mode
- HTML5, modern CSS (custom properties, animations) and vanilla JavaScript

## Local setup

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

Create the PostgreSQL database:

```sql
CREATE DATABASE wbooks;
```

Copy `.env.example` to `.env` and adjust the database credentials. PostgreSQL is
the default backend (a local `.env` is already provided for an immediate SQLite
preview on this workstation):

```env
DJANGO_DEBUG=True
DJANGO_SECRET_KEY=replace-this-in-production
DB_ENGINE=postgresql
DB_NAME=wbooks
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=127.0.0.1
DB_PORT=5432
```

For a zero-configuration preview on a machine without PostgreSQL, set
`DB_ENGINE=sqlite` in `.env`.

> Windows note: if the `psycopg[binary]` wheel is blocked by an application
> control policy, add the PostgreSQL `bin` directory
> (`C:\Program Files\PostgreSQL\18\bin`) to `PATH` so the pure-Python `psycopg`
> build can load `libpq`.

```bash
python manage.py migrate
python manage.py seed_wbooks
python manage.py runserver
```

Demo credentials created by `seed_wbooks` (password `WBooks!234`):

| Role | Email | Username | What to try |
| --- | --- | --- | --- |
| Parent | parent@wbooks.app | demo_parent | `/dashboard/parent/` — the family report |
| Child | amara@wbooks.app | demo_amara | Mid-story on a ForestBook tale |
| Child | kofi@wbooks.app | demo_kofi | Finished story, recap and quiz ready |

`python manage.py seed_demo` is kept as an alias of `seed_wbooks`.

Create a Django admin account with `python manage.py createsuperuser`.
The admin at `/admin/` manages users, books, the eight page slots per book,
reading progress, reading sessions, quizzes, results and badges.

## Tests

```bash
python manage.py test books
```

65 automated tests cover accounts, models, the reader, the progress API, the
post-reading flow, the guardian dashboard and both seed commands.

## Phase 1 scope

- Custom `User` with `CHILD` / `PARENT` roles and automatic `Profile` creation.
- `ParentChildLink` guardian-to-reader relationship (one guardian per reader,
  many readers per guardian).
- Registration and login flows, role-aware dashboards and family linking.
- `Book`, `BookPage` (pages 1–8 enforced at validation and database level) and
  `ReadingProgress` models with captured progress updates.
- Responsive, animated marketing page, auth screens, book preview and shelves.
- Django admin configuration, seed command and 18 automated tests.

## Phase 2 scope

- Interactive reader at `/books/<slug>/read/` for child accounts, with 3D page
  flips, arrow keys, swipe gestures and page dots.
- Four CSS-variable atmospheres with live switching, persisted per book in
  `localStorage`:
  - `ForestBook` — bark-textured pages, falling leaves, earthy greens.
  - `IceBook` — frosted glass, drifting crystals, cool blues.
  - `HoloBook` — neon cyan hologram UI, scanlines, data-stream particles.
  - `ClassicBook` — warm paper, serif type, eye-comfort pacing.
- `GET/POST /api/progress/` (DRF) restores and saves the current page on every
  turn, with retry, online recovery and `sendBeacon` on page hide.
- Reader progress restores on reopen; `?restart=1` rewinds to page 1 and the
  final page marks the story complete.
- Reader entry points on book cards, detail pages and the child dashboard.
- 30 automated tests covering accounts, models, reader access and progress API.

## Phase 3 scope — post-reading flow

- `QuizQuestion` (book or general, JSON options, validated correct answer),
  `QuizResult` (score plus a frozen review snapshot), `Badge` and `ChildBadge`.
- Animated recap at `/books/<slug>/recap/`: CSS/JS storyboard with autoplay,
  scene dots, swipe, keyboard control and optional video player, plus the
  story's lessons and moral.
- Interactive quiz at `/books/<slug>/quiz/` and `/quiz/general/` with instant
  per-question feedback, a live progress meter and server-side grading in
  `books/quizzes.py`.
- Result screen at `/quiz/results/<pk>/` with score ring, badge unlocks and a
  question-by-question review.
- Eight starter badges (First Book, Forest Explorer, Ice Voyager,
  Holo Navigator, Classic Storyteller, First Quiz, Quiz Master, Bookworm)
  unlocked automatically from stored progress by `books/achievements.py`.
- 51 automated tests after this phase.

## Phase 4 scope — guardian dashboard and seed data

- Rebuilt parent dashboard at `/dashboard/parent/` showing, per reader:
  current page out of 8, completed books, quiz scores, time spent and earned
  badges; plus family totals, a daily goal ring, a seven-day reading chart,
  a per-story time breakdown and the badge catalogue.
- Real reading-time tracking: the reader reports seconds with every save, the
  API stores them on `ReadingProgress.reading_seconds` and in
  `ReadingSession` rows, and `books/reports.py` turns them into guardian
  figures.
- New `python manage.py seed_wbooks` command shipping one guardian, two young
  readers, three original eight-page stories (ForestBook, IceBook and
  HoloBook atmospheres), recap scenes, four quiz questions per story, five
  general quiz questions, eight starter badges and a believable reading
  history. The command is idempotent and `seed_demo` now delegates to it.
- 65 automated tests after this phase.


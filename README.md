# Vocabestie

A vocabulary learning app with flashcards, quizzes, and spaced repetition (SM-2 algorithm).

## Features

- **Flashcards**: Review vocabulary with interactive flip cards
- **Quizzes**: Multiple choice quizzes to test your knowledge
- **Spaced Repetition**: SM-2 algorithm optimizes review timing for better retention
- **Word Management**: Add, edit, and delete vocabulary words

## Tech Stack

- **Backend**: FastAPI
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Migrations**: Alembic
- **Frontend**: Jinja2 templates + Tailwind CSS + HTMX

## Setup

### Prerequisites

- Python 3.10+
- Docker and Docker Compose

### Installation

1. Clone the repository and navigate to the project directory

2. Create a virtual environment and install dependencies:
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

3. Start PostgreSQL:
```bash
docker compose up -d
```

4. Run database migrations:
```bash
alembic upgrade head
```

5. Start the development server:
```bash
uvicorn app.main:app --reload
```

6. Open http://localhost:8000 in your browser

## API Documentation

Once the server is running, visit http://localhost:8000/docs for interactive API documentation.

## Project Structure

```
vocabestie/
├── app/
│   ├── main.py              # FastAPI app entry
│   ├── config.py            # Settings
│   ├── database.py          # SQLAlchemy setup
│   ├── models/              # Database models
│   ├── schemas/             # Pydantic schemas
│   ├── routers/             # API endpoints
│   ├── services/            # Business logic (SM-2)
│   └── templates/           # Jinja2 templates
├── alembic/                 # Database migrations
├── docker-compose.yml       # PostgreSQL container
└── requirements.txt
```

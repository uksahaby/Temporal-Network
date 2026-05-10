# Temporal Network Analysis Backend

A FastAPI backend for processing and analyzing temporal network data with PostgreSQL database.

## Prerequisites

- Docker and Docker Compose
- Python 3.12+ (for local development)

## Quick Start with Docker

### 1. Start the database and API

```bash
# Start all services (PostgreSQL + FastAPI)
docker-compose up -d

# Or start only the database
docker-compose up -d db
```

### 2. Check service status

```bash
docker-compose ps
```

### 3. View logs

```bash
# All services
docker-compose logs -f

# Only API
docker-compose logs -f api

# Only database
docker-compose logs -f db
```

### 4. Access the API

- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

### 5. Stop services

```bash
docker-compose down

# Remove volumes (deletes database data)
docker-compose down -v
```

## Local Development

### 1. Start only the database with Docker

```bash
docker-compose up -d db
```

### 2. Set up Python environment

```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
.\venv\Scripts\Activate.ps1

# Activate (Linux/Mac)
source venv/bin/activate

# Install dependencies
pip install -r requirement.txt
```

### 3. Configure environment

Copy `.env.example` to `.env` and adjust settings:

```bash
cp .env.example .env
```

### 4. Run the API locally

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Database

### Connection Details (Development)

- Host: `localhost`
- Port: `5432`
- Database: `temporal_network`
- User: `temporal_user`
- Password: `temporal_password`

### Access PostgreSQL

```bash
# Connect via Docker
docker-compose exec db psql -U temporal_user -d temporal_network

# Or use any PostgreSQL client with the connection details above
```

### Database Migrations (Alembic)

```bash
# Initialize migrations (first time only)
alembic init alembic

# Create a new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Project Structure

```
temporal-network-backend/
├── app/
│   ├── api/           # API endpoints
│   ├── core/          # Configuration
│   ├── models/        # Database models & schemas
│   ├── services/      # Business logic
│   └── utils/         # Helpers
├── data/              # File storage
├── docker-compose.yml # Docker services
├── Dockerfile         # API container
├── requirement.txt    # Python dependencies
└── .env              # Environment variables
```

## API Endpoints

- `GET /` - API info
- `GET /health` - Health check
- `POST /api/upload` - Upload network data
- `POST /api/analyze` - Run analysis
- See `/docs` for full API documentation

## Environment Variables

| Variable       | Description                  | Default                                                                        |
| -------------- | ---------------------------- | ------------------------------------------------------------------------------ |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://temporal_user:temporal_password@localhost:5432/temporal_network` |
| `ENVIRONMENT`  | Environment mode             | `development`                                                                  |
| `DEBUG`        | Enable debug mode            | `true`                                                                         |
| `SECRET_KEY`   | Application secret key       | -                                                                              |

# Task-Management
Python based Task Management API

---

# The Database Design
Details about database design are stored in design directory.

---

# Setup

**Environment variables**
1. Rename .env.example to .env
2. Change database url

## Database setup
Run following commands:
1. uv run alembic init alembic
2. uv run alembic revision --autogenerate -m "create initial"
3. uv run alembic upgrade head

## Application setup

This project uses `uv` package manager. Use the official guide [uv](https://docs.astral.sh/uv/) to install uv.

Once installed follow the below steps:

> uv run main.py

The fastapi documentation will be available in [local](http://localhost:8000)

---
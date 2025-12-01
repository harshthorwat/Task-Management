# Task-Management
Python based Task Management API

---

# Chosen Features
1. Allows filtering tasks by multiple criteria (status, priority, assignee, dates, tags) using AND/OR logic
Reason: 
- The filtering feature is most widely used in task management systems. 
- Stakeholders and team members can use this feature for analysis.

2. Making tasks depend on other tasks. (For ex - Task 2 is blocked on Task 1)
Reason:
- In real world task dependance is very common, like dependancy on other team members task etc.
- Hence this feature is must needed

3. API showing task distribution, and overdue tasks per user
- This feature can be very useful in order to monitor the task progress.
- If one team member is loaded with multiple tasks then we can evenly distribute the tasks among all team members.

---

# The Database Design
Details about database **design** are stored in design directory.

---

# Setup

**Environment variables**
1. Rename .env.example to .env
2. Change database url

## Application setup
This project uses `uv` package manager. Use the official guide [uv](https://docs.astral.sh/uv/) to install uv.

Once installed follow the below steps:

### Database setup
Run following commands:
1. uv run alembic init alembic
2. uv run alembic revision --autogenerate -m "create initial"
3. uv run alembic upgrade head

Run the application by:
> uv run main.py

The fastapi documentation will be available in [local](http://localhost:8000)

---
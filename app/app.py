from fastapi import FastAPI, Depends, HTTPException
from app.database import get_db, engine, Base
from sqlalchemy.ext.asyncio import AsyncSession
import app.crud as crud
import app.schemas as schemas
from app.models import User, RefreshToken
from app.auth_utils import hash_password, verify_password, create_access_token, create_refresh_token_jti, REFRESH_TOKEN_EXPIRE_DAYS
from datetime import datetime, timedelta
from sqlalchemy import select

app = FastAPI(title="Task Manager")

@app.on_event("startup")
async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@app.post("/auth/signup")
async def signup(user_in: schemas.UserCreate, db: AsyncSession = Depends(get_db)):
    q = await db.execute(select(User).where(User.username == user_in.username))
    if q.scalars().first():
        raise HTTPException(status_code=400, detail="username already exists")

    q = await db.execute(select(User).where(User.email == user_in.email))
    if q.scalars().first():
        raise HTTPException(status_code=400, detail="email already exists")

    hashed = hash_password(user_in.password)
    user = User(
        username=user_in.username,
        email=user_in.email,
        team_id=user_in.team_id,
        hashed_password=hashed
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return {"id": str(user.id)}

@app.post("/auth/token")
async def login_for_token(username: str, password: str, db: AsyncSession=Depends(get_db)):
    q = await db.execute(select(User).where(User.username==username))
    user = q.scalars().first()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect credentials")
    access_token = create_access_token(sub=str(user.id), data={"roles": []})
    jti = create_refresh_token_jti()
    expires_at = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    rt = RefreshToken(user_id = user.id, jti=jti, expires_at=expires_at)
    db.add(rt)
    await db.commit()
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "refresh_jti": str(jti),
        "refresh_expires_at": expires_at
    }

@app.post("/auth/token/refresh")
async def refresh_token(refresh_jti: str, db: AsyncSession=Depends(get_db)):
    q = await db.execute(select(RefreshToken).where(RefreshToken.jti == refresh_jti))
    rt = q.scalars().first()
    if not rt or rt.revoked or rt.expires_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Invalid refresh")
    access_token = create_access_token(sub=str(rt.user_id))
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

@app.post("/teams/", response_model=schemas.TeamRead)
async def create_team(name: schemas.TeamCreate, db: AsyncSession=Depends(get_db)):
    team = await crud.create_team(db, name=name.name)
    return team

@app.post("/users/", response_model=schemas.UserRead)
async def create_user(user_in: schemas.UserCreate, db: AsyncSession = Depends(get_db)):
    user = await crud.create_user(db, username=user_in.username, email=user_in.email, team_id=user_in.team_id)
    return user

@app.post("/tasks/", response_model=schemas.TaskRead)
async def create_task(task_in: schemas.TaskCreate, db: AsyncSession=Depends(get_db)):
    task = await crud.create_task(db, task_in)
    return task

@app.get("/tasks/{task_id}", response_model=schemas.TaskRead)
async def read_task(task_id: int, db: AsyncSession=Depends(get_db)):
    task = await crud.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not Found")
    return task

@app.get("/tasks/", response_model=list[schemas.TaskRead])
async def list_tasks(skip: int=0, limit: int=50, db: AsyncSession=Depends(get_db)):
    tasks = await crud.list_tasks(db, skip=skip, limit=limit)
    return tasks

@app.post("/assignments/", response_model=schemas.AssignmentRead)
async def create_assignment(a: schemas.AssignmentCreate, db: AsyncSession=Depends(get_db)):
    assignment = await crud.create_assignment(db, a)
    return assignment

@app.post("/comments/", response_model=schemas.CommentRead)
async def add_comment(c: schemas.CommentCreate, db: AsyncSession=Depends(get_db)):
    comment = await crud.add_comment(db, c)
    return comment

@app.post("/tasks/{task_id}/dependencies/{depends_on_id}")
async def add_dependency(task_id: int, depends_on_id: int, db:AsyncSession=Depends(get_db)):
    if task_id == depends_on_id:
        raise HTTPException(status_code=400, detail="Task can not depend on itself")
    
    t1 = await crud.get_task(db, task_id=task_id)
    t2 = await crud.get_task(db, depends_on_id)
    if not t1 or not t2:
        raise HTTPException(status_code=404, detail="Task not found")
    dep = await crud.add_dependency(db, task_id=task_id, depends_on_task_id=depends_on_id)
    return {"status": "ok","dependency": {"task_id": dep.task_id, "depends_on_task_id": dep.depends_on_task_id}}

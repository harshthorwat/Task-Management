from fastapi import FastAPI, Depends, HTTPException, status, Query
from app.database import get_db, engine, Base
from sqlalchemy.ext.asyncio import AsyncSession
import app.crud as crud
import app.schemas as schemas
from app.models import User, RefreshToken
from app.auth_utils import hash_password, verify_password, create_access_token, create_refresh_token_jti, REFRESH_TOKEN_EXPIRE_DAYS
from datetime import datetime, timedelta
from sqlalchemy import select
from app.deps import get_current_user
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.exc import IntegrityError
from typing import Optional

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
async def login_for_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    q = await db.execute(select(User).where(User.username == form_data.username))
    user = q.scalars().first()
    if not user or not verify_password(form_data.password, user.hashed_password or ""):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect credentials")

    access_token = create_access_token(sub=str(user.id), data={"roles": []})

    jti = create_refresh_token_jti()
    expires_at = datetime.utcnow() + timedelta(days=30)  
    rt = RefreshToken(user_id=user.id, jti=jti, expires_at=expires_at)
    db.add(rt)
    try:
        await db.commit()
        await db.refresh(rt)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Unable to create refresh token")

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "refresh_jti": str(jti),
        "refresh_expires_at": expires_at.isoformat() 
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

@app.get("/user/", response_model=list[schemas.UserRead])
async def list_users(skip: int=0, limit: int=50, db: AsyncSession=Depends(get_db), current_user = Depends(get_current_user)):
    if current_user.is_superuser:
        users = await crud.list_users(db, skip=skip, limit=limit)
        return users
    else:
        raise HTTPException(status_code=401, detail="User not authorized to perform this operation")

@app.post("/teams/", response_model=schemas.TeamRead)
async def create_team(name: schemas.TeamCreate, db: AsyncSession=Depends(get_db), current_user = Depends(get_current_user)):
    if current_user.is_superuser:
        team = await crud.create_team(db, name=name.name)
        return team
    else:
        raise HTTPException(status_code=401, detail="User not authorized to perform this operation")

@app.post("/tasks/", response_model=schemas.TaskRead)
async def create_task(task_in: schemas.TaskCreate, db: AsyncSession=Depends(get_db), current_user = Depends(get_current_user)):
    task = await crud.create_task(db, task_in)
    return task

@app.get("/tasks/{task_id}", response_model=schemas.TaskRead)
async def read_task(task_id: int, db: AsyncSession=Depends(get_db), current_user = Depends(get_current_user)):
    task = await crud.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not Found")
    return task

@app.get("/tasks/", response_model=list[schemas.TaskRead])
async def list_tasks(skip: int=0, limit: int=50, db: AsyncSession=Depends(get_db), current_user = Depends(get_current_user)):
    tasks = await crud.list_tasks(db, skip=skip, limit=limit)
    return tasks

@app.post("/tasks/bulk_update", response_model=schemas.BulkTaskUpdateResponse)
async def bulk_update_tasks(
    payload: schemas.BulkTaskUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    items = [item.dict(exclude_unset=False) for item in payload.items]
    updated_tasks, not_found, results = await crud.bulk_update_tasks(db, items)

    updated_ids = [t.id for t in updated_tasks] if updated_tasks else []
    return schemas.BulkTaskUpdateResponse(updated=updated_ids, not_found=not_found, results=[schemas.BulkTaskUpdateResultItem(**r) for r in results])

@app.post("/tasks/filter")
async def filter_tasks_route(
    filters: schemas.TaskFilter,
    db: AsyncSession = Depends(get_db)
):
    tasks = await crud.filter_tasks(
        db,
        status=filters.status,
        priority=filters.priority,
        assignee=filters.assignee,
        start_date=filters.start_date,
        end_date=filters.end_date,
        title_search=filters.title_search,
        logic=filters.logic,
        skip=filters.skip,
        limit=filters.limit
    )
    return tasks

@app.get("/task_distribution", response_model=schemas.TaskDistributionResponse)
async def task_distribution(
    group_by: str = Query("status", regex="^(status|priority|team|assignee)$"),
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    try:
        rows = await crud.get_task_distribution(db, group_by=group_by, skip=skip, limit=limit)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    items = [schemas.DistributionItem(key=r[0], count=r[1]) for r in rows]
    return schemas.TaskDistributionResponse(group_by=group_by, items=items)

@app.get("/overdue_by_user", response_model=schemas.OverdueByUserResponse)
async def overdue_by_user(
    as_of: Optional[datetime] = None,
    include_tasks: bool = Query(False),
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    as_of = as_of or datetime.utcnow()
    rows = await crud.get_overdue_tasks_per_user(db, as_of=as_of, include_tasks=include_tasks, skip=skip, limit=limit)
    users = []
    for r in rows:
        brief_tasks = None
        if include_tasks and r.get("overdue_tasks"):
            brief_tasks = [schemas.TaskBrief(**t) for t in r["overdue_tasks"]]
        users.append(schemas.OverdueUserItem(
            user_id=r["user_id"],
            username=r.get("username"),
            overdue_count=r["overdue_count"],
            overdue_tasks=brief_tasks
        ))
    return schemas.OverdueByUserResponse(as_of=as_of, users=users)


@app.post("/assignments/", response_model=schemas.AssignmentRead)
async def create_assignment(a: schemas.AssignmentCreate, db: AsyncSession=Depends(get_db), current_user = Depends(get_current_user)):
    assignment = await crud.create_assignment(db, a)
    return assignment

@app.post("/comments/", response_model=schemas.CommentRead)
async def add_comment(c: schemas.CommentCreate, db: AsyncSession=Depends(get_db), current_user = Depends(get_current_user)):
    comment = await crud.add_comment(db, c)
    return comment

@app.post("/tasks/{task_id}/dependencies/{depends_on_id}")
async def add_dependency(task_id: int, depends_on_id: int, db:AsyncSession=Depends(get_db), current_user = Depends(get_current_user)):
    if task_id == depends_on_id:
        raise HTTPException(status_code=400, detail="Task can not depend on itself")
    
    t1 = await crud.get_task(db, task_id=task_id)
    t2 = await crud.get_task(db, depends_on_id)
    if not t1 or not t2:
        raise HTTPException(status_code=404, detail="Task not found")
    dep = await crud.add_dependency(db, task_id=task_id, depends_on_task_id=depends_on_id)
    return {"status": "ok","dependency": {"task_id": dep.task_id, "depends_on_task_id": dep.depends_on_task_id}}


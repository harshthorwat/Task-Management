from sqlalchemy import select, update, insert
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Task, User, Assignment, TaskComment, TaskDependency, Team, Role, Permission, RolePermission, UserRole, RolePermission, RefreshToken
from app.schemas import TaskCreate, AssignmentCreate, CommentCreate, RoleCreate, PermissionCreate, UserRoleCreate, RefreshTokenCreate, RolePermissionCreate
from sqlalchemy.orm import selectinload

async def create_team(db: AsyncSession, name: str) -> Team:
    team = Team(name=name)
    db.add(team)
    await db.commit()
    await db.refresh(team)
    return team

async def create_user(db: AsyncSession, username: str, email: str, team_id:int = None) -> User:
    user = User(username=username, email=email, team_id=team_id)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

async def create_task(db: AsyncSession, task_in: TaskCreate) -> Task:
    task = Task(
        title=task_in.title,
        description=task_in.description,
        priority=task_in.priority,
        due_date=task_in.due_date,
        created_by=task_in.created_by
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task

async def get_task(db: AsyncSession, task_id: int):
    q = await db.execute(select(Task).where(Task.id == task_id))
    return q.scalars().first()

async def list_tasks(db: AsyncSession, skip: int=0, limit: int=50):
    q = await db.execute(select(Task).offset(skip).limit(limit))
    return q.scalars().all()

async def create_assignment(db: AsyncSession, a: AssignmentCreate, set_current=True):
    assignment = Assignment(
        task_id=a.task_id,
        assigned_to=a.assigned_to,
        assigned_by=a.assigned_by
    )
    db.add(assignment)
    await db.flush()
    if set_current:
        await db.execute(
            update(Task).where(Task.id==a.task_id).values(current_assignment_id=assignment.id)
        )
    await db.commit()
    await db.refresh(assignment)
    return assignment

async def add_comment(db: AsyncSession, c: CommentCreate):
    comment = TaskComment(task_id=c.task_id, author_id=c.author_id, body=c.body)
    db.add(comment)
    await db.commit()
    await db.refresh(comment)
    return comment

async def add_dependency(db: AsyncSession, task_id: int, depends_on_task_id: int):
    dep = TaskDependency(task_id=task_id, depends_on_task_id=depends_on_task_id)
    db.add(dep)
    await db.commit()
    return dep

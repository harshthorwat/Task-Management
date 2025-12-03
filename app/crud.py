from sqlalchemy import select, update, insert, and_, or_, func, not_, text, cast, String, literal
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Task, User, Assignment, TaskComment, TaskDependency, Team, Role, Permission, RolePermission, UserRole, RolePermission, RefreshToken
from app.schemas import TaskCreate, AssignmentCreate, CommentCreate, RoleCreate, PermissionCreate, UserRoleCreate, RefreshTokenCreate, RolePermissionCreate
from sqlalchemy.orm import selectinload
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError

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

async def list_users(db: AsyncSession, skip: int=0, limit: int=50):
    q = await db.execute(select(User).offset(skip).limit(limit))
    return q.scalars().all()

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

async def bulk_update_tasks(
    db: AsyncSession,
    items: List[Dict[str, Any]]
) -> Tuple[List[Task], List[int], List[Dict[str, Any]]]:

    allowed_fields = {
        "title", "description", "status", "priority",
        "due_date", "current_assignment_id", "deleted_at"
    }

    if not items:
        return ([], [], [])

    ids = [int(it["id"]) for it in items]

    q = await db.execute(select(Task).where(Task.id.in_(ids)))
    tasks = q.scalars().all()
    task_map = {t.id: t for t in tasks}

    assignment_ids_to_check = {
        int(it["current_assignment_id"])
        for it in items
        if it.get("current_assignment_id") is not None
    }
    existing_assignments = set()
    if assignment_ids_to_check:
        q2 = await db.execute(select(Assignment.id).where(Assignment.id.in_(list(assignment_ids_to_check))))
        existing_assignments = {row[0] for row in q2.all()}

    try:
        allowed_statuses = set(task_status_enum.enums)  # type: ignore[attr-defined]
    except Exception:
        allowed_statuses = {"unassigned", "assigned", "in_progress", "review", "completed", "abandoned"}

    results: List[Dict[str, Any]] = []
    updated_ids: List[int] = []
    not_found: List[int] = []

    for it in items:
        tid = int(it.get("id"))
        if tid not in task_map:
            not_found.append(tid)
            results.append({"id": tid, "ok": False, "error": "Task not found"})
            continue

        task = task_map[tid]

        if "priority" in it and it["priority"] is not None:
            try:
                p = int(it["priority"])
            except Exception:
                results.append({"id": tid, "ok": False, "error": "priority must be an integer"})
                continue
            if not (1 <= p <= 5):
                results.append({"id": tid, "ok": False, "error": "priority out of range (1..5)"})
                continue

        if "status" in it and it["status"] is not None:
            s = it["status"]
            if s not in allowed_statuses:
                results.append({"id": tid, "ok": False, "error": f"invalid status '{s}'"})
                continue

        if "current_assignment_id" in it and it["current_assignment_id"] is not None:
            ca = int(it["current_assignment_id"])
            if ca not in existing_assignments:
                results.append({"id": tid, "ok": False, "error": f"current_assignment_id {ca} does not exist"})
                continue

        changed = False
        for k, v in it.items():
            if k == "id":
                continue
            if k not in allowed_fields:
                continue
            if v is None:
                continue
            setattr(task, k, v)
            changed = True

        if changed:
            task.updated_at = datetime.now(timezone.utc)
            updated_ids.append(tid)

        results.append({"id": tid, "ok": True, "error": None})
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        db_msg = str(exc.orig) if hasattr(exc, "orig") else str(exc)
        new_results = []
        for r in results:
            if not r["ok"]:
                new_results.append(r)
            else:
                new_results.append({"id": r["id"], "ok": False, "error": f"DB integrity error: {db_msg}"})
        return ([], not_found, new_results)

    updated_tasks = []
    for tid in updated_ids:
        t = task_map.get(tid)
        if t:
            await db.refresh(t)
            updated_tasks.append(t)

    return (updated_tasks, not_found, results)

async def filter_tasks(
    db: AsyncSession,
    *,
    status: Optional[List[str]] = None,
    priority: Optional[List[int]] = None,
    assignee: Optional[List[str]] = None, 
    start_date: Optional[str] = None,      
    end_date: Optional[str] = None,
    title_search: Optional[str] = None, 
    logic: str = "AND",                    
    skip: int = 0,
    limit: int = 50
):
    filters = []

    if status:
        filters.append(Task.status.in_(status))

    if priority:
        filters.append(Task.priority.in_(priority))

    if assignee:
        filters.append(Task.current_assignment_id.isnot(None))
        filters.append(
            Assignment.assigned_to.in_(assignee)
        )

    if start_date:
        filters.append(Task.created_at >= start_date)

    if end_date:
        filters.append(Task.created_at <= end_date)

    if title_search:
        like = f"%{title_search.lower()}%"
        filters.append(Task.title.ilike(like))

    if logic.upper() == "OR":
        combined = or_(*filters) if filters else None
    else:
        combined = and_(*filters) if filters else None

    stmt = (
        select(Task)
        .outerjoin(Assignment, Assignment.id == Task.current_assignment_id)
    )

    if combined is not None:
        stmt = stmt.where(combined)

    stmt = stmt.order_by(Task.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(stmt)
    return result.scalars().all()

async def get_task_distribution(
    db: AsyncSession,
    group_by: str = "status",
    skip: int = 0,
    limit: int = 100
) -> List[Tuple[Optional[str], int]]:
    group_by = (group_by or "status").lower()

    if group_by == "status":
        stmt = (
            select(Task.status.label("key"), func.count(Task.id))
            .group_by(Task.status)
            .order_by(func.count(Task.id).desc())
        )

    elif group_by == "priority":
        stmt = (
            select(
                func.coalesce(cast(Task.priority, String), literal("unknown")).label("key"),
                func.count(Task.id)
            )
            .group_by(cast(Task.priority, String))
            .order_by(func.count(Task.id).desc())
        )

    elif group_by == "team":
        stmt = (
            select(Team.name.label("key"), func.count(Task.id))
            .select_from(Task)
            .join(User, User.id == Task.created_by, isouter=True)
            .join(Team, Team.id == User.team_id, isouter=True)
            .group_by(Team.name)
            .order_by(func.count(Task.id).desc())
        )

    elif group_by == "assignee":
        stmt = (
            select(User.username.label("key"), func.count(Task.id))
            .select_from(Task)
            .outerjoin(Assignment, Assignment.id == Task.current_assignment_id)
            .outerjoin(User, User.id == Assignment.assigned_to)
            .group_by(User.username)
            .order_by(func.count(Task.id).desc())
        )

    else:
        raise ValueError("unsupported group_by value")

    stmt = stmt.offset(skip).limit(limit)
    res = await db.execute(stmt)
    rows = res.all()
    return [(str(r[0]) if r[0] is not None else None, int(r[1])) for r in rows]

async def get_overdue_tasks_per_user(
    db: AsyncSession,
    as_of: Optional[datetime] = None,
    include_tasks: bool = False,
    skip: int = 0,
    limit: int = 100
):
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    as_of = as_of or today

    try:
        enum_vals = set(task_status_enum.enums)  # type: ignore[attr-defined]
    except Exception:
        enum_vals = {"unassigned", "assigned", "in_progress", "review", "completed", "abandoned"}

    finished_statuses = {"completed", "abandoned"} & enum_vals
    if not finished_statuses:
        finished_statuses = {"completed", "abandoned"}

    stmt = (
        select(
            User.id.label("user_id"),
            User.username.label("username"),
            func.count(Task.id).label("overdue_count")
        )
        .select_from(Task)
        .join(Assignment, Assignment.id == Task.current_assignment_id)
        .join(User, User.id == Assignment.assigned_to)
        .where(
            and_(
                Task.due_date.isnot(None),
                Task.due_date < as_of,
                Task.status.notin_(finished_statuses)
            )
        )
        .group_by(User.id, User.username)
        .order_by(func.count(Task.id).desc())
        .offset(skip)
        .limit(limit)
    )

    rowres = await db.execute(stmt)
    rows = rowres.all()

    results = []
    user_ids = [r.user_id for r in rows]

    tasks_map = {}
    if include_tasks and user_ids:
        q = (
            select(
                Task.id,
                Task.title,
                Task.due_date,
                Task.priority,
                Task.status,
                Task.created_by,
                Assignment.assigned_to
            )
            .join(Assignment, Assignment.id == Task.current_assignment_id)
            .where(
                and_(
                    Assignment.assigned_to.in_(user_ids),
                    Task.due_date.isnot(None),
                    Task.due_date < as_of,
                    Task.status.notin_(finished_statuses)
                )
            )
            .order_by(Assignment.assigned_to, Task.due_date.asc())
        )

        res = await db.execute(q)
        for r in res.all():
            uid = r.assigned_to
            tasks_map.setdefault(uid, []).append({
                "id": r.id,
                "title": r.title,
                "due_date": r.due_date,
                "priority": r.priority,
                "status": r.status,
                "created_by": r.created_by
            })

    for r in rows:
        uid = r.user_id
        results.append({
            "user_id": uid,
            "username": r.username,
            "overdue_count": int(r.overdue_count),
            "overdue_tasks": tasks_map.get(uid) if include_tasks else None
        })

    return results

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

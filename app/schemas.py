from __future__ import annotations
from typing import Optional, List
from pydantic import BaseModel, Field, EmailStr
from uuid import UUID
from datetime import datetime

class BaseReadModel(BaseModel):
    model_config = {"from_attributes": True}

class TeamCreate(BaseModel):
    name: str

class TeamRead(BaseReadModel):
    id: int
    name: str
    created_at: datetime

class UserCreate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    team_id: Optional[int] = None
    password: str

class UserRead(BaseReadModel):
    id: UUID
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    team_id: Optional[int] = None
    is_active: bool
    is_superuser: bool
    last_login: Optional[datetime] = None
    created_at: datetime

class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    priority: Optional[int] = Field(1, ge=1, le=5)
    due_date: Optional[datetime] = None
    created_by: Optional[UUID] = None

class TaskRead(BaseReadModel):
    id: int
    title: str
    description: Optional[str] = None
    status: str
    priority: int
    due_date: Optional[datetime] = None
    updated_at: datetime
    created_at: datetime
    created_by: Optional[UUID] = None

class AssignmentCreate(BaseModel):
    task_id: int
    assigned_to: UUID
    assigned_by: Optional[UUID] = None
    delegated: Optional[bool] = False
    notes: Optional[str] = None

class AssignmentRead(BaseReadModel):
    id: int
    task_id: int
    assigned_to: UUID
    assigned_by: Optional[UUID] = None
    assigned_at: datetime
    delegated: bool
    notes: Optional[str] = None

class CommentCreate(BaseModel):
    task_id: int
    author_id: Optional[UUID] = None
    body: str

class CommentRead(BaseReadModel):
    id: int
    task_id: int
    author_id: Optional[UUID] = None
    body: str
    created_at: datetime
    edited_at: Optional[datetime] = None

class DependencyCreate(BaseModel):
    task_id: int
    depends_on_task_id: int

class DependencyRead(BaseReadModel):
    task_id: int
    depends_on_task_id: int

class RoleCreate(BaseModel):
    name: str
    description: Optional[str] = None

class RoleRead(BaseReadModel):
    id: int
    name: str
    description: Optional[str] = None

class PermissionCreate(BaseModel):
    name: str
    description: Optional[str] = None

class PermissionRead(BaseReadModel):
    id: int
    name: str
    description: Optional[str] = None

class UserRoleCreate(BaseModel):
    user_id: UUID
    role_id: int

class RolePermissionCreate(BaseModel):
    role_id: int
    permission_id: int

class RefreshTokenCreate(BaseModel):
    user_id: UUID
    jti: UUID
    expires_at: datetime

class RefreshTokenRead(BaseReadModel):
    id: int
    user_id: UUID
    jti: UUID
    issued_at: datetime
    expires_at: datetime
    revoked: bool

class BulkTaskUpdateItem(BaseModel):
    id: int
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[int] = Field(None, ge=1, le=5)
    due_date: Optional[datetime] = None
    current_assignment_id: Optional[int] = None
    deleted_at: Optional[datetime] = None

class BulkTaskUpdateRequest(BaseModel):
    items: List[BulkTaskUpdateItem]

class BulkTaskUpdateResultItem(BaseModel):
    id: int
    ok: bool
    error: Optional[str] = None

class BulkTaskUpdateResponse(BaseModel):
    updated: List[int]
    not_found: List[int]
    results: List[BulkTaskUpdateResultItem]

class TaskFilter(BaseModel):
    status: Optional[List[str]] = None
    priority: Optional[List[int]] = None
    assignee: Optional[List[str]] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    title_search: Optional[str] = None
    logic: Optional[str] = "AND"
    skip: int = 0
    limit: int = 50

class DistributionItem(BaseModel):
    key: Optional[str]  
    count: int

class TaskBrief(BaseModel):
    id: int
    title: str
    due_date: Optional[datetime]
    priority: Optional[int]
    status: str
    created_by: Optional[UUID]

class OverdueUserItem(BaseModel):
    user_id: UUID
    username: Optional[str]
    overdue_count: int
    overdue_tasks: Optional[List[TaskBrief]] = None

class TaskDistributionResponse(BaseModel):
    group_by: str
    items: List[DistributionItem]

class OverdueByUserResponse(BaseModel):
    as_of: datetime
    users: List[OverdueUserItem]

import uuid
from sqlalchemy import (
    Column, String, Integer, BigInteger, Boolean, ForeignKey,
    Text, TIMESTAMP, CheckConstraint, UniqueConstraint, Index, text
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID, ENUM
from sqlalchemy.orm import relationship
from app.database import Base
from sqlalchemy.sql import func

task_status_enum = ENUM(
    'unassigned', 'assigned', 'in_progress', 'review', 'completed', 'abandoned',
    name='task_status', create_type=True
)

class Team(Base):
    __tablename__ = "teams"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)


class User(Base):
    __tablename__ = "users"
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(100), unique=True, index=True, nullable=True)
    email = Column(String(255), unique=True, index=True, nullable=True)
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="SET NULL"), nullable=True)
    hashed_password = Column(Text, nullable=True)
    is_active = Column(Boolean, server_default=text('true'), nullable=False)
    is_superuser = Column(Boolean, server_default=text('false'), nullable=False)
    last_login = Column(TIMESTAMP(timezone=True), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    team = relationship("Team", backref="users")


class Task(Base):
    __tablename__ = "tasks"
    id = Column(BigInteger, primary_key=True, index=True)
    title = Column(String(1000), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(task_status_enum, nullable=False, server_default='unassigned')
    priority = Column(Integer, nullable=False, server_default=text('1'))
    due_date = Column(TIMESTAMP(timezone=True), nullable=True)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    created_by = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    current_assignment_id = Column(BigInteger, ForeignKey("assignment.id", ondelete="SET NULL"), nullable=True)
    deleted_at = Column(TIMESTAMP(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint('priority BETWEEN 1 AND 5', name='priority_range_check'),
        Index('idx_tasks_status', 'status'),
        Index('idx_tasks_priority', 'priority'),
        Index('idx_tasks_duedate', 'due_date'),
    )

    creator = relationship("User", foreign_keys=[created_by])

    current_assignment = relationship(
        "Assignment",
        foreign_keys=[current_assignment_id],
        post_update=True,
        uselist=False,
        viewonly=False
    )


class Assignment(Base):
    __tablename__ = "assignment"
    id = Column(BigInteger, primary_key=True, index=True)
    task_id = Column(BigInteger, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    assigned_to = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=False)
    assigned_by = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    assigned_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    delegated = Column(Boolean, server_default=text('false'), nullable=False)
    notes = Column(Text, nullable=True)

    task = relationship(
        "Task",
        backref="assignments",
        foreign_keys=[task_id]
    )

    assignee = relationship("User", foreign_keys=[assigned_to])
    assigner = relationship("User", foreign_keys=[assigned_by])

    __table_args__ = (
        Index('idx_assignment_task', 'task_id'),
        Index('idx_assignment_assigned_to', 'assigned_to'),
    )


class TaskComment(Base):
    __tablename__ = 'task_comments'
    id = Column(BigInteger, primary_key=True, index=True)
    task_id = Column(BigInteger, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    author_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    body = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    edited_at = Column(TIMESTAMP(timezone=True), nullable=True)

    __table_args__ = (
        Index('idx_comments_task', 'task_id'),
    )


class TaskDependency(Base):
    __tablename__ = "task_dependencies"
    task_id = Column(BigInteger, ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True)
    depends_on_task_id = Column(BigInteger, ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True)

    __table_args__ = (
        CheckConstraint("task_id <> depends_on_task_id", name="no_self_dependency"),
    )


class Role(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)


class Permission(Base):
    __tablename__ = "permissions"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)


class UserRole(Base):
    __tablename__ = "user_roles"
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role_id = Column(Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)


class RolePermission(Base):
    __tablename__ = "role_permissions"
    role_id = Column(Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
    permission_id = Column(Integer, ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True)


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    id = Column(BigInteger, primary_key=True)
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    jti = Column(PGUUID(as_uuid=True), nullable=False)
    issued_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(TIMESTAMP(timezone=True), nullable=False)
    revoked = Column(Boolean, nullable=False, server_default=text('false'))

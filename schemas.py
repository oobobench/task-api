from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class TaskStatus(str, Enum):
    todo = "todo"
    in_progress = "in_progress"
    done = "done"


class SortOrder(str, Enum):
    asc = "asc"
    desc = "desc"


class TaskBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    status: TaskStatus = TaskStatus.todo


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    status: Optional[TaskStatus] = None


class Task(TaskBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    user_id: int


class PaginatedTasks(BaseModel):
    items: List[Task]
    total: int
    page: int
    per_page: int
    pages: int


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class User(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class WebhookEvent(str, Enum):
    task_created = "task.created"
    task_updated = "task.updated"
    task_deleted = "task.deleted"
    task_status_changed = "task.status_changed"


class WebhookCreate(BaseModel):
    url: str = Field(..., min_length=1, max_length=2048)
    events: List[WebhookEvent] = Field(..., min_length=1)


class Webhook(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    url: str
    events: List[WebhookEvent]
    active: bool
    created_at: datetime


class WebhookWithSecret(Webhook):
    secret: str


class WebhookDelivery(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    webhook_id: int
    event: str
    status: str
    attempts: int
    response_status: Optional[int]
    error: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]

from datetime import datetime, timezone
from math import ceil
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

import cache
from database import get_db
from models import Task as TaskModel
from models import User as UserModel
from schemas import PaginatedTasks, SortOrder, Task, TaskCreate, TaskStatus, TaskUpdate
from security import get_current_user

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _get_owned_or_404(db: Session, task_id: int, user: UserModel) -> TaskModel:
    task = db.get(TaskModel, task_id)
    if task is None or task.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task


def _json_response(body: str, cache_status: str, max_age: int, status_code: int = 200) -> Response:
    return Response(
        content=body,
        media_type="application/json",
        status_code=status_code,
        headers={
            "X-Cache": cache_status,
            "Cache-Control": f"private, max-age={max_age}",
        },
    )


@router.get("", response_model=PaginatedTasks)
async def list_tasks(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: Optional[TaskStatus] = None,
    search: Optional[str] = None,
    sort: SortOrder = SortOrder.desc,
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_user),
) -> Response:
    version = await cache.get_list_version(user.id)
    params = {
        "page": page,
        "per_page": per_page,
        "status": status.value if status else None,
        "search": search,
        "sort": sort.value,
    }
    key = cache.list_key(user.id, version, params)

    cached = await cache.get(key)
    if cached is not None:
        return _json_response(cached, "HIT", cache.LIST_CACHE_TTL)

    filters = [TaskModel.user_id == user.id]
    if status is not None:
        filters.append(TaskModel.status == status.value)
    if search:
        pattern = f"%{search}%"
        filters.append(
            or_(TaskModel.title.ilike(pattern), TaskModel.description.ilike(pattern))
        )

    total = db.scalar(select(func.count()).select_from(TaskModel).where(*filters)) or 0

    order_col = (
        TaskModel.created_at.asc() if sort == SortOrder.asc else TaskModel.created_at.desc()
    )
    stmt = (
        select(TaskModel)
        .where(*filters)
        .order_by(order_col, TaskModel.id.asc() if sort == SortOrder.asc else TaskModel.id.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    items = list(db.scalars(stmt).all())
    pages = ceil(total / per_page) if total else 0
    payload = PaginatedTasks(
        items=[Task.model_validate(t) for t in items],
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )
    body = payload.model_dump_json()
    await cache.setex(key, cache.LIST_CACHE_TTL, body)
    return _json_response(body, "MISS", cache.LIST_CACHE_TTL)


@router.post("", response_model=Task, status_code=status.HTTP_201_CREATED)
async def create_task(
    payload: TaskCreate,
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_user),
) -> TaskModel:
    task = TaskModel(
        title=payload.title,
        description=payload.description,
        status=payload.status.value,
        created_at=datetime.now(timezone.utc),
        user_id=user.id,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    await cache.bump_list_version(user.id)
    return task


@router.get("/{task_id}", response_model=Task)
async def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_user),
) -> Response:
    key = cache.task_key(user.id, task_id)
    cached = await cache.get(key)
    if cached is not None:
        return _json_response(cached, "HIT", cache.TASK_CACHE_TTL)

    task = _get_owned_or_404(db, task_id, user)
    body = Task.model_validate(task).model_dump_json()
    await cache.setex(key, cache.TASK_CACHE_TTL, body)
    return _json_response(body, "MISS", cache.TASK_CACHE_TTL)


@router.put("/{task_id}", response_model=Task)
async def update_task(
    task_id: int,
    payload: TaskUpdate,
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_user),
) -> TaskModel:
    task = _get_owned_or_404(db, task_id, user)
    updates = payload.model_dump(exclude_unset=True)
    for key, value in updates.items():
        if key == "status" and isinstance(value, TaskStatus):
            value = value.value
        setattr(task, key, value)
    db.commit()
    db.refresh(task)
    await cache.delete(cache.task_key(user.id, task_id))
    await cache.bump_list_version(user.id)
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_user),
) -> None:
    task = _get_owned_or_404(db, task_id, user)
    db.delete(task)
    db.commit()
    await cache.delete(cache.task_key(user.id, task_id))
    await cache.bump_list_version(user.id)

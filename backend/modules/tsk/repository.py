"""Repository helpers for TSK-01..TSK-05."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.modules.tsk.models import Task, TaskDependency


class TskRepository:
    """Data-access layer for tasks and dependencies."""

    def list_tasks(self, session: Session, exam_id: str) -> list[Task]:
        stmt = (
            select(Task)
            .where(Task.exam_id == exam_id)
            .order_by(Task.due_date, Task.title)
        )
        return list(session.scalars(stmt))

    def get_task(self, session: Session, exam_id: str, task_id: str) -> Task | None:
        stmt = select(Task).where(Task.exam_id == exam_id, Task.id == task_id)
        return session.scalar(stmt)

    def list_dependencies(self, session: Session, exam_id: str) -> list[TaskDependency]:
        stmt = select(TaskDependency).where(TaskDependency.exam_id == exam_id)
        return list(session.scalars(stmt))

    def get_dependency(
        self, session: Session, exam_id: str, dependency_id: str
    ) -> TaskDependency | None:
        stmt = select(TaskDependency).where(
            TaskDependency.exam_id == exam_id, TaskDependency.id == dependency_id
        )
        return session.scalar(stmt)

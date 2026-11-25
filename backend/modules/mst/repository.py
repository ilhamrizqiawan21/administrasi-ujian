"""Repository layer for MST models (scoped by institution_id, no commits)."""

from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from backend.modules.mst.models import (
    Enrollment,
    Room,
    SchoolClass,
    Staff,
    Student,
    Subject,
    TeachingAssignment,
)


class MstRepository:
    """Scoped data access for master entities."""

    def list_students(
        self,
        session: Session,
        institution_id: str,
        *,
        query: str = "",
        active_only: bool = False,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[Student], int]:
        stmt = select(Student).where(Student.institution_id == institution_id)
        if active_only:
            stmt = stmt.where(Student.active == 1)
        if query.strip():
            like = f"%{query.strip()}%"
            stmt = stmt.where(
                or_(
                    Student.full_name.ilike(like),
                    Student.nis.ilike(like),
                    Student.nisn.ilike(like),
                )
            )
        total = session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        rows = list(
            session.scalars(
                stmt.order_by(Student.full_name.asc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        return rows, int(total)

    def get_student(
        self, session: Session, institution_id: str, student_id: str
    ) -> Student | None:
        return session.scalar(
            select(Student).where(
                Student.id == student_id, Student.institution_id == institution_id
            )
        )

    def get_student_by_nis(
        self, session: Session, institution_id: str, nis: str
    ) -> Student | None:
        return session.scalar(
            select(Student).where(
                Student.institution_id == institution_id, Student.nis == nis
            )
        )

    def list_all_students(self, session: Session, institution_id: str) -> list[Student]:
        return list(
            session.scalars(
                select(Student)
                .where(Student.institution_id == institution_id)
                .order_by(Student.full_name.asc())
            )
        )

    def count_student_references(self, session: Session, student_id: str) -> int:
        count = session.scalar(
            select(func.count())
            .select_from(Enrollment)
            .where(Enrollment.student_id == student_id)
        )
        return int(count or 0)

    def list_staff(
        self,
        session: Session,
        institution_id: str,
        *,
        query: str = "",
        active_only: bool = False,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[Staff], int]:
        stmt = select(Staff).where(Staff.institution_id == institution_id)
        if active_only:
            stmt = stmt.where(Staff.active == 1)
        if query.strip():
            like = f"%{query.strip()}%"
            stmt = stmt.where(
                or_(
                    Staff.full_name.ilike(like),
                    Staff.staff_code.ilike(like),
                    Staff.nip.ilike(like),
                )
            )
        total = session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        rows = list(
            session.scalars(
                stmt.order_by(Staff.full_name.asc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        return rows, int(total)

    def get_staff(
        self, session: Session, institution_id: str, staff_id: str
    ) -> Staff | None:
        return session.scalar(
            select(Staff).where(
                Staff.id == staff_id, Staff.institution_id == institution_id
            )
        )

    def get_staff_by_code(
        self, session: Session, institution_id: str, staff_code: str
    ) -> Staff | None:
        return session.scalar(
            select(Staff).where(
                Staff.institution_id == institution_id, Staff.staff_code == staff_code
            )
        )

    def list_all_staff(self, session: Session, institution_id: str) -> list[Staff]:
        return list(
            session.scalars(
                select(Staff)
                .where(Staff.institution_id == institution_id)
                .order_by(Staff.staff_code.asc())
            )
        )

    def count_staff_references(self, session: Session, staff_id: str) -> int:
        count = session.scalar(
            select(func.count())
            .select_from(TeachingAssignment)
            .where(TeachingAssignment.staff_id == staff_id)
        )
        return int(count or 0)

    def list_classes(
        self, session: Session, institution_id: str, *, year_id: str | None = None
    ) -> list[SchoolClass]:
        stmt = select(SchoolClass).where(SchoolClass.institution_id == institution_id)
        if year_id:
            stmt = stmt.where(SchoolClass.year_id == year_id)
        return list(session.scalars(stmt.order_by(SchoolClass.name.asc())))

    def get_class(
        self, session: Session, institution_id: str, class_id: str
    ) -> SchoolClass | None:
        return session.scalar(
            select(SchoolClass).where(
                SchoolClass.id == class_id, SchoolClass.institution_id == institution_id
            )
        )

    def list_enrollments(
        self, session: Session, institution_id: str, *, year_id: str | None = None
    ) -> list[Enrollment]:
        stmt = select(Enrollment).where(Enrollment.institution_id == institution_id)
        if year_id:
            stmt = stmt.where(Enrollment.year_id == year_id)
        return list(session.scalars(stmt))

    def get_enrollment(
        self, session: Session, institution_id: str, student_id: str, year_id: str
    ) -> Enrollment | None:
        return session.scalar(
            select(Enrollment).where(
                Enrollment.institution_id == institution_id,
                Enrollment.student_id == student_id,
                Enrollment.year_id == year_id,
            )
        )

    def list_subjects(
        self, session: Session, institution_id: str, *, query: str = ""
    ) -> list[Subject]:
        stmt = select(Subject).where(Subject.institution_id == institution_id)
        if query.strip():
            like = f"%{query.strip()}%"
            stmt = stmt.where(or_(Subject.code.ilike(like), Subject.name.ilike(like)))
        return list(session.scalars(stmt.order_by(Subject.code.asc())))

    def get_subject(
        self, session: Session, institution_id: str, subject_id: str
    ) -> Subject | None:
        return session.scalar(
            select(Subject).where(
                Subject.id == subject_id, Subject.institution_id == institution_id
            )
        )

    def get_subject_by_code(
        self, session: Session, institution_id: str, code: str
    ) -> Subject | None:
        return session.scalar(
            select(Subject).where(
                Subject.institution_id == institution_id, Subject.code == code
            )
        )

    def list_teaching_assignments(
        self, session: Session, institution_id: str
    ) -> list[TeachingAssignment]:
        return list(
            session.scalars(
                select(TeachingAssignment).where(
                    TeachingAssignment.institution_id == institution_id
                )
            )
        )

    def get_teaching_assignment(
        self, session: Session, institution_id: str, ta_id: str
    ) -> TeachingAssignment | None:
        return session.scalar(
            select(TeachingAssignment).where(
                TeachingAssignment.id == ta_id,
                TeachingAssignment.institution_id == institution_id,
            )
        )

    def list_rooms(
        self, session: Session, institution_id: str, *, query: str = ""
    ) -> list[Room]:
        stmt = select(Room).where(Room.institution_id == institution_id)
        if query.strip():
            like = f"%{query.strip()}%"
            stmt = stmt.where(or_(Room.code.ilike(like), Room.name.ilike(like)))
        return list(session.scalars(stmt.order_by(Room.code.asc())))

    def get_room(
        self, session: Session, institution_id: str, room_id: str
    ) -> Room | None:
        return session.scalar(
            select(Room).where(
                Room.id == room_id, Room.institution_id == institution_id
            )
        )

    def get_room_by_code(
        self, session: Session, institution_id: str, code: str
    ) -> Room | None:
        return session.scalar(
            select(Room).where(Room.institution_id == institution_id, Room.code == code)
        )

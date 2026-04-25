from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.report_export import ReportExport


class ReportRepository:
    def __init__(self, session: Session):
        self.session = session

    def create_export(self, **values) -> ReportExport:  # type: ignore[no-untyped-def]
        export = ReportExport(**values)
        self.session.add(export)
        self.session.flush()
        return export


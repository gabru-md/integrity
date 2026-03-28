import json
from datetime import date, datetime
from typing import List, Optional

from gabru.db.db import DB
from gabru.db.service import CRUDService
from model.report import Report


class ReportService(CRUDService[Report]):
    def __init__(self):
        super().__init__("reports", DB("rasbhari"), user_scoped=True)

    @staticmethod
    def _json_default(value):
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        if hasattr(value, "dict"):
            return value.dict()
        raise TypeError(f"Object of type {value.__class__.__name__} is not JSON serializable")

    def _create_table(self):
        if self.db.conn:
            with self.db.conn.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS reports (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL,
                        report_type VARCHAR(32) NOT NULL,
                        anchor_date VARCHAR(20) NOT NULL,
                        period_start TIMESTAMP NOT NULL,
                        period_end TIMESTAMP NOT NULL,
                        generated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        title VARCHAR(255) NOT NULL,
                        integrity_score INTEGER NOT NULL DEFAULT 0,
                        headline TEXT NOT NULL DEFAULT '',
                        observations JSONB NOT NULL DEFAULT '[]'::jsonb,
                        metrics JSONB NOT NULL DEFAULT '{}'::jsonb,
                        sections JSONB NOT NULL DEFAULT '{}'::jsonb
                    )
                """)
                cursor.execute("""
                    CREATE UNIQUE INDEX IF NOT EXISTS reports_type_anchor_idx
                    ON reports (user_id, report_type, anchor_date)
                """)
                self.db.conn.commit()

    def _to_tuple(self, report: Report) -> tuple:
        return (
            report.user_id,
            report.report_type,
            report.anchor_date,
            report.period_start,
            report.period_end,
            report.generated_at,
            report.title,
            report.integrity_score,
            report.headline,
            json.dumps(report.observations, default=self._json_default),
            json.dumps(report.metrics, default=self._json_default),
            json.dumps(report.sections, default=self._json_default),
        )

    def _to_object(self, row: tuple) -> Report:
        return Report(
            id=row[0],
            user_id=row[1],
            report_type=row[2],
            anchor_date=row[3],
            period_start=row[4],
            period_end=row[5],
            generated_at=row[6],
            title=row[7],
            integrity_score=row[8],
            headline=row[9] or "",
            observations=row[10] or [],
            metrics=row[11] or {},
            sections=row[12] or {},
        )

    def _get_columns_for_insert(self) -> List[str]:
        return [
            "user_id", "report_type", "anchor_date", "period_start", "period_end", "generated_at",
            "title", "integrity_score", "headline", "observations", "metrics", "sections"
        ]

    def _get_columns_for_update(self) -> List[str]:
        return self._get_columns_for_insert()

    def _get_columns_for_select(self) -> List[str]:
        return [
            "id", "user_id", "report_type", "anchor_date", "period_start", "period_end", "generated_at",
            "title", "integrity_score", "headline", "observations", "metrics", "sections"
        ]

    def get_by_type_and_anchor(self, user_id: int, report_type: str, anchor_date: str) -> Optional[Report]:
        reports = self.find_all(filters={"user_id": user_id, "report_type": report_type, "anchor_date": anchor_date})
        return reports[0] if reports else None

    def upsert(self, report: Report) -> int:
        existing = self.get_by_type_and_anchor(report.user_id, report.report_type, report.anchor_date)
        if existing:
            report.id = existing.id
            self.update(report)
            return existing.id
        return self.create(report)

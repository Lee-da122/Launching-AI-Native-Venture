from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional


@dataclass
class CompetitionRecord:
    name: str
    organizer: Optional[str]
    deadline: Optional[str]
    deadline_date: Optional[date]
    description: str
    category: Optional[str]
    eligibility: Optional[str]
    participation_type: Optional[str]
    source_name: str
    source_url: str
    external_id: str
    fetched_at: datetime
    application_start_date: Optional[date] = None
    original_deadline_text: Optional[str] = None
    is_active: bool = True

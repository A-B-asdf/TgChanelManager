from pydantic import BaseModel

class ScheduleSettings(BaseModel):
    cron: str
    timezone: str = "Europe/Moscow"
    active: bool = True
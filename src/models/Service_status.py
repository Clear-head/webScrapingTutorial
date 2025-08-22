from datetime import datetime
from enum import Enum
from typing import Optional, List

from pydantic import BaseModel, Field


class ScrapStatus(Enum):
    WAITING = "WAITING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SCHEDULED = "SCHEDULED"


class SystemStatus(Enum):
    NORMAL = "NORMAL"
    WARNING = "WARNING"
    ERROR = "ERROR"


class ScrapingStatus(BaseModel):
    state: ScrapStatus = Field(default=ScrapStatus.WAITING, description="현재 상태")
    progress: int = Field(default=0, description="진행률", ge=0, le=100)
    current_site: str = Field(default="대기 중", description="현재 처리 중인 사이트")

    started_time: Optional[datetime] = Field(description="시작 시간")
    updated_time: Optional[datetime] = Field(description="마지막 작업 완료 시간")
    completed_time: Optional[datetime] = Field(description="완료 시간")

    total_scraped: int = Field(default=0, description="총 수집된 항목 수", ge=0)
    total_saved: int = Field(default=0, description="실제 저장된 항목 수", ge=0)
    duplicates_skipped: int = Field(default=0, description="중복 항목 수", ge=0)

    error_message: Optional[str] = Field(None, description="에러 메시지")
    failed_sites: List[str] = Field(default_factory=list, description="실패한 사이트 목록")

    next_run: Optional[datetime] = Field(None, description="다음 실행 예정 시간")


    class Config:
        use_enum_values = True
        json_encoders = {datetime: lambda v: v.isoformat() if v else None}


    def update_timestamp(self) -> None:
        self.updated_time = datetime.now()


    def start(self, site_name = "start"):
        self.state = ScrapingStatus.RUNNING
        self.progress = 0
        self.current_site = site_name
        self.started_time = datetime.now()
        self.completed_time = datetime.now()
        self.total_scraped = 0
        self.total_saved = 0
        self.duplicates_skipped = 0
        self.error_message = None
        self.failed_sites = []
        self.update_timestamp()


    def update_progress(self, progress, current_site):
        self.progress = max(0, min(100, progress))
        if current_site:
            self.current_site = current_site
        self.update_timestamp()


    def add_data(self, scraped, saved, duplicates = 0):
        self.total_scraped += scraped
        self.total_saved += saved
        self.duplicates_skipped += duplicates
        self.update_timestamp()


    def add_failed_site(self, site_name):
        if site_name not in self.failed_sites:
            self.failed_sites.append(site_name)
        self.update_timestamp()


    def complete(self):
        self.state = ScrapingStatus.COMPLETED
        self.progress = 100
        self.completed_time = datetime.now()
        self.current_site = f"Finished {self.current_site} saved : {self.total_saved}"
        self.update_timestamp()


    def fail(self, error_message):
        self.state = ScrapingStatus.FAILED
        self.error_message = error_message
        self.completed_time = datetime.now()
        self.current_site = f"Failed {self.current_site}"
        self.update_timestamp()


    def schedule_next_run(self, next_time):
        self.state = ScrapingStatus.SCHEDULED
        self.next_run = next_time
        self.update_timestamp()



    @property
    def is_running(self):
        return self.state is ScrapingStatus.RUNNING


    @property
    def doing_second(self):
        if not self.started_time:
            return -1
        end_time = datetime.now() or self.completed_time
        return end_time - self.started_time

    @property
    def success_rate(self):
        if self.total_scraped == 0:
            return 0.0
        return round((self.total_saved / self.total_scraped) * 100, 2)


    def to_dict(self):
        return {
            "state": self.state,
            "progress": self.progress,
            "current_site": self.current_site,
            "started_time": self.started_time.isoformat(),
            "updated_time": self.updated_time.isoformat(),
            "completed_time": self.completed_time.isoformat(),
            "total_scraped": self.total_scraped,
            "total_saved": self.total_saved,
            "duplicates_skipped": self.duplicates_skipped,
            "error_message": self.error_message,
            "failed_sites": self.failed_sites,
            "next_run": self.next_run,
            "doing_second": self.doing_second,
            "success_rate": self.success_rate,
        }


    @classmethod
    def from_dict(cls, data):
        processed_data = {}

        for key, value in data.items():
            if isinstance(value, bytes):
                value = value.decode('utf-8')

            if key in ["progress", "total_scraped", "total_saved", "duplicates_skipped"]:
                processed_data[key] = int(value) if value else 0
            elif key in ["started_at", "completed_at", "updated_at", "next_run_at"]:
                processed_data[key] = datetime.fromisoformat(value) if value else None
            elif key == "state":
                processed_data[key] = ScrapStatus(value) if value else ScrapStatus.WAITING
            elif key == "failed_sites":
                processed_data[key] = value.split(",") if value else []
            elif key == "error_message":
                processed_data[key] = value if value else None
            else:
                processed_data[key] = value

        # computed property 제거
        processed_data.pop("duration_seconds", None)
        processed_data.pop("success_rate", None)

        return cls(**processed_data)


#   todo: watch here


class ScrapingResult(BaseModel):
    """개별 사이트 스크래핑 결과"""

    site_name: str = Field(..., description="사이트 이름")
    success: bool = Field(..., description="성공 여부")
    scraped_count: int = Field(default=0, description="수집된 항목 수", ge=0)
    saved_count: int = Field(default=0, description="저장된 항목 수", ge=0)
    duplicates_count: int = Field(default=0, description="중복 항목 수", ge=0)
    duration_seconds: float = Field(default=0.0, description="소요 시간(초)", ge=0)
    error_message: Optional[str] = Field(None, description="에러 메시지")


    @property
    def success_rate(self) -> float:
        """성공률"""
        if self.scraped_count == 0:
            return 0.0
        return (self.saved_count / self.scraped_count) * 100




class SystemHealth(BaseModel):
    status: SystemStatus = Field(default=SystemStatus.NORMAL, description="시스템 상태")
    redis_connected: bool = Field(default=False, description="Redis 연결 상태")
    last_scraping: Optional[datetime] = Field(None, description="마지막 스크래핑 시간")
    next_scraping: Optional[datetime] = Field(None, description="다음 스크래핑 시간")

    total_contests: int = Field(default=0, description="총 공모전 수", ge=0)
    active_contests: int = Field(default=0, description="진행 중 공모전 수", ge=0)
    expired_contests: int = Field(default=0, description="마감 공모전 수", ge=0)

    uptime_seconds: int = Field(default=0, description="가동 시간(초)", ge=0)
    memory_usage_mb: float = Field(default=0.0, description="메모리 사용량(MB)", ge=0)

    recent_errors: List[str] = Field(default_factory=list, description="최근 에러 목록")


    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


    def add_error(self, error_message: str, max_errors: int = 10) -> None:
        """에러 추가 (최대 개수 제한)"""
        timestamp = datetime.now().strftime("%m/%d %H:%M")
        self.recent_errors.insert(0, f"[{timestamp}] {error_message}")
        if len(self.recent_errors) > max_errors:
            self.recent_errors = self.recent_errors[:max_errors]


    def update_redis_status(self, connected: bool) -> None:
        """Redis 연결 상태 업데이트"""
        self.redis_connected = connected
        if not connected:
            self.status = SystemStatus.ERROR
            self.add_error("Redis 연결 실패")

    def update_contest_stats(self, total: int, active: int, expired: int) -> None:
        """공모전 통계 업데이트"""
        self.total_contests = total
        self.active_contests = active
        self.expired_contests = expired


    def calculate_status(self) -> SystemStatus:
        """전체 상태 계산"""
        if not self.redis_connected:
            return SystemStatus.ERROR

        if self.recent_errors:
            return SystemStatus.WARNING

        if self.last_scraping:
            hours_since_last = (datetime.now() - self.last_scraping).total_seconds() / 3600
            if hours_since_last > 25:
                return SystemStatus.WARNING

        return SystemStatus.NORMAL


    @property
    def uptime_formatted(self) -> str:
        """포맷된 가동 시간"""
        hours = self.uptime_seconds // 3600
        minutes = (self.uptime_seconds % 3600) // 60
        return f"{hours}시간 {minutes}분"
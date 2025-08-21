from datetime import datetime, timedelta
from enum import Enum
from re import sub
from typing import Optional, Dict, Any

from pydantic import BaseModel, Field, field_validator, computed_field


class ContestStatus(str, Enum):
    """공모전 상태"""
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    UNKNOWN = "UNKNOWN"


class Contest(BaseModel):
    title: str = Field(..., description="제목", min_length=1)
    organization: str = Field(..., description="주최 기관")
    img_url: str = Field(..., description="포스터")
    detail_url: str = Field(..., description="상세 페이지")
    deadline: str = Field(..., description="마감일")
    d_day: int = Field(..., description="디데이")
    site: str = Field(..., description="원본 사이트")

    create_day: datetime = Field(default_factory=datetime.now)

    class Config:
        use_enum_values = True
        json_encoders = {datetime: lambda dt: dt.isoformat()}


    @field_validator("deadline", mode="before")
    @classmethod
    def deadline_parser(cls, value: str) -> str:
        """

            마감일 계산

        """
        if not value or value.strip() == "":
            return "2000-01-01"

        if value.strip().startswith("D-"):
            try:
                days = int(value[2:])
                date_obj = datetime.now() + timedelta(days=days)
                return date_obj.strftime("%Y-%m-%d")
            except ValueError:
                return "2000-01-01"


        elif value.startswith("20"):

            try:
                digits_only = ''.join(filter(lambda x: x.isdigit(), value))

                if len(digits_only) == 8:  # YYYYMMDD
                    date_obj = datetime.strptime(digits_only, "%Y-%m-%d")
                    return date_obj.strftime("%Y-%m-%d")

            except ValueError:
                return "2000-01-01"

        return "2000-01-01"


    @computed_field
    @property
    def unique_key(self):
        """

            DB primary key

        """
        strip_title = sub(r'[^A-Za-z0-9ㄱ-힣]', '', self.title.replace(" ", ""))
        # return f"{self.deadline}{strip_title}"
        return f"{strip_title}"


    @computed_field
    @property
    def status(self) -> ContestStatus:
        """

            공모전 상태 계산

        """
        try:
            deadline_date = datetime.strptime(self.deadline, "%Y-%m-%d").date()
            today = datetime.now().date()

            if deadline_date < today:
                return ContestStatus.EXPIRED
            elif deadline_date == today:
                return ContestStatus.ACTIVE
            else:
                return ContestStatus.ACTIVE

        except ValueError:
            return ContestStatus.UNKNOWN


    @computed_field
    @property
    def days_remaining(self) -> Optional[int]:
        try:
            deadline_date = datetime.strptime(self.deadline, "%Y-%m-%d").date()
            today = datetime.now().date()
            delta = (deadline_date - today).days
            return delta if delta >= 0 else None
        except ValueError:
            return None


    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "organization": self.organization,
            "img_url": self.img_url,
            "detail_url": self.detail_url,
            "deadline": self.deadline,
            "d_day": self.d_day,
            "site": self.site,
            "create_day": self.create_day,
            "key": self.unique_key,
            "days_remaining": self.days_remaining
        }

    def is_expired(self) -> bool:
        """만료 여부 확인"""
        return self.status == ContestStatus.EXPIRED

    def __str__(self) -> str:
        return f"Contest(title='{self.title}', deadline='{self.deadline}', status='{self.status}')"

    def __repr__(self) -> str:
        return self.__str__()
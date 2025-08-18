from datetime import datetime, timedelta
from pydantic import BaseModel, field_validator, model_validator
from re import sub


class Item_info(BaseModel):
    img: str
    title: str
    organize: str
    date: str
    link: str
    key: str = ""

    @field_validator('date', mode='before')
    @classmethod
    def convert_date(cls, value):
        if value.startswith("D-"):
            try:
                days = int(value[2:])
                date_obj = datetime.now() + timedelta(days=days)
                return date_obj.strftime("%Y-%m-%d")
            except ValueError:
                return "2000-01-01"

        elif value.startswith("20"):
            digits_only = ''.join(filter(lambda x: x.isdigit(), value))
            if len(digits_only) == 8:  # YYYYMMDD
                date_obj = datetime.strptime(digits_only, "%Y%m%d")
                return date_obj.strftime("%Y-%m-%d")

        return "2000-01-01"

    @model_validator(mode="after")
    def set_key(self):
        self.key = self.date + sub(r'[^A-Za-z0-9ㄱ-힣]', '', self.title.replace(" ", ""))
        return self

    def to_dict(self):  # cls가 아니라 self를 사용

        d = {
            "img": self.img,
            "title": self.title,
            "org": self.organize,
            "date": self.date,
            "link": self.link,
            "key": self.key
        }

        print(f"[debug] item to ditionary {d}")

        return d

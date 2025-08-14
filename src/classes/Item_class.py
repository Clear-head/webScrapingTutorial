from datetime import datetime, timedelta
from pydantic import BaseModel, field_validator, model_validator
from re import sub
from typing import Dict

class item_info(BaseModel):
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
                return "마감"
        return "마감"
    

    @model_validator(mode="after")
    def set_key(self):
        self.key = sub('[-=+,#/\?:^.@*\"※~ㆍ!』‘|\(\)\[\]`\'…》\”\“\’·]', '', self.title)
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
    




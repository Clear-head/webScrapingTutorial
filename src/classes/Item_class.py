from datetime import datetime, timedelta
from pydantic import BaseModel, field_validator

class item_info(BaseModel):
    img: str
    title: str
    organize: str
    date: str
    link: str
    key: str
    site: str

    @field_validator('date', mode='before')
    @classmethod
    def convert_date(cls, value):
        if value.startswith("D-"):
            try:
                days = int(value[2:]) if cls.site != "위비티" else int(value[2:])-1
                date_obj = datetime.now() + timedelta(days=days)
                return date_obj.strftime("%Y-%m-%d") + " 까지"
            except ValueError:
                return "마감"
        return "마감"
    
    def to_dict(cls):
        return {"img": cls.img, "title": cls.title, "org": cls.organize, "date": cls.date, "link": cls.link, "key": cls.key, "site": cls.site}
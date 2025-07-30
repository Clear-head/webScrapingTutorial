from datetime import datetime, timedelta

class item_info:
    def __init__(self, img, title, organize, date):
        self.img = img
        self.title = title
        self.organize = organize
        self.date = self.__set_date(date)

    def __set_date(self, date):
        now = datetime.now() + timedelta(days=int(date[2:]))
        return now.strftime('%Y-%m-%d')
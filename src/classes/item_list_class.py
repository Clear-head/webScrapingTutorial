from .Item_class import item_info
import re
from typing import List

class ItemList:
    def __init__(self):
        self._items = []
        # 중복 확인을 위한 고유 식별자 집합
        self._unique_keys = set()

    def add_item(self, item: item_info):

        title_key = re.sub('[-=+,#/\?:^.@*\"※~ㆍ!』‘|\(\)\[\]`\'…》\”\“\’·]', ' ', item.title)
        item.key = title_key

        if title_key not in self._unique_keys:
            self._items.append(item)
            self._unique_keys.add(title_key)
            return True
        return False
    
    def get_items(self):
        return self._items
    
    def extends(self, items: List[item_info]):
        for item in items:
            self.add_item(item)
    
    def __len__(self):
        return len(self._items)
    
    def __iter__(self):
        return iter(self._items)

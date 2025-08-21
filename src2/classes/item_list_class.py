from .Item_class import ItemInfo
from typing import List


class ItemList:
    def __init__(self):
        self._items = []
        # 중복 확인을 위한 고유 식별자 집합
        self._unique_keys = set()

    def add_item(self, item: ItemInfo):

        if item.key not in self._unique_keys:
            self._items.append(item)
            self._unique_keys.add(item.key)
            return True
        return False

    def get_items(self):
        return self._items

    def extends(self, items: List[ItemInfo]):
        for item in items:
            self.add_item(item)

    def __len__(self):
        return len(self._items)

    def __iter__(self):
        return iter(self._items)

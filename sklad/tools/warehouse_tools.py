"""
title: MEZA — Склад
description: Поиск товаров, проверка остатков и построение маршрута сборки заказа.
"""

import json
import os

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "warehouse_mock.json")


def _load_data():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _zone_order(item):
    return (item["zone"], item["aisle"], item["shelf"])


class Tools:
    def __init__(self):
        pass

    def find_item(self, query: str) -> str:
        """
        Найти товар на складе по названию (частичное совпадение) или точному SKU.
        :param query: Название товара или SKU для поиска.
        """
        data = _load_data()
        query_lower = query.strip().lower()
        matches = [
            item
            for item in data["items"]
            if query_lower == item["sku"].lower() or query_lower in item["name"].lower()
        ]
        if not matches:
            return json.dumps({"found": False, "query": query}, ensure_ascii=False)
        return json.dumps({"found": True, "items": matches}, ensure_ascii=False)

    def check_stock(self, sku: str) -> str:
        """
        Проверить остаток конкретного товара по SKU.
        :param sku: SKU товара.
        """
        data = _load_data()
        for item in data["items"]:
            if item["sku"].lower() == sku.strip().lower():
                low = item["qty"] < item["low_stock_threshold"]
                return json.dumps({"found": True, "item": item, "low_stock": low}, ensure_ascii=False)
        return json.dumps({"found": False, "sku": sku}, ensure_ascii=False)

    def list_low_stock(self) -> str:
        """
        Вернуть список товаров, остаток которых ниже порога пополнения.
        """
        data = _load_data()
        low = [item for item in data["items"] if item["qty"] < item["low_stock_threshold"]]
        return json.dumps({"low_stock_items": low}, ensure_ascii=False)

    def build_route(self, order_id: str = "", item_skus: str = "") -> str:
        """
        Построить кратчайший маршрут сборки заказа по складу.
        :param order_id: Идентификатор заказа из базы заказов (если известен).
        :param item_skus: Список SKU товаров через запятую (используется, если order_id не указан).
        """
        data = _load_data()
        skus = []

        if order_id:
            order = next((o for o in data["orders"] if o["order_id"] == order_id), None)
            if not order:
                return json.dumps({"found": False, "order_id": order_id}, ensure_ascii=False)
            skus = order["items"]
        elif item_skus:
            skus = [s.strip() for s in item_skus.split(",") if s.strip()]
        else:
            return json.dumps({"error": "Укажи order_id или item_skus"}, ensure_ascii=False)

        items_by_sku = {item["sku"]: item for item in data["items"]}
        route_items = [items_by_sku[s] for s in skus if s in items_by_sku]
        missing = [s for s in skus if s not in items_by_sku]

        route_items.sort(key=_zone_order)

        route = [
            {
                "step": i + 1,
                "sku": item["sku"],
                "name": item["name"],
                "location": f"Зона {item['zone']}, ряд {item['aisle']}, полка {item['shelf']}",
            }
            for i, item in enumerate(route_items)
        ]

        return json.dumps({"route": route, "missing_skus": missing}, ensure_ascii=False)

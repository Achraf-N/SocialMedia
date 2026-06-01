from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from bson import ObjectId
from fastapi import APIRouter, Depends

from app.core.database import (
    chat_sessions_collection,
    orders_collection,
    products_collection,
    shops_collection,
)
from app.core.dependencies import get_current_owner

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

DAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _week_bounds(offset_weeks: int = 0) -> tuple[datetime, datetime]:
    """Return (start, end) of the week offset_weeks ago (UTC, Monday-based)."""
    now = datetime.now(timezone.utc)
    monday = now - timedelta(days=now.weekday(), weeks=offset_weeks)
    start = monday.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=7)
    return start, end


def _month_bounds(offset_months: int = 0) -> tuple[datetime, datetime]:
    """Return (start, end) of the month offset_months ago (UTC)."""
    now = datetime.now(timezone.utc)
    year = now.year
    month = now.month - offset_months
    while month <= 0:
        month += 12
        year -= 1
    start = datetime(year, month, 1, tzinfo=timezone.utc)
    if month == 12:
        end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        end = datetime(year, month + 1, 1, tzinfo=timezone.utc)
    return start, end


def _day_bounds(days_ago: int = 0) -> tuple[datetime, datetime]:
    now = datetime.now(timezone.utc)
    day = (now - timedelta(days=days_ago)).replace(hour=0, minute=0, second=0, microsecond=0)
    return day, day + timedelta(days=1)


def _owner_shop_ids(owner: dict[str, Any]) -> list[ObjectId]:
    return [s["_id"] for s in shops_collection.find({"owner_id": owner["_id"]}, {"_id": 1})]


def _change_percent(current: float, previous: float) -> float | None:
    if previous == 0:
        return None
    return round((current - previous) / previous * 100, 1)


@router.get("/summary")
def get_summary(owner: dict[str, Any] = Depends(get_current_owner)) -> dict:
    owner_oid = owner["_id"]
    shop_ids = _owner_shop_ids(owner)

    # --- Shops ---
    month_start, month_end = _month_bounds(0)
    prev_month_start, prev_month_end = _month_bounds(1)

    total_shops = shops_collection.count_documents({"owner_id": owner_oid})
    shops_this_month = shops_collection.count_documents({
        "owner_id": owner_oid,
        "created_at": {"$gte": month_start, "$lt": month_end},
    })
    shops_prev_month = shops_collection.count_documents({
        "owner_id": owner_oid,
        "created_at": {"$gte": prev_month_start, "$lt": prev_month_end},
    })

    # --- Products ---
    total_products = products_collection.count_documents({"shop_id": {"$in": shop_ids}}) if shop_ids else 0
    products_this_month = products_collection.count_documents({
        "shop_id": {"$in": shop_ids},
        "created_at": {"$gte": month_start, "$lt": month_end},
    }) if shop_ids else 0
    products_prev_month = products_collection.count_documents({
        "shop_id": {"$in": shop_ids},
        "created_at": {"$gte": prev_month_start, "$lt": prev_month_end},
    }) if shop_ids else 0

    # --- Orders ---
    today_start, today_end = _day_bounds(0)
    total_orders = orders_collection.count_documents({"shop_id": {"$in": shop_ids}}) if shop_ids else 0
    orders_today = orders_collection.count_documents({
        "shop_id": {"$in": shop_ids},
        "created_at": {"$gte": today_start, "$lt": today_end},
    }) if shop_ids else 0

    # --- Revenue (delivered only) ---
    def _sum_revenue(extra_filter: dict) -> float:
        if not shop_ids:
            return 0.0
        pipeline = [
            {"$match": {"shop_id": {"$in": shop_ids}, "status": "delivered", **extra_filter}},
            {"$group": {"_id": None, "total": {"$sum": "$total_price"}}},
        ]
        result = list(orders_collection.aggregate(pipeline))
        return round(result[0]["total"], 2) if result else 0.0

    total_revenue = _sum_revenue({})
    revenue_this_month = _sum_revenue({"created_at": {"$gte": month_start, "$lt": month_end}})
    revenue_prev_month = _sum_revenue({"created_at": {"$gte": prev_month_start, "$lt": prev_month_end}})

    # --- Conversations ---
    week_start, week_end = _week_bounds(0)
    prev_week_start, prev_week_end = _week_bounds(1)

    total_conversations = chat_sessions_collection.count_documents({"shop_id": {"$in": [str(s) for s in shop_ids]}}) if shop_ids else 0
    conversations_this_week = chat_sessions_collection.count_documents({
        "shop_id": {"$in": [str(s) for s in shop_ids]},
        "updated_at": {"$gte": week_start, "$lt": week_end},
    }) if shop_ids else 0
    conversations_prev_week = chat_sessions_collection.count_documents({
        "shop_id": {"$in": [str(s) for s in shop_ids]},
        "updated_at": {"$gte": prev_week_start, "$lt": prev_week_end},
    }) if shop_ids else 0

    return {
        "shops": {
            "total": total_shops,
            "this_month": shops_this_month,
            "previous_month": shops_prev_month,
            "change": shops_this_month - shops_prev_month,
        },
        "products": {
            "total": total_products,
            "this_month": products_this_month,
            "previous_month": products_prev_month,
            "change": products_this_month - products_prev_month,
        },
        "orders": {
            "total": total_orders,
            "today": orders_today,
        },
        "revenue": {
            "total": total_revenue,
            "this_month": revenue_this_month,
            "previous_month": revenue_prev_month,
            "change_percent": _change_percent(revenue_this_month, revenue_prev_month),
        },
        "conversations": {
            "total": total_conversations,
            "this_week": conversations_this_week,
            "previous_week": conversations_prev_week,
            "change_percent": _change_percent(conversations_this_week, conversations_prev_week),
        },
    }


@router.get("/orders-chart")
def get_orders_chart(owner: dict[str, Any] = Depends(get_current_owner)) -> list[dict]:
    shop_ids = _owner_shop_ids(owner)
    week_start, week_end = _week_bounds(0)

    daily_counts: dict[int, int] = defaultdict(int)

    if shop_ids:
        orders = orders_collection.find(
            {"shop_id": {"$in": shop_ids}, "created_at": {"$gte": week_start, "$lt": week_end}},
            {"created_at": 1},
        )
        for order in orders:
            created = order["created_at"]
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            day_index = (created - week_start).days
            if 0 <= day_index < 7:
                daily_counts[day_index] += 1

    return [{"day": DAY_LABELS[i], "orders": daily_counts[i]} for i in range(7)]


@router.get("/chat-chart")
def get_chat_chart(owner: dict[str, Any] = Depends(get_current_owner)) -> list[dict]:
    shop_ids = _owner_shop_ids(owner)
    str_shop_ids = [str(s) for s in shop_ids]
    week_start, week_end = _week_bounds(0)

    daily_counts: dict[int, int] = defaultdict(int)

    if shop_ids:
        sessions = chat_sessions_collection.find(
            {
                "shop_id": {"$in": str_shop_ids},
                "updated_at": {"$gte": week_start, "$lt": week_end},
            },
            {"updated_at": 1},
        )
        for session in sessions:
            updated = session["updated_at"]
            if updated.tzinfo is None:
                updated = updated.replace(tzinfo=timezone.utc)
            day_index = (updated - week_start).days
            if 0 <= day_index < 7:
                daily_counts[day_index] += 1

    return [{"day": DAY_LABELS[i], "sessions": daily_counts[i]} for i in range(7)]


@router.get("/best-sellers")
def get_best_sellers(
    limit: int = 5,
    owner: dict[str, Any] = Depends(get_current_owner),
) -> list[dict]:
    shop_ids = _owner_shop_ids(owner)
    if not shop_ids:
        return []

    delivered_orders = list(
        orders_collection.find(
            {"shop_id": {"$in": shop_ids}, "status": "delivered"},
            {"items": 1},
        )
    )

    sales: dict[ObjectId, dict] = {}
    for order in delivered_orders:
        for item in order.get("items", []):
            pid = item["product_id"]
            qty = item.get("quantity", 1)
            if pid not in sales:
                sales[pid] = {"units_sold": 0}
            sales[pid]["units_sold"] += qty

    if not sales:
        return []

    top_ids = sorted(sales, key=lambda pid: sales[pid]["units_sold"], reverse=True)[:limit]

    products = {
        p["_id"]: p
        for p in products_collection.find({"_id": {"$in": top_ids}})
    }

    result = []
    for pid in top_ids:
        product = products.get(pid)
        if not product:
            continue
        units_sold = sales[pid]["units_sold"]
        unit_price = float(product.get("price", 0))
        result.append({
            "product_id": str(pid),
            "name": product.get("name", ""),
            "category": product.get("category", ""),
            "stock": product.get("stock", 0),
            "units_sold": units_sold,
            "revenue": round(units_sold * unit_price, 2),
        })

    return result

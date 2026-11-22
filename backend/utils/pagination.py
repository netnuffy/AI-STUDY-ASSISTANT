"""Shared pagination helpers for list endpoints."""

from fastapi import Query


def pagination_params(
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)
):
    return {"page": page, "page_size": page_size}


def paginate(query, page: int, page_size: int):
    """Returns (items, total) for a SQLAlchemy query."""
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return items, total

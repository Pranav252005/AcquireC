"""Celery tasks for background job processing."""

from src.celery_app import celery_app


@celery_app.task(bind=True, max_retries=3)
def discover_city_task(self, city: str, category: str, max_leads: int = 50):
    """Celery task to discover leads for a city+category.

    Args:
        city: Target city name.
        category: Business category to search.
        max_leads: Maximum number of leads to discover.

    Returns:
        Dict with task metadata.
    """
    return {
        "city": city,
        "category": category,
        "max_leads": max_leads,
        "status": "queued",
    }


@celery_app.task(bind=True, max_retries=3)
def enrich_lead_task(self, lead_id: int):
    """Celery task to enrich a single lead.

    Args:
        lead_id: Primary key of the lead to enrich.

    Returns:
        Dict with task metadata.
    """
    return {"lead_id": lead_id, "status": "queued"}

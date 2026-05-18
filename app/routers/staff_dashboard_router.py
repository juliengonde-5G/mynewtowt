"""Staff dashboard — landing for collaborators."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_staff
from app.database import get_db
from app.models.booking import Booking
from app.models.leg import Leg
from app.templating import templates

router = APIRouter(tags=["staff-dashboard"])


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    user=Depends(get_current_staff),
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    now = datetime.now(timezone.utc)

    bookings_to_confirm = await db.scalar(
        select(func.count(Booking.id)).where(Booking.status == "submitted")
    )
    legs_upcoming = await db.scalar(
        select(func.count(Leg.id)).where(Leg.etd > now)
    )

    return templates.TemplateResponse(
        "staff/dashboard.html",
        {
            "request": request,
            "user": user,
            "bookings_to_confirm": int(bookings_to_confirm or 0),
            "legs_upcoming": int(legs_upcoming or 0),
        },
    )

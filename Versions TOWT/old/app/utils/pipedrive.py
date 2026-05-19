"""
Pipedrive CRM integration — async HTTP client.

Supports:
- Searching Organizations (for client creation)
- Creating/updating Deals (for offers & transport orders)
"""
import httpx
from typing import Optional


PIPEDRIVE_BASE = "https://api.pipedrive.com/v1"


async def _get_token_from_db(db=None) -> Optional[str]:
    """Get Pipedrive API token from database (OpexParameter)."""
    if db:
        from sqlalchemy import select
        from app.models.finance import OpexParameter
        result = await db.execute(
            select(OpexParameter).where(OpexParameter.parameter_name == "pipedrive_api_token")
        )
        param = result.scalar_one_or_none()
        if param and param.description:
            return param.description.strip() or None
        return None

    # Fallback: create a new DB session
    from app.database import async_session
    async with async_session() as session:
        from sqlalchemy import select
        from app.models.finance import OpexParameter
        result = await session.execute(
            select(OpexParameter).where(OpexParameter.parameter_name == "pipedrive_api_token")
        )
        param = result.scalar_one_or_none()
        if param and param.description:
            return param.description.strip() or None
    return None


async def _get_token() -> Optional[str]:
    """Get Pipedrive API token (DB first, then .env fallback)."""
    # Try DB first
    token = await _get_token_from_db()
    if token:
        return token
    # Fallback to config (.env)
    from app.config import get_settings
    settings = get_settings()
    return getattr(settings, "PIPEDRIVE_API_TOKEN", None) or None


async def _request(method: str, path: str, params: dict = None, json_body: dict = None) -> dict:
    """Make an authenticated request to Pipedrive API."""
    token = await _get_token()
    if not token:
        return {"success": False, "error": "PIPEDRIVE_API_TOKEN not configured"}

    url = f"{PIPEDRIVE_BASE}{path}"
    query = {"api_token": token}
    if params:
        query.update(params)

    async with httpx.AsyncClient(timeout=15.0) as client:
        if method == "GET":
            resp = await client.get(url, params=query)
        elif method == "POST":
            resp = await client.post(url, params=query, json=json_body)
        elif method == "PUT":
            resp = await client.put(url, params=query, json=json_body)
        else:
            return {"success": False, "error": f"Unsupported method: {method}"}

    if resp.status_code >= 400:
        return {"success": False, "error": f"HTTP {resp.status_code}: {resp.text[:200]}"}

    return resp.json()


# ═══════════════════════════════════════════════════════════
#  ORGANIZATIONS (read from Pipedrive)
# ═══════════════════════════════════════════════════════════

async def search_organizations(term: str, limit: int = 10) -> list:
    """Search Pipedrive Organizations by name."""
    data = await _request("GET", "/organizations/search", params={
        "term": term,
        "limit": limit,
        "fields": "name",
    })
    if not data.get("success") or not data.get("data"):
        return []

    results = []
    for item in data["data"].get("items", []):
        org = item.get("item", {})
        results.append({
            "id": org.get("id"),
            "name": org.get("name", ""),
            "address": org.get("address", ""),
            "owner_name": org.get("owner", {}).get("name", "") if org.get("owner") else "",
        })
    return results


async def get_organization(org_id: int) -> Optional[dict]:
    """Get full Organization details from Pipedrive."""
    data = await _request("GET", f"/organizations/{org_id}")
    if not data.get("success") or not data.get("data"):
        return None

    org = data["data"]
    # Extract primary person contact
    contact_name = ""
    contact_email = ""
    contact_phone = ""

    # Get persons associated with this org
    persons_data = await _request("GET", f"/organizations/{org_id}/persons", params={"limit": 1})
    if persons_data.get("success") and persons_data.get("data"):
        person = persons_data["data"][0]
        contact_name = person.get("name", "")
        emails = person.get("email", [])
        if emails and isinstance(emails, list):
            contact_email = emails[0].get("value", "") if emails else ""
        phones = person.get("phone", [])
        if phones and isinstance(phones, list):
            contact_phone = phones[0].get("value", "") if phones else ""

    return {
        "id": org["id"],
        "name": org.get("name", ""),
        "address": org.get("address", ""),
        "country": org.get("address_country", "") or org.get("cc_email", ""),
        "contact_name": contact_name,
        "contact_email": contact_email,
        "contact_phone": contact_phone,
        "owner_name": org.get("owner_name", ""),
    }


# ═══════════════════════════════════════════════════════════
#  DEALS (push to Pipedrive)
# ═══════════════════════════════════════════════════════════

async def create_deal(
    title: str,
    org_id: int,
    value: float = 0,
    currency: str = "EUR",
    stage_id: Optional[int] = None,
    notes: str = "",
) -> Optional[int]:
    """Create a Deal in Pipedrive linked to an Organization. Returns deal_id."""
    body = {
        "title": title,
        "org_id": org_id,
        "value": str(value),
        "currency": currency,
    }
    if stage_id:
        body["stage_id"] = stage_id

    data = await _request("POST", "/deals", json_body=body)
    if not data.get("success") or not data.get("data"):
        return None

    deal_id = data["data"]["id"]

    # Add note if provided
    if notes:
        await _request("POST", "/notes", json_body={
            "deal_id": deal_id,
            "content": notes,
        })

    return deal_id


async def update_deal(
    deal_id: int,
    title: Optional[str] = None,
    value: Optional[float] = None,
    status: Optional[str] = None,  # "open", "won", "lost"
    stage_id: Optional[int] = None,
) -> bool:
    """Update an existing Deal in Pipedrive."""
    body = {}
    if title:
        body["title"] = title
    if value is not None:
        body["value"] = str(value)
    if status:
        body["status"] = status
    if stage_id:
        body["stage_id"] = stage_id

    if not body:
        return True

    data = await _request("PUT", f"/deals/{deal_id}", json_body=body)
    return data.get("success", False)


async def add_deal_note(deal_id: int, content: str) -> bool:
    """Add a note to an existing Deal."""
    data = await _request("POST", "/notes", json_body={
        "deal_id": deal_id,
        "content": content,
    })
    return data.get("success", False)


async def is_configured() -> bool:
    """Check if Pipedrive integration is configured."""
    token = await _get_token()
    return bool(token)

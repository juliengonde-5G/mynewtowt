"""
Permission system for my_newtowt App.

Roles: administrateur, operation, armement, technique, data_analyst, marins,
       commercial, manager_maritime
Modules: planning, commercial, escale, finance, kpi, captain, crew, cargo, claims, mrv
Permissions: C (consult), M (modify), S (delete/suppress)

Usage:
  from app.permissions import can_view, can_edit, can_delete, require_permission

  # In route:
  if not can_view(user, 'commercial'):
      raise HTTPException(403)

  # As dependency:
  @router.get("/commercial")
  async def index(user = Depends(require_permission('commercial', 'C'))):
"""

from fastapi import Depends, HTTPException
from app.auth import get_current_user

# ═══════════════════════════════════════════════════════════════
# PERMISSION MATRIX
# Key: (role, module) → set of permissions {'C', 'M', 'S'}
# Empty set or absent = no access
# ═══════════════════════════════════════════════════════════════

_MATRIX = {
    # ─── ADMINISTRATEUR ──────────────────────────────────
    ("administrateur", "planning"):    {"C", "M", "S"},
    ("administrateur", "commercial"):  {"C", "M", "S"},
    ("administrateur", "escale"):      {"C", "M", "S"},
    ("administrateur", "finance"):     {"C", "M", "S"},
    ("administrateur", "kpi"):         {"C", "M", "S"},
    ("administrateur", "captain"):     {"C", "M", "S"},
    ("administrateur", "crew"):        {"C", "M", "S"},
    ("administrateur", "cargo"):       {"C", "M", "S"},
    ("administrateur", "mrv"):         {"C", "M", "S"},
    ("administrateur", "claims"):      {"C", "M", "S"},

    # ─── OPERATION ───────────────────────────────────────
    # Planning, Commercial, Escale, KPI, On board, Equipage, Cargo, MRV
    ("operation", "planning"):    {"C", "M"},
    ("operation", "commercial"):  {"C", "M"},
    ("operation", "escale"):      {"C", "M", "S"},
    ("operation", "kpi"):         {"C"},
    ("operation", "captain"):     {"C", "M"},
    ("operation", "crew"):        {"C", "M"},
    ("operation", "cargo"):       {"C", "M", "S"},
    ("operation", "mrv"):         {"C", "M"},
    ("operation", "claims"):      {"C", "M", "S"},

    # ─── ARMEMENT (CREW) ────────────────────────────────
    # Planning, Escale, KPI, Equipage
    ("armement", "planning"):    {"C"},
    ("armement", "escale"):      {"C"},
    ("armement", "kpi"):         {"C"},
    ("armement", "captain"):     {"C"},
    ("armement", "crew"):        {"C", "M", "S"},
    ("armement", "mrv"):         {"C"},

    # ─── TECHNIQUE ───────────────────────────────────────
    # Planning, Commercial, Escale, KPI, On board, Equipage, Cargo, MRV
    ("technique", "planning"):    {"C"},
    ("technique", "commercial"):  {"C"},
    ("technique", "escale"):      {"C", "M", "S"},
    ("technique", "kpi"):         {"C"},
    ("technique", "captain"):     {"C", "M"},
    ("technique", "crew"):        {"C"},
    ("technique", "cargo"):       {"C"},
    ("technique", "mrv"):         {"C", "M"},
    ("technique", "claims"):      {"C"},

    # ─── DATA ANALYST ────────────────────────────────────
    # Planning, Escale, Finance, KPI, MRV + admin data params
    ("data_analyst", "planning"):    {"C"},
    ("data_analyst", "commercial"):  {"C"},
    ("data_analyst", "escale"):      {"C"},
    ("data_analyst", "finance"):     {"C", "M", "S"},
    ("data_analyst", "kpi"):         {"C"},
    ("data_analyst", "captain"):     {"C"},
    ("data_analyst", "crew"):        {"C"},
    ("data_analyst", "cargo"):       {"C"},
    ("data_analyst", "mrv"):         {"C", "M"},
    ("data_analyst", "claims"):      {"C"},

    # ─── MARINS ──────────────────────────────────────────
    # Planning, Escale, KPI, Equipage — lecture seule
    ("marins", "planning"):    {"C"},
    ("marins", "escale"):      {"C"},
    ("marins", "kpi"):         {"C"},
    ("marins", "captain"):     {"C"},
    ("marins", "crew"):        {"C"},
    ("marins", "cargo"):       {"C"},
    ("marins", "mrv"):         {"C"},

    # ─── COMMERCIAL ──────────────────────────────────────
    # Planning, Commercial, Escale, KPI, Cargo
    ("commercial", "planning"):    {"C"},
    ("commercial", "commercial"):  {"C", "M", "S"},
    ("commercial", "escale"):      {"C"},
    ("commercial", "kpi"):         {"C"},
    ("commercial", "cargo"):       {"C", "M"},
    ("commercial", "captain"):     {"C"},

    # ─── MANAGER MARITIME ────────────────────────────────
    # Planning, Commercial, Escale, KPI, On board, Equipage, Cargo, MRV
    ("manager_maritime", "planning"):    {"C", "M"},
    ("manager_maritime", "commercial"):  {"C", "M"},
    ("manager_maritime", "escale"):      {"C", "M"},
    ("manager_maritime", "kpi"):         {"C"},
    ("manager_maritime", "captain"):     {"C", "M", "S"},
    ("manager_maritime", "crew"):        {"C", "M"},
    ("manager_maritime", "cargo"):       {"C", "M"},
    ("manager_maritime", "mrv"):         {"C", "M"},
    ("manager_maritime", "claims"):      {"C", "M"},
}

# Legacy role mapping (old roles → new roles)
_LEGACY_MAP = {
    "admin": "administrateur",
    "manager": "operation",
    "operator": "operation",
    "viewer": "data_analyst",
    "gestionnaire_passagers": "commercial",
}

# All roles for settings page
ROLES = [
    ("administrateur", "Administrateur"),
    ("operation", "Opération"),
    ("armement", "Armement / Équipage"),
    ("technique", "Technique"),
    ("data_analyst", "Data Analyst"),
    ("marins", "Marins"),
    ("commercial", "Commercial"),
    ("manager_maritime", "Manager Maritime"),
]

# All modules
MODULES = [
    "planning", "commercial", "escale", "finance",
    "kpi", "captain", "crew", "cargo", "claims", "mrv",
]

# Module display names
MODULE_NAMES = {
    "planning": "Planning",
    "commercial": "Commercial",
    "escale": "Escale",
    "finance": "Finance",
    "kpi": "KPI",
    "captain": "On Board",
    "crew": "Équipage",
    "cargo": "Cargo Docs",
    "mrv": "MRV Fuel",
    "claims": "Claims / Sinistres",
}


def _resolve_role(role: str) -> str:
    """Map legacy roles to new ones."""
    return _LEGACY_MAP.get(role, role)


def get_permissions(user, module: str) -> set:
    """Get permission set for a user on a module."""
    role = _resolve_role(user.role) if user else ""
    return _MATRIX.get((role, module), set())


def can_view(user, module: str) -> bool:
    """Can the user see this module?"""
    return "C" in get_permissions(user, module)


def can_edit(user, module: str) -> bool:
    """Can the user modify data in this module?"""
    return "M" in get_permissions(user, module)


def can_delete(user, module: str) -> bool:
    """Can the user delete data in this module?"""
    return "S" in get_permissions(user, module)


def has_any_access(user, module: str) -> bool:
    """Does the user have any access to this module?"""
    return len(get_permissions(user, module)) > 0


def get_accessible_modules(user) -> list:
    """Return list of modules the user can access."""
    role = _resolve_role(user.role) if user else ""
    return [m for m in MODULES if _MATRIX.get((role, m), set())]


def require_permission(module: str, level: str = "C"):
    """
    FastAPI dependency factory. Checks user has required permission level.
    level: 'C' (view), 'M' (modify), 'S' (delete)
    """
    async def _check(user=Depends(get_current_user)):
        perms = get_permissions(user, module)
        if level not in perms:
            raise HTTPException(
                status_code=403,
                detail=f"Accès non autorisé au module {module}"
            )
        return user
    return _check

"""Shared Jinja2 templates instance with global filters."""
from fastapi.templating import Jinja2Templates
from app.i18n import t as _raw_t, SUPPORTED_LANGUAGES, DEFAULT_LANG


class _TranslatedTemplates(Jinja2Templates):
    """Subclass that auto-injects 'lang' into every TemplateResponse."""

    def TemplateResponse(self, *args, **kwargs):
        # Handle both positional and keyword 'context' argument
        # FastAPI/Starlette signature: TemplateResponse(name, context, ...)
        if len(args) >= 2:
            context = args[1]
        elif "context" in kwargs:
            context = kwargs["context"]
        else:
            # Fallback — no context dict found, let parent handle
            return super().TemplateResponse(*args, **kwargs)

        # Auto-inject lang from user.language if not already set
        if "lang" not in context or not context["lang"]:
            user = context.get("user")
            if user and hasattr(user, "language") and user.language:
                context["lang"] = user.language
            else:
                context["lang"] = DEFAULT_LANG

        # Default timezone context for sidebar clock
        context.setdefault("port_timezone", "UTC")
        context.setdefault("port_tz_label", "Port")
        context.setdefault("port_tz_offset", "UTC")

        return super().TemplateResponse(*args, **kwargs)


templates = _TranslatedTemplates(directory="app/templates")


def fmt_eur(val):
    """Format number as French EUR: 1.234,56"""
    if val is None:
        return "0"
    neg = val < 0
    val = abs(val)
    if val == int(val):
        s = f"{int(val):,}".replace(",", ".")
    else:
        s = f"{val:,.2f}".replace(",", " ").replace(".", ",").replace(" ", ".")
    return f"-{s}" if neg else s


def fmt_eur_int(val):
    """Format number as French EUR without decimals: 1.234"""
    if val is None:
        return "0"
    neg = val < 0
    val = abs(int(val))
    s = f"{val:,}".replace(",", ".")
    return f"-{s}" if neg else s


def country_flag(country_code):
    """Convert 2-letter country code to flag emoji. FR -> 🇫🇷"""
    if not country_code or len(country_code) != 2:
        return ""
    return "".join(chr(0x1F1E6 + ord(c) - ord("A")) for c in country_code.upper())


# Register global filters
templates.env.filters["eur"] = fmt_eur
templates.env.filters["eur_int"] = fmt_eur_int
templates.env.filters["flag"] = country_flag

# Register i18n globals (accessible in all templates)
templates.env.globals["t"] = _raw_t
templates.env.globals["SUPPORTED_LANGUAGES"] = SUPPORTED_LANGUAGES

# Register permission helpers
from app.permissions import can_view, can_edit, can_delete, has_any_access
templates.env.globals["can_view"] = can_view
templates.env.globals["can_edit"] = can_edit
templates.env.globals["can_delete"] = can_delete
templates.env.globals["has_any_access"] = has_any_access

# Register site URL for external links (portals)
from app.config import get_settings
_settings = get_settings()
templates.env.globals["site_url"] = _settings.SITE_URL

# Register CSRF helper (available in all templates as {{ csrf_input(request) }})
from app.csrf import csrf_input as _csrf_input
from markupsafe import Markup
templates.env.globals["csrf_input"] = lambda request: Markup(_csrf_input(request))

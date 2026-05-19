"""TOTP MFA (RFC 6238) — setup, verify, QR code rendering.

Pile : ``pyotp`` pour TOTP, ``segno`` pour QR (pure Python, pas de Pillow).
Les imports sont locaux pour ne pas planter le boot si une dépendance
n'est pas installée — la route appelante affiche alors un message clair.

Modèle de données : ``ClientAccount.mfa_secret`` (base32, 32 chars) et
``ClientAccount.mfa_enabled`` (boolean). Le secret est posé dès la phase
*setup* mais ``mfa_enabled`` ne passe à True qu'après la 1re vérification
réussie (anti-lock-out : on confirme que l'utilisateur peut générer un
code avant d'exiger l'OTP au login).
"""
from __future__ import annotations

from base64 import b64encode
from io import BytesIO


def generate_secret() -> str:
    """Renvoie un nouveau secret base32 pour TOTP."""
    import pyotp
    return pyotp.random_base32()


def provisioning_uri(secret: str, account_email: str, *, issuer: str = "NEWTOWT") -> str:
    """URL otpauth:// pour scan par Google Authenticator / Authy / 1Password / ..."""
    import pyotp
    return pyotp.totp.TOTP(secret).provisioning_uri(account_email, issuer_name=issuer)


def verify_totp(secret: str, code: str, *, valid_window: int = 1) -> bool:
    """Vérifie un code TOTP 6 chiffres.

    ``valid_window=1`` tolère une dérive d'horloge de ±30s (utile sur
    téléphones mal synchronisés).
    """
    if not secret or not code:
        return False
    import pyotp
    try:
        return pyotp.totp.TOTP(secret).verify(code.strip().replace(" ", ""), valid_window=valid_window)
    except Exception:
        return False


def qr_data_uri(otpauth_uri: str) -> str | None:
    """Renvoie un ``data:image/svg+xml;base64,...`` pour ``<img src=...>``.

    Inline = pas d'appel réseau, compatible CSP (data: explicitement
    autorisé par img-src). Renvoie None si segno indisponible — la route
    affichera alors juste le secret en clair pour saisie manuelle.
    """
    try:
        import segno
    except ImportError:
        return None
    try:
        qr = segno.make(otpauth_uri, error="M")
        buf = BytesIO()
        qr.save(buf, kind="svg", scale=4, border=2, dark="#0D5966", light="#FFFFFF")
        return "data:image/svg+xml;base64," + b64encode(buf.getvalue()).decode("ascii")
    except Exception:
        return None

from passlib.context import CryptContext
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from fastapi import Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.config import get_settings
from app.database import get_db
from app.models.user import User

settings = get_settings()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
serializer = URLSafeTimedSerializer(settings.SECRET_KEY)

COOKIE_NAME = "towt_session"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_session_token(user_id: int) -> str:
    return serializer.dumps({"user_id": user_id})


def decode_session_token(token: str) -> dict | None:
    try:
        data = serializer.loads(token, max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60)
        return data
    except (BadSignature, SignatureExpired):
        return None


class AuthRequired(Exception):
    """Raised when user is not authenticated."""
    pass


async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)) -> User:
    """Dependency: get authenticated user from session cookie."""
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise AuthRequired()

    data = decode_session_token(token)
    if not data:
        raise AuthRequired()

    result = await db.execute(select(User).where(User.id == data["user_id"], User.is_active == True))
    user = result.scalar_one_or_none()
    if not user:
        raise AuthRequired()

    return user


async def get_current_user_optional(request: Request, db: AsyncSession = Depends(get_db)) -> User | None:
    """Like get_current_user but returns None instead of raising."""
    try:
        return await get_current_user(request, db)
    except AuthRequired:
        return None


def require_role(*roles):
    """Dependency factory: require specific roles."""
    async def checker(user: User = Depends(get_current_user)):
        if user.role not in roles:
            raise AuthRequired()
        return user
    return checker

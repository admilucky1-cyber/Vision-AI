"""
Vision AI v2.0 - Authentication Router
======================================
JWT-based authentication with Google OAuth2 support.
Production-ready with proper error handling and security.

Features:
- Username/password authentication with bcrypt hashing
- JWT token generation with configurable expiry
- Token blacklisting for logout
- Google OAuth2 integration
- User profile management
"""

import os
import uuid
import bcrypt
from datetime import datetime, timedelta, timezone
from urllib.parse import quote
from typing import Optional, Dict, Set, List  # ✅ FIX: Added missing Optional import
from pathlib import Path

from services.security import require_admin, is_reserved_username, RESERVED_USERNAMES
from fastapi import APIRouter, HTTPException, Depends, status, Request
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import BaseModel, Field, EmailStr, field_validator
from dotenv import load_dotenv
from services.rate_limit import limiter

import logging
logger = logging.getLogger("vision-ai.auth")

# Load environment variables
load_dotenv()

router = APIRouter(prefix="/auth", tags=["Authentication"])

# ==========================================================
# CONFIGURATION
# ==========================================================
SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

# Validate critical configuration
if SECRET_KEY == "change-me-in-production":
    logger.warning("Using default SECRET_KEY. Set a secure key in .env file!")

# ==========================================================
# OAUTH2 SETUP
# ==========================================================
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)

# ==========================================================
# DATA MODELS
# ==========================================================
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_]+$")
    full_name: str = Field(default="", max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=10, max_length=128)

    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        if not v.isalnum() and '_' not in v:
            raise ValueError('Username can only contain letters, numbers, and underscores')
        return v

class UserResponse(BaseModel):
    username: str
    full_name: str
    email: str
    plan: str = "free"
    created_at: str
    disabled: bool = False
    expires_in: Optional[int] = None  # Added for token expiry info

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    username: str

    @field_validator('token_type')
    @classmethod
    def validate_token_type(cls, v):
        if v != "bearer":
            raise ValueError('token_type must be "bearer"')
        return v

class TokenRefresh(BaseModel):
    refresh_token: str

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=10)

    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v):
        if v.strip() == "":
            raise ValueError('New password cannot be empty')
        return v

class UpdateProfileRequest(BaseModel):
    full_name: str = Field(default="", max_length=100)

# ==========================================================
# DATABASE (Production: Replace with PostgreSQL/MongoDB)
# ==========================================================
class UserDatabase:
    """
    File-backed user store (JSON under data/users.json).
    Suitable for single-instance production. For multi-instance, switch to Postgres.
    """

    def __init__(self, path: Optional[Path] = None):
        import json
        import threading

        self._json = json
        self._lock = threading.RLock()
        data_dir = Path(__file__).resolve().parent.parent / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        self._path = path or (data_dir / "users.json")
        self._users: Dict[str, dict] = {}
        self._blacklisted_tokens: Set[str] = set()
        self._load()
        self._seed_admin_from_env()

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            raw = self._json.loads(self._path.read_text(encoding="utf-8"))
            self._users = {k.lower(): v for k, v in (raw.get("users") or {}).items()}
            self._blacklisted_tokens = set(raw.get("blacklist") or [])
            logger.info(f"Loaded {len(self._users)} users from {self._path}")
        except Exception as e:
            logger.error(f"Failed to load users.json: {e}")

    def _save(self) -> None:
        payload = {
            "users": self._users,
            "blacklist": list(self._blacklisted_tokens)[-5000:],  # cap growth
        }
        tmp = self._path.with_suffix(".tmp")
        try:
            tmp.write_text(self._json.dumps(payload, indent=2, default=str), encoding="utf-8")
            tmp.replace(self._path)
        except Exception as e:
            logger.error(f"Failed to persist users.json: {e}")

    def _hash_password(self, password: str) -> str:
        salt = bcrypt.gensalt(rounds=12)
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

    def _seed_admin_from_env(self) -> None:
        """Optional bootstrap admin via ADMIN_USERNAME / ADMIN_PASSWORD (once)."""
        admin_user = (os.getenv("ADMIN_USERNAME") or "").strip()
        admin_pass = (os.getenv("ADMIN_PASSWORD") or "").strip()
        admin_email = (os.getenv("ADMIN_EMAIL") or "admin@localhost").strip()
        if not admin_user or not admin_pass:
            return
        if self.get_user(admin_user):
            return
        with self._lock:
            self._users[admin_user.lower()] = {
                "username": admin_user.lower(),
                "email": admin_email.lower(),
                "full_name": os.getenv("ADMIN_FULL_NAME", "Administrator"),
                "hashed_password": self._hash_password(admin_pass),
                "disabled": False,
                "plan": "enterprise",
                "role": "admin",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "messages_this_month": 0,
                "usage_month": datetime.now(timezone.utc).strftime("%Y-%m"),
            }
            self._save()
            logger.info(f"Seeded admin user from env: {admin_user.lower()}")

    def get_user(self, username: str) -> Optional[dict]:
        return self._users.get(username.lower())

    def get_user_by_email(self, email: str) -> Optional[dict]:
        email_lower = email.lower()
        for user in self._users.values():
            if user.get("email", "").lower() == email_lower:
                return user
        return None

    def create_user(self, user_data: dict) -> dict:
        with self._lock:
            username = user_data["username"].lower()
            if username in self._users:
                raise ValueError(f"Username '{username}' already exists")
            if self.get_user_by_email(user_data["email"]):
                raise ValueError(f"Email '{user_data['email']}' already registered")
            user_data.setdefault("plan", "free")
            user_data.setdefault("role", "user")
            user_data.setdefault("disabled", False)
            user_data.setdefault("messages_this_month", 0)
            user_data.setdefault("usage_month", datetime.now(timezone.utc).strftime("%Y-%m"))
            user_data.setdefault("created_at", datetime.now(timezone.utc).isoformat())
            user_data["username"] = username
            self._users[username] = user_data
            self._save()
            return user_data

    def update_user(self, username: str, updates: dict) -> Optional[dict]:
        with self._lock:
            user = self._users.get(username.lower())
            if not user:
                return None
            user.update(updates)
            self._save()
            return user

    def increment_message_count(self, username: str) -> dict:
        """Track monthly message usage; reset when calendar month changes."""
        with self._lock:
            user = self._users.get(username.lower())
            if not user:
                return {}
            month = datetime.now(timezone.utc).strftime("%Y-%m")
            if user.get("usage_month") != month:
                user["usage_month"] = month
                user["messages_this_month"] = 0
            user["messages_this_month"] = int(user.get("messages_this_month") or 0) + 1
            self._save()
            return user

    def blacklist_token(self, token: str):
        with self._lock:
            self._blacklisted_tokens.add(token)
            self._save()

    def is_token_blacklisted(self, token: str) -> bool:
        return token in self._blacklisted_tokens

    def get_all_users(self) -> Dict[str, dict]:
        return self._users.copy()

    def clear_blacklist(self):
        with self._lock:
            self._blacklisted_tokens.clear()
            self._save()

# Global database instance
user_db = UserDatabase()

# ==========================================================
# HELPER FUNCTIONS
# ==========================================================
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password."""
    try:
        return bool(bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8')))
    except Exception:
        return False

def get_password_hash(password: str) -> str:
    """Hash a password for storing."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def authenticate_user(username: str, password: str) -> Optional[dict]:
    """Authenticate a user by username and password."""
    user = user_db.get_user(username)
    if not user:
        return None
    if not verify_password(password, user["hashed_password"]):
        return None
    if user.get("disabled", False):
        return None
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({
        "exp": expire, 
        "iat": datetime.now(timezone.utc), 
        "jti": str(uuid.uuid4()),
        "type": "access"
    })
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(data: dict) -> str:
    """Create a JWT refresh token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({
        "exp": expire, 
        "iat": datetime.now(timezone.utc), 
        "type": "refresh", 
        "jti": str(uuid.uuid4())
    })
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def _client_ip(request: Optional[Request] = None) -> str:
    """Best-effort client IP behind Railway/Caddy proxies."""
    if not request:
        return "guest"
    try:
        xff = (request.headers.get("x-forwarded-for") or "").split(",")[0].strip()
        if xff:
            return xff[:64]
        xri = (request.headers.get("x-real-ip") or "").strip()
        if xri:
            return xri[:64]
        if request.client and request.client.host:
            return (request.client.host or "guest")[:64]
    except Exception:
        pass
    return "guest"


def make_guest_user(request: Optional[Request] = None) -> dict:
    """Public guest identity — no login required when ALLOW_GUEST=1."""
    ip = _client_ip(request)
    safe = "".join(ch if ch.isalnum() else "_" for ch in ip)[:48] or "guest"
    return {
        "username": f"guest_{safe}",
        "email": "",
        "full_name": "Guest",
        "plan": "free",
        "disabled": False,
        "is_guest": True,
        "messages_this_month": 0,
        "usage_month": datetime.now(timezone.utc).strftime("%Y-%m"),
    }


async def get_current_user(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme),
) -> dict:
    """Get current authenticated user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not token:
        allow = (os.getenv("ALLOW_GUEST", "1") or "1").strip().lower() not in ("0", "false", "no")
        if allow:
            return make_guest_user(request)
        raise credentials_exception

    if user_db.is_token_blacklisted(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        token_type: str = payload.get("type", "access")

        if username is None or token_type != "access":
            raise credentials_exception

        exp = payload.get("exp")
        if exp and datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Guest JWTs are valid without a row in user_db
        if payload.get("guest") is True or str(username).startswith("guest_"):
            return {
                "username": username,
                "email": "",
                "full_name": "Guest",
                "plan": (payload.get("plan") or "free"),
                "disabled": False,
                "is_guest": True,
                "messages_this_month": 0,
                "usage_month": datetime.now(timezone.utc).strftime("%Y-%m"),
            }

    except JWTError:
        raise credentials_exception

    user = user_db.get_user(username)
    if user is None or user.get("disabled", False):
        raise credentials_exception

    return user

async def get_current_active_user(current_user: dict = Depends(get_current_user)) -> dict:
    """Get current active user."""
    return current_user

# ==========================================================
# GOOGLE OAUTH SETUP
# ==========================================================
GOOGLE_CLIENT_ID = (os.getenv("GOOGLE_CLIENT_ID") or "").strip()
GOOGLE_CLIENT_SECRET = (os.getenv("GOOGLE_CLIENT_SECRET") or "").strip()
# Prefer explicit env; otherwise derived from APP_BASE_URL or the live request
GOOGLE_REDIRECT_URI = (os.getenv("GOOGLE_REDIRECT_URI") or "").strip()
APP_BASE_URL = (os.getenv("APP_BASE_URL") or os.getenv("RAILWAY_PUBLIC_DOMAIN") or "").strip().rstrip("/")

google_oauth_available = bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)

if google_oauth_available:
    try:
        from authlib.integrations.starlette_client import OAuth
        oauth = OAuth()
        oauth.register(
            name="google",
            server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
            client_id=GOOGLE_CLIENT_ID,
            client_secret=GOOGLE_CLIENT_SECRET,
            client_kwargs={
                "scope": "openid email profile",
                "prompt": "select_account",
            },
        )
    except ImportError:
        logger.warning("authlib not installed. Google OAuth will be disabled.")
        oauth = None
else:
    oauth = None
    logger.info("Google OAuth disabled — set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET to enable")


def _resolve_google_redirect_uri(request: Request) -> str:
    """Production-safe redirect URI (must match Google Cloud Console exactly)."""
    if GOOGLE_REDIRECT_URI:
        return GOOGLE_REDIRECT_URI
    if APP_BASE_URL:
        base = APP_BASE_URL if APP_BASE_URL.startswith("http") else f"https://{APP_BASE_URL}"
        return f"{base.rstrip('/')}/auth/google/callback"
    # Derive from incoming request (works on Railway if proxy headers are correct)
    try:
        base = str(request.base_url).rstrip("/")
        return f"{base}/auth/google/callback"
    except Exception:
        return "http://localhost:5050/auth/google/callback"

# ==========================================================
# ROUTES
# ==========================================================

@router.get("/login/debug", tags=["debug"])
async def debug_google_config():
    """Debug endpoint to check Google OAuth configuration (no secrets returned)."""
    return {
        "client_id_configured": bool(GOOGLE_CLIENT_ID),
        "client_secret_configured": bool(GOOGLE_CLIENT_SECRET),
        "oauth_available": bool(google_oauth_available and oauth is not None),
        "redirect_uri_env": GOOGLE_REDIRECT_URI or None,
        "app_base_url": APP_BASE_URL or None,
        "hint": "Google Cloud Console → Authorized redirect URIs must match exactly",
    }

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(request: Request, user: UserCreate):
    if is_reserved_username(user.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This username is reserved",
        )
    """
    Register a new user account.

    - **username**: Unique username (3-50 chars, alphanumeric + underscore)
    - **full_name**: Display name
    - **email**: Valid email address
    - **password**: Minimum 6 characters
    """
    try:
        hashed_password = get_password_hash(user.password)
        new_user = {
            "username": user.username.lower(),
            "full_name": (user.full_name or user.username),
            "email": user.email.lower(),
            "hashed_password": hashed_password,
            "plan": "free",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "disabled": False,
        }
        user_db.create_user(new_user)

        return UserResponse(
            username=new_user["username"],
            full_name=new_user["full_name"],
            email=new_user["email"],
            plan=new_user["plan"],
            created_at=new_user["created_at"],
            disabled=new_user["disabled"],
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

# POST /login is registered on app in main.py (direct_auth_login) to avoid 405


@router.post("/guest")
async def guest_login(request: Request):
    """Issue a short-lived guest JWT so Continue as guest works without an account."""
    allow = (os.getenv("ALLOW_GUEST", "1") or "1").strip().lower() not in ("0", "false", "no")
    if not allow:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Guest access is disabled")

    guest = make_guest_user(request)
    # unique suffix so concurrent guests do not collide
    guest_name = f"{guest['username']}_{uuid.uuid4().hex[:8]}"
    access = create_access_token(
        data={"sub": guest_name, "guest": True, "plan": "free"},
        expires_delta=timedelta(hours=12),
    )
    refresh = create_refresh_token(data={"sub": guest_name, "guest": True})
    return {
        "message": "Guest session started",
        "access_token": access,
        "refresh_token": refresh,
        "token": access,
        "token_type": "bearer",
        "expires_in": 12 * 3600,
        "username": guest_name,
        "isGuest": True,
        "is_guest": True,
        "plan": "free",
        "user": {
            "username": guest_name,
            "full_name": "Guest",
            "email": "",
            "plan": "free",
            "is_guest": True,
        },
    }


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: Request, token_data: TokenRefresh):
    """Refresh an expired access token using a refresh token."""
    try:
        payload = jwt.decode(token_data.refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        token_type: str = payload.get("type")

        if username is None or token_type != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

        is_guest = payload.get("guest") is True or str(username).startswith("guest_")
        user = user_db.get_user(username) if not is_guest else None
        if not is_guest and (user is None or user.get("disabled")):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

        token_data = {"sub": username}
        if is_guest:
            token_data["guest"] = True
            token_data["plan"] = payload.get("plan") or "free"
        access_token = create_access_token(data=token_data)
        refresh_token = create_refresh_token(data={k: token_data[k] for k in token_data if k in ("sub", "guest")})

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            username=username,
        )

    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: dict = Depends(get_current_active_user)):
    """Get current authenticated user profile."""
    # Added expires_in for frontend to know when token expires
    token_exp = current_user.get("exp")
    expires_in = int(token_exp - datetime.now(timezone.utc).timestamp()) if token_exp else None

    return UserResponse(
        username=current_user["username"],
        full_name=current_user["full_name"],
        email=current_user["email"],
        plan=current_user.get("plan", "free"),
        created_at=current_user.get("created_at", ""),
        disabled=current_user.get("disabled", False),
        expires_in=expires_in,
    )

@router.post("/logout")
async def logout(token: str = Depends(oauth2_scheme)):
    """Logout user by blacklisting the token."""
    if token:
        user_db.blacklist_token(token)
    return {"message": "Logged out successfully", "success": True}

@router.post("/change-password")
async def change_password(
    password_data: ChangePasswordRequest,
    current_user: dict = Depends(get_current_active_user),
):
    """Change user password."""
    if not verify_password(password_data.old_password, current_user["hashed_password"]):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect current password")

    user_db.update_user(current_user["username"], {"hashed_password": get_password_hash(password_data.new_password)})
    return {"message": "Password updated successfully", "success": True}

@router.post("/update-profile")
async def update_profile(
    profile_data: UpdateProfileRequest,
    current_user: dict = Depends(get_current_active_user),
):
    """Update user's full name."""
    user_db.update_user(current_user["username"], {"full_name": profile_data.full_name})
    return {"message": "Profile updated successfully", "success": True}

@router.post("/verify-email")
async def verify_email(token: str):
    """Placeholder for email verification."""
    return {"message": "Email verification not implemented yet", "success": False}

@router.get("/users", response_model=List[UserResponse])
async def get_all_users(current_user: dict = Depends(get_current_active_user)):
    """Get all users (admin only - placeholder)."""
    # This is a placeholder for admin functionality
    require_admin(current_user)
    
    users = user_db.get_all_users()
    return [
        UserResponse(
            username=user["username"],
            full_name=user["full_name"],
            email=user["email"],
            plan=user.get("plan", "free"),
            created_at=user.get("created_at", ""),
            disabled=user.get("disabled", False),
        )
        for user in users.values()
    ]

# ==========================================================
# GOOGLE OAUTH ROUTES (✅ SESSION-BASED, RELIABLE)
# ==========================================================

@router.get("/google")
async def login_via_google(request: Request):
    """Redirect to Google OAuth login page."""
    if not oauth:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth is not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env"
        )

    state = str(uuid.uuid4())
    request.session["oauth_state"] = state
    # Remember redirect for callback consistency
    redirect_uri = _resolve_google_redirect_uri(request)
    request.session["oauth_redirect_uri"] = redirect_uri
    logger.info(f"Google OAuth start → redirect_uri={redirect_uri}")
    return await oauth.google.authorize_redirect(request, redirect_uri, state=state)


@router.get("/google/callback")
async def auth_google_callback(request: Request):
    """Handle Google OAuth callback and issue app JWTs."""
    if not oauth:
        return RedirectResponse(url="/login.html?error=oauth_not_configured", status_code=302)

    err = request.query_params.get("error")
    if err:
        desc = request.query_params.get("error_description") or err
        logger.warning(f"Google OAuth error: {desc}")
        return RedirectResponse(
            url=f"/login.html?error={quote(str(desc)[:120])}",
            status_code=302,
        )

    try:
        returned_state = request.query_params.get("state")
        saved_state = request.session.get("oauth_state")
        if not returned_state or not saved_state or returned_state != saved_state:
            logger.warning(
                "OAuth state mismatch (session cookie lost?). "
                "Check SESSION_SECRET, HTTPS, and same-site cookies."
            )
            return RedirectResponse(
                url="/login.html?error=session_expired_retry_google_login",
                status_code=302,
            )
        request.session.pop("oauth_state", None)

        redirect_uri = request.session.pop(
            "oauth_redirect_uri", None
        ) or _resolve_google_redirect_uri(request)

        token = await oauth.google.authorize_access_token(request)
        user_info = token.get("userinfo")
        if not user_info and token.get("id_token"):
            # Some Authlib versions need explicit parse
            try:
                user_info = await oauth.google.parse_id_token(request, token)
            except Exception as pe:
                logger.debug(f"parse_id_token: {pe}")
        if not user_info:
            try:
                resp = await oauth.google.get(
                    "https://openidconnect.googleapis.com/v1/userinfo", token=token
                )
                user_info = resp.json()
            except Exception as ue:
                logger.error(f"userinfo fetch failed: {ue}")
                return RedirectResponse(url="/login.html?error=google_userinfo_failed", status_code=302)

        email = (user_info.get("email") or "").lower().strip()
        name = (user_info.get("name") or email or "Google User").strip()
        google_id = str(user_info.get("sub") or "")
        if not email:
            return RedirectResponse(url="/login.html?error=google_email_required", status_code=302)

        existing_user = user_db.get_user_by_email(email)
        if not existing_user:
            base_username = re.sub(r"[^a-z0-9_]", "", email.split("@")[0].lower())[:24] or "user"
            username = f"{base_username}_{google_id[:6]}"
            # Ensure unique username
            n = 0
            while user_db.get_user(username):
                n += 1
                username = f"{base_username}_{google_id[:4]}{n}"
            new_user = {
                "username": username,
                "full_name": name,
                "email": email,
                "hashed_password": get_password_hash(os.urandom(32).hex()),
                "plan": "free",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "disabled": False,
                "google_id": google_id,
            }
            user_db.create_user(new_user)
            existing_user = new_user
        else:
            # Link google_id if missing
            if google_id and not existing_user.get("google_id"):
                try:
                    user_db.update_user(existing_user["username"], {"google_id": google_id})
                except Exception:
                    pass

        access_token = create_access_token(data={"sub": existing_user["username"]})
        refresh_token = create_refresh_token(data={"sub": existing_user["username"]})

        # Hand tokens to SPA then strip from history (index.js)
        return RedirectResponse(
            url=f"/?token={access_token}&refresh={refresh_token}",
            status_code=302,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Google OAuth callback failed")
        return RedirectResponse(
            url=f"/login.html?error={quote(str(e)[:100])}",
            status_code=302,
        )

# ==========================================================
# HEALTH CHECK
# ==========================================================
@router.get("/health")
async def auth_health():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "user_count": len(user_db.get_all_users()),
        "blacklisted_tokens": len(user_db._blacklisted_tokens),
        "oauth_available": google_oauth_available and oauth is not None,
        "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
    }

# ==========================================================
# EXPORT
# ==========================================================
# Export database for other modules
fake_users_db = user_db.get_all_users()


from services.security import require_admin
"""
Vision AI v2.0 - Upgrade Router
===============================
User plan management with validation, audit logging, and billing integration.
"""

import logging
import os
from datetime import datetime, timezone, timedelta  # 🔥 FIX: Added timedelta import
from typing import Dict, List, Optional, Any

from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, Field, field_validator
from services.rate_limit import limiter

from routes.login import get_current_active_user, user_db

router = APIRouter(prefix="/upgrade", tags=["Upgrade"])
logger = logging.getLogger("vision-ai")

# ==========================================================
# PLAN CONFIGURATION
# ==========================================================
def get_effective_plan(user: dict) -> str:
    """Return plan id, downgrading expired paid plans to free."""
    from datetime import datetime, timezone, timedelta
    plan = (user.get("plan") or "free").lower()
    if plan in ("free", "", "guest"):
        return "free"
    if plan in ("team", "enterprise"):
        return plan
    # student/pro: 30 days from upgraded_at unless subscription says active
    exp = user.get("plan_expires_at")
    if exp:
        try:
            if isinstance(exp, str):
                exp_dt = datetime.fromisoformat(exp.replace("Z", "+00:00"))
            else:
                exp_dt = exp
            if exp_dt.tzinfo is None:
                exp_dt = exp_dt.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) > exp_dt:
                return "free"
        except Exception:
            pass
    elif user.get("upgraded_at"):
        try:
            up = user.get("upgraded_at")
            if isinstance(up, str):
                up_dt = datetime.fromisoformat(up.replace("Z", "+00:00"))
            else:
                up_dt = up
            if up_dt.tzinfo is None:
                up_dt = up_dt.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) > up_dt + timedelta(days=30):
                return "free"
        except Exception:
            pass
    return plan


class PlanConfig:

    """Available subscription plans with comprehensive configuration."""

    PLANS: Dict[str, dict] = {
        "free": {
            "id": "free",
            "name": "Free",
            "price": 0.0,
            "currency": "PKR",
            "billing": "forever",
            "features": [
                "Groq / Gemini / OpenRouter chat",
                "PDF & image Q&A (limits apply)",
                "YouTube transcript tools",
                "10 messages on free plan (then upgrade)",
                "Guest: 1 try — then sign in",
            ],
            "limits": {
                "messages_per_month": int(os.getenv("FREE_MESSAGES_PER_MONTH", "10")),
                "file_upload_size_mb": int(os.getenv("FREE_FILE_MB", "10")),
                "concurrent_chats": 2,
                "images_per_day": int(os.getenv("FREE_IMAGES_PER_DAY", "3")),
            },
            "stripe_price_id": None,
        },
        "pro": {
            "id": "pro",
            "name": "Pro",
            "price": float(os.getenv("PRO_PRICE_PKR", "799")),
            "currency": "PKR",
            "billing": "month",
            "features": [
                "Higher chat limits (2,000 / month)",
                "Larger PDF uploads (50 MB)",
                "Priority when Colab Boost is online",
                "Better RAG on long documents",
                "Easypaisa / bank activation",
            ],
            "limits": {
                "messages_per_month": int(os.getenv("PRO_MESSAGES_PER_MONTH", "2000")),
                "file_upload_size_mb": 50,
                "concurrent_chats": 10,
                "images_per_day": int(os.getenv("PRO_IMAGES_PER_DAY", "30")),
            },
            "stripe_price_id": None,
        },
        
        "student": {
            "id": "student",
            "name": "Student",
            "price": float(os.getenv("STUDENT_PRICE_PKR", "399")),
            "currency": "PKR",
            "billing": "month",
            "features": [
                "Same as Pro for learners",
                "1,500 messages / month",
                "Exam PDF help",
                "Show student ID on payment note",
            ],
            "limits": {
                "messages_per_month": int(os.getenv("STUDENT_MESSAGES_PER_MONTH", "1500")),
                "file_upload_size_mb": 40,
                "concurrent_chats": 5,
                "images_per_day": 20,
            },
            "stripe_price_id": None,
        },

        "team": {
            "id": "team",
            "name": "Team",
            "price": float(os.getenv("TEAM_PRICE_PKR", "3999")),
            "currency": "PKR",
            "billing": "month",
            "features": [
                "All Pro features",
                "5 Team Members",
                "Shared Knowledge Base",
                "Team Analytics Dashboard",
                "API access",
            ],
            "limits": {
                "messages_per_month": -1,
                "file_upload_size_mb": 100,
                "concurrent_chats": 25,
                "team_members": 5,
            },
            "stripe_price_id": "price_team_monthly",
        },
        "enterprise": {
            "id": "enterprise",
            "name": "Enterprise",
            "price": float(os.getenv("ENTERPRISE_PRICE_PKR", "9999")),
            "currency": "PKR",
            "billing": "month",
            "features": [
                "All Team features",
                "Fine-tuning access",
                "Dedicated Cloud",
                "SLA guarantee",
                "Custom integrations",
                "Dedicated account manager",
            ],
            "limits": {
                "messages_per_month": -1,
                "file_upload_size_mb": 500,
                "concurrent_chats": -1,
                "team_members": -1,
            },
            "stripe_price_id": "price_enterprise_monthly",
        }
    }

    @classmethod
    def get_plan(cls, plan_id: str) -> Optional[dict]:
        """Get plan by ID with case-insensitive lookup."""
        return cls.PLANS.get(plan_id.lower())

    @classmethod
    def list_plans(cls) -> List[dict]:
        """List all available plans."""
        return [
            {"id": k, **v}
            for k, v in cls.PLANS.items()
        ]

    @classmethod
    def is_valid_plan(cls, plan_id: str) -> bool:
        """Check if a plan ID is valid."""
        return plan_id.lower() in cls.PLANS

# ==========================================================
# REQUEST/RESPONSE MODELS
# ==========================================================
class UpgradeRequest(BaseModel):
    plan: str = Field(..., description="Plan ID to upgrade to")

    @field_validator('plan')
    @classmethod
    def validate_plan(cls, v):
        """Validate that the plan exists."""
        if not PlanConfig.is_valid_plan(v):
            raise ValueError(f"Plan '{v}' is not available. Choose from: {list(PlanConfig.PLANS.keys())}")
        return v.lower()

class PlanResponse(BaseModel):
    id: str
    name: str
    price: float
    currency: str
    billing: str
    features: List[str]
    limits: dict

    class Config:
        json_schema_extra = {
            "example": {
                "id": "pro",
                "name": "Pro",
                "price": 799,
                "currency": "PKR",
                "billing": "month",
                "features": ["DeepSeek & OpenRouter Access", "Unlimited messages"],
                "limits": {"messages_per_month": -1, "file_upload_size_mb": 50}
            }
        }

class UserPlanResponse(BaseModel):
    username: str
    current_plan: str
    plan_details: dict
    upgraded_at: Optional[str] = None
    plan_expires_at: Optional[str] = None

# ==========================================================
# ROUTES
# ==========================================================
@router.get("/plans", response_model=List[PlanResponse])
@limiter.limit("30/minute")
async def list_available_plans(request: Request):
    """List all available subscription plans with features and limits."""
    logger.info("Plans list requested")
    return PlanConfig.list_plans()

@router.get("/me", response_model=UserPlanResponse)
async def get_user_plan(current_user: dict = Depends(get_current_active_user)):
    """Get current user's subscription plan details."""
    username = current_user["username"]
    user = user_db.get_user(username)

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    plan_id = user.get("plan", "free")
    plan_details = PlanConfig.get_plan(plan_id) or PlanConfig.get_plan("free")

    # Calculate plan expiration (30 days from upgrade for paid plans)
    plan_expires_at = None
    if plan_id != "free" and user.get("upgraded_at"):
        try:
            upgraded = datetime.fromisoformat(user["upgraded_at"])
            plan_expires_at = (upgraded + timedelta(days=30)).isoformat()
        except (TypeError, ValueError) as e:
            logger.debug(f"plan_expires_at parse skip: {e}")

    logger.info(f"Plan details retrieved for user {username}")
    return UserPlanResponse(
        username=username,
        current_plan=plan_id,
        plan_details=plan_details,
        upgraded_at=user.get("upgraded_at"),
        plan_expires_at=plan_expires_at,
    )

@router.post("/upgrade")
@limiter.limit("10/minute")
async def upgrade_user_plan(
    request: Request,
    plan_data: UpgradeRequest,
    current_user: dict = Depends(get_current_active_user),
):
    """
    Upgrade user to a specific plan.
    
    - **plan**: Plan ID (free, pro, team, enterprise)
    """
    plan = plan_data.plan.lower()
    plan_details = PlanConfig.get_plan(plan)

    if not plan_details:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Plan '{plan}' is not available"
        )

    username = current_user["username"]
    user = user_db.get_user(username)

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Prevent upgrading to same plan
    current_plan = user.get("plan", "free")
    if current_plan == plan:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User already on {plan} plan"
        )

    # Prevent downgrading via upgrade endpoint
    if PlanConfig.get_plan(current_plan)["price"] > plan_details["price"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Use /downgrade endpoint to move to a cheaper plan"
        )

    # 🔒 PRODUCTION SAFEGUARD: this endpoint must never grant a paid plan
    # without real payment verification. It previously simulated a
    # successful payment unconditionally for ANY plan, letting any
    # logged-in user self-upgrade to Enterprise for free. Paid plans must
    # go through /upgrade/checkout (Stripe) or /upgrade/payment-request +
    # admin review (Easypaisa/bank) instead. DEBUG mode keeps the old
    # instant-upgrade behavior for local development/testing only.
    if plan_details["price"] > 0 and os.getenv("DEBUG", "false").lower() != "true":
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=(
                f"'{plan}' is a paid plan. Complete payment via /upgrade/checkout "
                f"(card) or submit a transaction ID via /upgrade/payment-request "
                f"(Easypaisa/bank) — plans are activated after payment is verified."
            ),
        )

    # Update user plan (only reached for free-tier transitions, or DEBUG)
    updates = {
        "plan": plan,
        "plan_price": plan_details["price"],
        "upgraded_at": datetime.now(timezone.utc).isoformat(),
        "upgrade_history": user.get("upgrade_history", []) + [{
            "from": current_plan,
            "to": plan,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }]
    }

    if plan_details["price"] > 0:
        # Only reachable in DEBUG mode (see guard above) — dev/testing only.
        updates["payment_id"] = f"pay_debug_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        logger.warning(f"DEBUG-only simulated payment for {username}: {plan} plan (${plan_details['price']})")

    user_db.update_user(username, updates)

    # Audit logging
    logger.info(f"User {username} upgraded from {current_plan} to {plan} plan")
    logger.info(f"Plan details: {plan_details['name']} (${plan_details['price']}/{plan_details['billing']})")

    return {
        "message": f"Successfully upgraded to {plan_details['name']} plan!",
        "plan": plan,
        "plan_details": plan_details,
        "upgraded_at": updates["upgraded_at"],
        "payment_id": updates.get("payment_id"),
    }

@router.post("/downgrade")
@limiter.limit("10/minute")
async def downgrade_to_free(
    request: Request,
    current_user: dict = Depends(get_current_active_user),
):
    """Downgrade user to free plan."""
    username = current_user["username"]
    user = user_db.get_user(username)

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    current_plan = user.get("plan", "free")
    if current_plan == "free":
        return {"message": "Already on free plan", "plan": "free"}

    # Record downgrade
    updates = {
        "plan": "free",
        "plan_price": 0.0,
        "downgraded_at": datetime.now(timezone.utc).isoformat(),
        "downgrade_history": user.get("downgrade_history", []) + [{
            "from": current_plan,
            "to": "free",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }]
    }
    user_db.update_user(username, updates)

    # Audit logging
    logger.info(f"User {username} downgraded from {current_plan} to free plan")

    return {
        "message": "Successfully downgraded to Free plan",
        "previous_plan": current_plan,
        "downgraded_at": updates["downgraded_at"],
    }

@router.get("/usage")
async def get_user_usage(current_user: dict = Depends(get_current_active_user)):
    """Get current user's usage statistics."""
    username = current_user["username"]
    user = user_db.get_user(username)

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    plan_id = user.get("plan", "free")
    plan_details = PlanConfig.get_plan(plan_id)

    month = datetime.now(timezone.utc).strftime("%Y-%m")
    used = int(user.get("messages_this_month") or 0)
    if user.get("usage_month") != month:
        used = 0
    return {
        "username": username,
        "plan": plan_id,
        "usage": {
            "messages_this_month": used,
            "messages_limit": plan_details["limits"]["messages_per_month"],
            "usage_month": user.get("usage_month") or month,
            "file_size_limit_mb": plan_details["limits"]["file_upload_size_mb"],
            "concurrent_chats_limit": plan_details["limits"]["concurrent_chats"],
        },
        "plan_expires_at": None,
    }

# ==========================================================
# ADMIN ENDPOINTS (Future Implementation)
# ==========================================================
@router.get("/admin/plans")
async def admin_list_plans(current_user: dict = Depends(get_current_active_user)):
    """Admin endpoint to list all plans with configuration."""
    # Check if user is admin
    require_admin(current_user)
    
    return PlanConfig.PLANS

@router.post("/admin/plans")
async def admin_create_plan(
    plan_data: dict,
    current_user: dict = Depends(get_current_active_user),
):
    """Admin endpoint to create or update a plan."""
    require_admin(current_user)
    
    # Validate plan data
    required_fields = ["id", "name", "price", "currency", "billing", "features", "limits"]
    for field in required_fields:
        if field not in plan_data:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Missing required field: {field}")
    
    plan_id = plan_data["id"].lower()
    PlanConfig.PLANS[plan_id] = plan_data
    
    logger.info(f"Admin created/updated plan: {plan_id}")
    return {"message": f"Plan '{plan_id}' created/updated successfully"}



# ==========================================================
# STRIPE BILLING (optional — enabled when STRIPE_SECRET_KEY is set)
# ==========================================================

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
STRIPE_SUCCESS_URL = os.getenv("STRIPE_SUCCESS_URL", "http://localhost:5050/upgrade.html?success=1")
STRIPE_CANCEL_URL = os.getenv("STRIPE_CANCEL_URL", "http://localhost:5050/upgrade.html?canceled=1")
APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:5050")

def _stripe_client():
    if not STRIPE_SECRET_KEY:
        return None
    try:
        import stripe
        stripe.api_key = STRIPE_SECRET_KEY
        return stripe
    except ImportError:
        logger.warning("stripe package not installed")
        return None


@router.post("/checkout")
@limiter.limit("10/minute")
async def create_checkout_session(
    request: Request,
    body: UpgradeRequest,
    current_user: dict = Depends(get_current_active_user),
):
    """
    Create a Stripe Checkout session for a paid plan.
    Falls back to local upgrade when Stripe is not configured (dev only).
    """
    plan = PlanConfig.get_plan(body.plan)
    if not plan:
        raise HTTPException(status_code=400, detail="Invalid plan")
    if plan["id"] == "free":
        raise HTTPException(status_code=400, detail="Use /upgrade/downgrade for free plan")

    stripe = _stripe_client()
    if not stripe:
        # Dev fallback: immediate upgrade without payment
        if os.getenv("DEBUG", "false").lower() == "true":
            user_db.update_user(current_user["username"], {
                "plan": plan["id"],
                "plan_price": plan["price"],
                "upgraded_at": datetime.now(timezone.utc).isoformat(),
            })
            return {
                "status": "upgraded_dev",
                "plan": plan["id"],
                "message": "Stripe not configured — upgraded locally (DEBUG only)",
            }
        raise HTTPException(
            status_code=503,
            detail="Payments not configured. Set STRIPE_SECRET_KEY and stripe_price_id for the plan.",
        )

    price_id = plan.get("stripe_price_id") or os.getenv(f"STRIPE_PRICE_{plan['id'].upper()}")
    if not price_id or str(price_id).startswith("price_pro") and "STRIPE_PRICE" not in os.environ and not os.getenv(f"STRIPE_PRICE_{plan['id'].upper()}"):
        # Allow env override always
        price_id = os.getenv(f"STRIPE_PRICE_{plan['id'].upper()}", price_id)
    if not price_id or price_id in ("price_pro_monthly", "price_team_monthly", "price_enterprise_monthly"):
        # Still placeholder — require real env price id
        env_price = os.getenv(f"STRIPE_PRICE_{plan['id'].upper()}")
        if not env_price:
            raise HTTPException(
                status_code=503,
                detail=f"Set STRIPE_PRICE_{plan['id'].upper()} to your Stripe Price ID",
            )
        price_id = env_price

    try:
        session = stripe.checkout.Session.create(
            mode="subscription",
            customer_email=current_user.get("email"),
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=STRIPE_SUCCESS_URL,
            cancel_url=STRIPE_CANCEL_URL,
            metadata={
                "username": current_user["username"],
                "plan": plan["id"],
            },
            client_reference_id=current_user["username"],
        )
        return {"status": "checkout", "checkout_url": session.url, "session_id": session.id}
    except Exception as e:
        logger.error(f"Stripe checkout error: {e}")
        raise HTTPException(status_code=502, detail=f"Stripe error: {e}")


@router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    """Stripe webhook — activates plan after successful payment."""
    stripe = _stripe_client()
    if not stripe:
        raise HTTPException(status_code=503, detail="Stripe not configured")

    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    try:
        if STRIPE_WEBHOOK_SECRET:
            event = stripe.Webhook.construct_event(payload, sig, STRIPE_WEBHOOK_SECRET)
        else:
            import json
            event = json.loads(payload)
    except Exception as e:
        logger.warning(f"Stripe webhook verify failed: {e}")
        raise HTTPException(status_code=400, detail="Invalid webhook")

    etype = event.get("type") if isinstance(event, dict) else getattr(event, "type", None)
    data = event.get("data", {}).get("object", {}) if isinstance(event, dict) else event.data.object

    if etype in ("checkout.session.completed", "customer.subscription.updated"):
        if isinstance(data, dict):
            meta = data.get("metadata") or {}
            username = meta.get("username") or data.get("client_reference_id")
            plan = meta.get("plan") or "pro"
        else:
            meta = getattr(data, "metadata", None) or {}
            username = (meta.get("username") if hasattr(meta, "get") else None) or getattr(data, "client_reference_id", None)
            plan = (meta.get("plan") if hasattr(meta, "get") else None) or "pro"
        if username:
            user_db.update_user(username, {
                "plan": plan,
                "upgraded_at": datetime.now(timezone.utc).isoformat(),
                "stripe_customer": (data.get("customer") if isinstance(data, dict) else getattr(data, "customer", None)),
            })
            logger.info(f"Stripe activated plan={plan} for {username}")

    if etype in ("customer.subscription.deleted",):
        if isinstance(data, dict):
            meta = data.get("metadata") or {}
            username = meta.get("username")
        else:
            meta = getattr(data, "metadata", None) or {}
            username = meta.get("username") if hasattr(meta, "get") else None
        if username:
            user_db.update_user(username, {"plan": "free", "downgraded_at": datetime.now(timezone.utc).isoformat()})
            logger.info(f"Stripe subscription ended for {username} → free")

    return {"received": True}



# ==========================================================
# PAKISTAN PAYMENTS (Easypaisa + Bank / Mashreq Neo)
# Best free-to-start path: user pays → submits Txn ID → admin approves
# ==========================================================
import json
import threading
from pathlib import Path as _Path

_PAY_LOCK = threading.RLock()
_PAY_FILE = _Path(__file__).resolve().parent.parent / "data" / "payment_requests.json"
_PAY_FILE.parent.mkdir(parents=True, exist_ok=True)


def _payment_config() -> dict:
    """Load receiver details from env (never hardcode secrets in repo)."""
    return {
        "currency": "PKR",
        "pro_price_pkr": int(os.getenv("PRO_PRICE_PKR", "1499")),
        "team_price_pkr": int(os.getenv("TEAM_PRICE_PKR", "3999")),
        "easypaisa_number": os.getenv("EASYPAISA_NUMBER", "").strip(),
        "easypaisa_title": os.getenv("EASYPAISA_TITLE", "").strip(),
        "bank_name": os.getenv("BANK_NAME", "Mashreq Neo").strip(),
        "bank_iban": os.getenv("BANK_IBAN", "").strip(),
        "bank_account_title": os.getenv("BANK_ACCOUNT_TITLE", "").strip(),
        "payment_note": os.getenv(
            "PAYMENT_NOTE",
            "After payment, submit your Transaction ID below. Access is activated after verification.",
        ),
        "whatsapp_support": os.getenv("PAYMENT_WHATSAPP", "").strip(),
    }


def _load_payments() -> list:
    if not _PAY_FILE.exists():
        return []
    try:
        return json.loads(_PAY_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save_payments(rows: list) -> None:
    tmp = _PAY_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    tmp.replace(_PAY_FILE)


def _append_admin_notification(title: str, body: str, kind: str = "payment") -> None:
    """Persist in-app admin notification (read via /upgrade/admin/notifications)."""
    import json as _json
    from pathlib import Path as _P
    path = _P(__file__).resolve().parent.parent / "data" / "admin_notifications.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    if path.exists():
        try:
            rows = _json.loads(path.read_text(encoding="utf-8") or "[]")
        except Exception:
            rows = []
    rows.insert(0, {
        "id": str(__import__("uuid").uuid4()),
        "kind": kind,
        "title": title,
        "body": body,
        "status": "unread",
        "created_at": datetime.now(timezone.utc).isoformat() + "Z",
    })
    path.write_text(_json.dumps(rows[:200], indent=2), encoding="utf-8")


def _notify_admin_new_payment(row: dict) -> None:
    """
    Notify owner of a new payment request (all free, no credit card):
    1. In-app admin notification (always)
    2. Telegram bot (recommended — most reliable)
    3. ntfy.sh push (no account needed)
    4. WhatsApp via CallMeBot (optional; often full / delayed key)
    5. Generic webhook URL
    """
    import urllib.parse
    import urllib.request

    title = f"New payment request — {row.get('username')} → {row.get('plan')}"
    body = (
        f"User: {row.get('username')} ({row.get('email')})\n"
        f"Plan: {row.get('plan')}\n"
        f"Method: {row.get('method')}\n"
        f"Txn ID: {row.get('transaction_id')}\n"
        f"Amount: {row.get('amount_pkr')} PKR\n"
        f"Sender: {row.get('sender_name') or '-'}\n"
        f"Note: {row.get('note') or '-'}\n"
        f"Request ID: {row.get('id')}\n"
        f"Approve in admin panel or POST /upgrade/admin/payment-review"
    )
    try:
        _append_admin_notification(title, body, kind="payment")
    except Exception as e:
        logger.warning(f"In-app admin notify failed: {e}")

    # --- 1) Telegram (best free option) ---
    # Setup: message @BotFather → /newbot → get token
    # Then message your bot once, open:
    #   https://api.telegram.org/bot<TOKEN>/getUpdates
    # Copy your chat.id into TELEGRAM_CHAT_ID
    tg_token = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
    tg_chat = (os.getenv("TELEGRAM_CHAT_ID") or "").strip()
    if tg_token and tg_chat:
        try:
            text = f"🔔 *Vision AI Payment*\n```\n{body}\n```"
            url = f"https://api.telegram.org/bot{tg_token}/sendMessage"
            data = urllib.parse.urlencode({
                "chat_id": tg_chat,
                "text": text,
                "parse_mode": "Markdown",
            }).encode("utf-8")
            req = urllib.request.Request(url, data=data, method="POST")
            with urllib.request.urlopen(req, timeout=12) as resp:
                logger.info(f"Telegram notify status={resp.status} for payment {row.get('id')}")
        except Exception as e:
            logger.warning(f"Telegram notify failed: {e}")

    # --- 2) ntfy.sh (zero signup, free push to phone) ---
    # Install ntfy app → subscribe to a private topic name you invent
    # Set NTFY_TOPIC=your-secret-topic-name
    ntfy_topic = (os.getenv("NTFY_TOPIC") or "").strip()
    if ntfy_topic:
        try:
            ntfy_url = f"https://ntfy.sh/{urllib.parse.quote(ntfy_topic)}"
            data = body.encode("utf-8")
            req = urllib.request.Request(
                ntfy_url,
                data=data,
                headers={
                    "Title": "Vision AI — Payment pending",
                    "Priority": "high",
                    "Tags": "moneybag,warning",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=12) as resp:
                logger.info(f"ntfy notify status={resp.status} for payment {row.get('id')}")
        except Exception as e:
            logger.warning(f"ntfy notify failed: {e}")

    # --- 3) WhatsApp via CallMeBot (optional — often full / key delayed) ---
    # Try numbers: +34 644 10 28 72  or  +34 623 78 64 49
    # Message: I allow callmebot to send me messages
    # If no key in 2 min → wait 24h or send: Recover APIKey
    wa_phone = (os.getenv("PAYMENT_WHATSAPP") or "").strip().lstrip("+")
    wa_key = (os.getenv("CALLMEBOT_APIKEY") or "").strip()
    if wa_phone and wa_key:
        try:
            text = urllib.parse.quote(f"🔔 Vision AI Payment\n{body}")
            url = (
                f"https://api.callmebot.com/whatsapp.php"
                f"?phone={wa_phone}&text={text}&apikey={wa_key}"
            )
            with urllib.request.urlopen(url, timeout=12) as resp:
                logger.info(f"WhatsApp notify status={resp.status} for payment {row.get('id')}")
        except Exception as e:
            logger.warning(f"WhatsApp (CallMeBot) notify failed: {e}")

    # --- 4) Generic webhook (Discord, custom, etc.) ---
    webhook = (os.getenv("PAYMENT_WEBHOOK_URL") or "").strip()
    if webhook:
        try:
            payload = json.dumps({"title": title, "body": body, "payment": row}).encode("utf-8")
            req = urllib.request.Request(
                webhook, data=payload, headers={"Content-Type": "application/json"}, method="POST"
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                logger.info(f"Payment webhook status={resp.status}")
        except Exception as e:
            logger.warning(f"Payment webhook failed: {e}")


class PaymentSubmit(BaseModel):
    plan: str = Field("pro", description="Target plan")
    method: str = Field(..., description="easypaisa | bank")
    transaction_id: str = Field(..., min_length=4, max_length=80)
    amount_pkr: Optional[float] = None
    sender_name: Optional[str] = Field(None, max_length=100)
    note: Optional[str] = Field(None, max_length=300)

    @field_validator("plan")
    @classmethod
    def _plan_ok(cls, v):
        v = (v or "pro").lower()
        if v == "free":
            raise ValueError("Cannot submit payment for free plan")
        # Manual payment flow only supports these plans for now
        allowed = {"pro", "team"}
        if v not in allowed:
            raise ValueError(f"Manual payment only supports: {', '.join(sorted(allowed))}")
        if not PlanConfig.is_valid_plan(v):
            raise ValueError(f"Invalid plan: {v}")
        return v

    @field_validator("method")
    @classmethod
    def _method_ok(cls, v):
        v = (v or "").lower().strip()
        if v not in ("easypaisa", "bank"):
            raise ValueError("method must be easypaisa or bank")
        return v


@router.get("/payment-info")
async def payment_info():
    """Public payment instructions (numbers from env)."""
    cfg = _payment_config()
    # Hide empty fields
    methods = []
    if cfg["easypaisa_number"]:
        methods.append({
            "id": "easypaisa",
            "name": "Easypaisa",
            "number": cfg["easypaisa_number"],
            "title": cfg["easypaisa_title"] or None,
        })
    if cfg["bank_iban"]:
        methods.append({
            "id": "bank",
            "name": cfg["bank_name"] or "Bank transfer",
            "iban": cfg["bank_iban"],
            "title": cfg["bank_account_title"] or None,
        })
    return {
        "currency": cfg["currency"],
        "prices": {
            "pro": cfg["pro_price_pkr"],
            "team": cfg["team_price_pkr"],
        },
        "methods": methods,
        "note": cfg["payment_note"],
        "whatsapp": cfg["whatsapp_support"] or None,
        "configured": len(methods) > 0,
    }


@router.post("/payment-request")
@limiter.limit("10/minute")
async def submit_payment_request(
    request: Request,
    body: PaymentSubmit,
    current_user: dict = Depends(get_current_active_user),
):
    """User submits Easypaisa/bank Txn ID for manual verification."""
    cfg = _payment_config()
    # Server-side price is authoritative — never trust client amount for business logic
    if body.plan == "team":
        expected = cfg["team_price_pkr"]
    else:
        expected = cfg["pro_price_pkr"]

    row = {
        "id": str(__import__("uuid").uuid4()),
        "username": current_user["username"],
        "email": current_user.get("email"),
        "plan": body.plan,
        "method": body.method,
        "transaction_id": body.transaction_id.strip(),
        "amount_pkr": expected,  # always store server price
        "expected_pkr": expected,
        "client_reported_pkr": body.amount_pkr,  # informational only
        "sender_name": body.sender_name,
        "note": body.note,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat() + "Z",
    }
    with _PAY_LOCK:
        rows = _load_payments()
        # prevent exact duplicate txn spam
        if any(r.get("transaction_id") == row["transaction_id"] and r.get("status") == "pending" for r in rows):
            raise HTTPException(status_code=400, detail="This transaction ID is already submitted and pending")
        rows.append(row)
        _save_payments(rows)

    logger.info(f"Payment request {row['id']} from {row['username']} txn={row['transaction_id']}")

    # Admin notification (in-app queue + optional webhook)
    try:
        _notify_admin_new_payment(row)
    except Exception as ne:
        logger.warning(f"Admin payment notify failed: {ne}")

    return {
        "status": "pending",
        "message": "Payment submitted. Please wait for payment confirmation — the owner has been notified and will verify your transaction, then activate your plan.",
        "request_id": row["id"],
        "expected_pkr": expected,
    }


@router.get("/payment-requests")
async def list_my_payment_requests(current_user: dict = Depends(get_current_active_user)):
    """User: list own payment requests."""
    with _PAY_LOCK:
        rows = _load_payments()
    mine = [r for r in rows if r.get("username") == current_user["username"]]
    mine.sort(key=lambda x: x.get("created_at") or "", reverse=True)
    return mine[:20]



@router.get("/admin/notifications")
async def admin_notifications(
    current_user: dict = Depends(get_current_active_user),
    unread_only: bool = False,
):
    require_admin(current_user)
    import json as _json
    from pathlib import Path as _P
    path = _P(__file__).resolve().parent.parent / "data" / "admin_notifications.json"
    rows = []
    if path.exists():
        try:
            rows = _json.loads(path.read_text(encoding="utf-8") or "[]")
        except Exception:
            rows = []
    if unread_only:
        rows = [r for r in rows if r.get("status") == "unread"]
    pending_payments = 0
    with _PAY_LOCK:
        pending_payments = sum(1 for r in _load_payments() if r.get("status") == "pending")
    return {
        "notifications": rows[:50],
        "unread": sum(1 for r in rows if r.get("status") == "unread"),
        "pending_payments": pending_payments,
    }


@router.post("/admin/notifications/read")
async def admin_mark_notifications_read(current_user: dict = Depends(get_current_active_user)):
    require_admin(current_user)
    import json as _json
    from pathlib import Path as _P
    path = _P(__file__).resolve().parent.parent / "data" / "admin_notifications.json"
    if not path.exists():
        return {"status": "ok", "marked": 0}
    rows = _json.loads(path.read_text(encoding="utf-8") or "[]")
    n = 0
    for r in rows:
        if r.get("status") == "unread":
            r["status"] = "read"
            n += 1
    path.write_text(_json.dumps(rows, indent=2), encoding="utf-8")
    return {"status": "ok", "marked": n}


@router.get("/admin/payment-requests")
async def admin_list_payments(current_user: dict = Depends(get_current_active_user)):
    """Admin: list all pending/processed payment requests."""
    require_admin(current_user)
    with _PAY_LOCK:
        rows = _load_payments()
    rows = sorted(rows, key=lambda x: x.get("created_at") or "", reverse=True)
    return rows[:100]


class PaymentReview(BaseModel):
    request_id: str
    action: str = Field(..., description="approve | reject")
    admin_note: Optional[str] = None

    @field_validator("action")
    @classmethod
    def _act(cls, v):
        v = (v or "").lower()
        if v not in ("approve", "reject"):
            raise ValueError("action must be approve or reject")
        return v


@router.post("/admin/payment-review")
async def admin_review_payment(
    body: PaymentReview,
    current_user: dict = Depends(get_current_active_user),
):
    """Admin approves → user plan upgraded; reject → marked rejected."""
    require_admin(current_user)

    with _PAY_LOCK:
        rows = _load_payments()
        found = None
        for r in rows:
            if r.get("id") == body.request_id:
                found = r
                break
        if not found:
            raise HTTPException(status_code=404, detail="Request not found")
        if found.get("status") != "pending":
            raise HTTPException(status_code=400, detail=f"Already {found.get('status')}")

        found["status"] = "approved" if body.action == "approve" else "rejected"
        found["reviewed_at"] = datetime.now(timezone.utc).isoformat() + "Z"
        found["reviewed_by"] = current_user["username"]
        found["admin_note"] = body.admin_note
        _save_payments(rows)

    if body.action == "approve":
        user_db.update_user(found["username"], {
            "plan": found.get("plan") or "pro",
            "upgraded_at": datetime.now(timezone.utc).isoformat(),
            "payment_method": found.get("method"),
            "last_payment_txn": found.get("transaction_id"),
        })
        logger.info(f"Admin approved payment {found['id']} → {found['username']} plan={found.get('plan')}")
        return {"status": "approved", "username": found["username"], "plan": found.get("plan")}

    return {"status": "rejected", "request_id": body.request_id}

# ==========================================================
# HEALTH CHECK
# ==========================================================
@router.get("/health")
async def upgrade_health():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "available_plans": len(PlanConfig.PLANS),
        "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
    }

# ==========================================================
# ADDITIONAL UTILITIES
# ==========================================================
def get_plan_limit(plan_id: str, limit_key: str) -> int:
    """Get a specific limit for a plan."""
    plan = PlanConfig.get_plan(plan_id)
    if not plan:
        return 0
    return plan["limits"].get(limit_key, 0)

def is_unlimited(value: int) -> bool:
    """Check if a limit is unlimited."""
    return value == -1


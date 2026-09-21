"""
backend/routes/payment_routes.py

Stripe Payment Gateway integration.
Handles checkout sessions, webhooks, and subscription management.
"""

import os
import stripe
from flask import Blueprint, request, g
import logging
from backend.config import Config
from backend.models.user_model import UserModel
from backend.models.payment_model import PaymentModel
from backend.utils.clerk_auth import require_auth, optional_auth
from backend.utils.helpers import api_response

logger = logging.getLogger("signbridge.payment")

payment_bp = Blueprint("payment", __name__, url_prefix="/api/payment")

if Config.STRIPE_SECRET_KEY:
    stripe.api_key = Config.STRIPE_SECRET_KEY


@payment_bp.get("/plans")
def get_plans():
    """Returns available pricing tiers."""
    return api_response(data=Config.PLANS)


@payment_bp.post("/create-checkout-session")
@optional_auth
def create_checkout_session():
    """
    Creates a Stripe Checkout Session for subscription or one-time upgrade.
    """
    data = request.get_json() or {}
    plan_id = data.get("plan_id", "pro_monthly")
    clerk_id = g.clerk_id or data.get("clerk_id", "anonymous_user")
    email = data.get("email", "")

    plan = Config.PLANS.get(plan_id)
    if not plan:
        return api_response(success=False, error=f"Invalid plan: {plan_id}", status_code=400)

    # In Dev Mode / Placeholder Keys, simulate checkout session
    if not Config.STRIPE_SECRET_KEY or Config.STRIPE_SECRET_KEY.startswith("sk_test_signbridge"):
        import uuid
        mock_session_id = f"cs_test_mock_{uuid.uuid4().hex[:12]}"
        PaymentModel.record_checkout_session(
            session_id=mock_session_id,
            user_id=clerk_id,
            plan=plan_id,
            amount=plan["price"],
            currency=plan.get("currency", "usd"),
            status="simulated_ready"
        )
        return api_response(
            data={
                "session_id": mock_session_id,
                "checkout_url": f"/#payment-success?session_id={mock_session_id}&plan={plan_id}",
                "simulated": True,
                "plan": plan,
            },
            message="Stripe checkout session initialized (Development Simulation mode)."
        )

    try:
        host_url = request.host_url.rstrip("/")
        mode = "subscription" if "monthly" in plan_id else "payment"

        price_data = {
            "currency": plan.get("currency", "usd"),
            "product_data": {
                "name": plan["name"],
                "description": ", ".join(plan["features"][:2]),
                "tax_code": "txcd_10000000",
            },
            "unit_amount": int(plan["price"] * 100),
        }
        if mode == "subscription":
            price_data["recurring"] = {"interval": "month"}

        session = stripe.checkout.Session.create(
            line_items=[{
                "price_data": price_data,
                "quantity": 1,
            }],
            mode=mode,
            customer_email=email if email else None,
            client_reference_id=clerk_id,
            metadata={"plan_id": plan_id, "clerk_id": clerk_id},
            success_url=f"{host_url}/#payment-success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{host_url}/#payment-cancelled",
        )

        PaymentModel.record_checkout_session(
            session_id=session.id,
            user_id=clerk_id,
            plan=plan_id,
            amount=plan["price"],
            currency=plan.get("currency", "usd")
        )

        return api_response(data={"checkout_url": session.url, "session_id": session.id})

    except Exception as e:
        logger.exception("Stripe checkout creation failed")
        return api_response(success=False, error=str(e), status_code=500)


@payment_bp.post("/simulate-success")
def simulate_success():
    """Development helper to mark a test checkout session as paid and upgrade user."""
    data = request.get_json() or {}
    session_id = data.get("session_id")
    clerk_id = data.get("clerk_id")
    plan_id = data.get("plan_id", "pro_monthly")

    if session_id:
        PaymentModel.update_payment_status(session_id, status="paid")
    if clerk_id:
        UserModel.update_subscription(clerk_id, plan=plan_id)

    return api_response(message=f"Plan upgraded to {plan_id} successfully.")


@payment_bp.post("/webhook")
def stripe_webhook():
    """Handles Stripe webhook events."""
    payload = request.data
    sig_header = request.headers.get("Stripe-Signature", "")

    event = None
    try:
        if Config.STRIPE_WEBHOOK_SECRET and not Config.STRIPE_WEBHOOK_SECRET.startswith("whsec_signbridge"):
            event = stripe.Webhook.construct_event(
                payload, sig_header, Config.STRIPE_WEBHOOK_SECRET
            )
        else:
            import json
            event = json.loads(payload)
    except Exception as e:
        return api_response(success=False, error=f"Webhook error: {e}", status_code=400)

    event_type = event.get("type", "")

    if event_type == "checkout.session.completed":
        session = event.get("data", {}).get("object", {})
        session_id = session.get("id")
        metadata = session.get("metadata", {})
        clerk_id = metadata.get("clerk_id")
        plan_id = metadata.get("plan_id", "pro_monthly")
        cust_id = session.get("customer")

        PaymentModel.update_payment_status(session_id, "paid", stripe_customer_id=cust_id)
        if clerk_id:
            UserModel.update_subscription(clerk_id, plan=plan_id, stripe_customer_id=cust_id)
            logger.info(f"User {clerk_id} upgraded to {plan_id} via Stripe Checkout.")

    return api_response(message="Webhook handled successfully.")

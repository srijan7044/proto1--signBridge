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
    logger.info("Stripe SDK version: %s", getattr(stripe, "_version", "unknown"))
    logger.info("Stripe key type: %s", "test" if Config.STRIPE_SECRET_KEY.startswith("sk_test_") else "live")


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
    clerk_id = g.clerk_id or "anonymous_user"
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
                "checkout_url": f"/app.html?payment=success&session_id={mock_session_id}&plan={plan_id}",
                "simulated": True,
                "plan": plan,
            },
            message="Stripe checkout session initialized (Development Simulation mode)."
        )

    try:
        host_url = request.host_url.rstrip("/")
        is_subscription = plan_id == "pro_monthly"
        mode = "subscription" if is_subscription else "payment"

        price_data = {
            "currency": plan.get("currency", "usd"),
            "product_data": {
                "name": plan["name"],
                "description": ", ".join(plan["features"][:2]),
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
            success_url=f"{host_url}/app.html?session_id={{CHECKOUT_SESSION_ID}}&plan={plan_id}",
            cancel_url=f"{host_url}/app.html?canceled=true",
            **{"managed_payments[enabled]": "false"},
        )

        logger.info(
            "Stripe Checkout Session created: id=%s mode=%s status=%s payment_status=%s currency=%s amount_total=%s url_exists=%s",
            session.id,
            session.mode,
            session.status,
            session.payment_status,
            getattr(session, "currency", None),
            getattr(session, "amount_total", None),
            bool(session.url),
        )

        verified_session = stripe.checkout.Session.retrieve(session.id)
        logger.info(
            "Stripe Checkout Session retrieved: id=%s mode=%s status=%s payment_status=%s currency=%s amount_total=%s url_exists=%s",
            verified_session.id,
            verified_session.mode,
            verified_session.status,
            verified_session.payment_status,
            getattr(verified_session, "currency", None),
            getattr(verified_session, "amount_total", None),
            bool(verified_session.url),
        )

        PaymentModel.record_checkout_session(
            session_id=session.id,
            user_id=clerk_id,
            plan=plan_id,
            amount=plan["price"],
            currency=plan.get("currency", "usd")
        )

        return api_response(data={"checkout_url": session.url, "session_id": session.id})

    except stripe.error.StripeError as e:
        logger.exception(
            "Stripe checkout creation failed: user_message=%s code=%s param=%s http_status=%s",
            getattr(e, "user_message", None),
            getattr(e, "code", None),
            getattr(e, "param", None),
            getattr(e, "http_status", None),
        )
        return api_response(success=False, error=str(e), status_code=500)
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


@payment_bp.post("/verify-session")
@optional_auth
def verify_session():
    """
    Verifies a Stripe Checkout Session by ID.
    In live/test mode, retrieves the session from Stripe's API and checks payment_status.
    In dev/simulation mode, checks the local payment record.
    Updates the user's subscription and payment record upon successful verification.
    """
    data = request.get_json() or {}
    session_id = data.get("session_id")
    if not session_id:
        return api_response(success=False, error="Missing session_id", status_code=400)

    try:
        if Config.STRIPE_SECRET_KEY and not Config.STRIPE_SECRET_KEY.startswith("sk_test_signbridge"):
            session = stripe.checkout.Session.retrieve(session_id)
            if session.payment_status != "paid":
                return api_response(
                    success=False,
                    message="Payment not completed",
                    data={"payment_status": session.payment_status},
                )

            plan_id = session.metadata.get("plan_id", "pro_monthly")
            clerk_id = session.metadata.get("clerk_id") or g.clerk_id
            cust_id = session.get("customer")

            PaymentModel.update_payment_status(session_id, "paid", stripe_customer_id=cust_id)
            if clerk_id:
                UserModel.update_subscription(clerk_id, plan=plan_id, stripe_customer_id=cust_id)
                logger.info(f"User {clerk_id} upgraded to {plan_id} via session verification.")

            return api_response(
                data={
                    "session_id": session.id,
                    "payment_status": session.payment_status,
                    "plan_id": plan_id,
                }
            )

        payment = PaymentModel.get_payment(session_id)
        if payment:
            PaymentModel.update_payment_status(session_id, status="paid")
            plan_id = payment.get("plan", "pro_monthly")
            clerk_id = payment.get("user_id") or g.clerk_id
            if clerk_id and clerk_id != "anonymous_user":
                UserModel.update_subscription(clerk_id, plan=plan_id)
            return api_response(
                data={
                    "session_id": session_id,
                    "payment_status": "paid",
                    "plan_id": plan_id,
                }
            )
        return api_response(success=False, error="Session not found", status_code=404)

    except Exception as e:
        logger.exception("Stripe session verification failed")
        return api_response(success=False, error=str(e), status_code=500)


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


@payment_bp.post("/debug-checkout-session")
@optional_auth
def debug_checkout_session():
    """
    Diagnostic endpoint: creates minimal Stripe Checkout Sessions for testing.
    Use ?type=minimal_payment or ?type=minimal_subscription or ?type=pro_monthly or ?type=lifetime
    """
    data = request.get_json() or {}
    test_type = data.get("type", "minimal_payment")
    clerk_id = g.clerk_id or "debug_user"
    email = data.get("email", "debug@signbridge.app")

    if not Config.STRIPE_SECRET_KEY or Config.STRIPE_SECRET_KEY.startswith("sk_test_signbridge"):
        return api_response(success=False, error="Stripe not configured", status_code=500)

    try:
        host_url = request.host_url.rstrip("/")

        if test_type == "minimal_payment":
            # Absolute minimal valid Checkout Session for one-time payment
            session = stripe.checkout.Session.create(
                line_items=[{
                    "price_data": {
                        "currency": "usd",
                        "product_data": {
                            "name": "SignBridge Test Product",
                            "tax_code": "txcd_10000000",
                        },
                        "unit_amount": 1000,
                    },
                    "quantity": 1,
                }],
                mode="payment",
                success_url=f"{host_url}/app.html?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=f"{host_url}/app.html?canceled=true",
            )

        elif test_type == "minimal_subscription":
            # Minimal valid Checkout Session for subscription
            session = stripe.checkout.Session.create(
                line_items=[{
                    "price_data": {
                        "currency": "usd",
                        "product_data": {
                            "name": "SignBridge Test Subscription",
                            "tax_code": "txcd_10000000",
                        },
                        "unit_amount": 1000,
                        "recurring": {"interval": "month"},
                    },
                    "quantity": 1,
                }],
                mode="subscription",
                success_url=f"{host_url}/app.html?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=f"{host_url}/app.html?canceled=true",
            )

        elif test_type == "pro_monthly":
            plan = Config.PLANS.get("pro_monthly")
            price_data = {
                "currency": plan.get("currency", "usd"),
                "product_data": {
                    "name": plan["name"],
                    "description": ", ".join(plan["features"][:2]),
                    "tax_code": "txcd_10000000",
                },
                "unit_amount": int(plan["price"] * 100),
                "recurring": {"interval": "month"},
            }
            session = stripe.checkout.Session.create(
                line_items=[{"price_data": price_data, "quantity": 1}],
                mode="subscription",
                customer_email=email,
                client_reference_id=clerk_id,
                metadata={"plan_id": "pro_monthly", "clerk_id": clerk_id},
                success_url=f"{host_url}/app.html?session_id={{CHECKOUT_SESSION_ID}}&plan=pro_monthly",
                cancel_url=f"{host_url}/app.html?canceled=true",
            )

        elif test_type == "lifetime":
            plan = Config.PLANS.get("lifetime")
            price_data = {
                "currency": plan.get("currency", "usd"),
                "product_data": {
                    "name": plan["name"],
                    "description": ", ".join(plan["features"][:2]),
                    "tax_code": "txcd_10000000",
                },
                "unit_amount": int(plan["price"] * 100),
            }
            session = stripe.checkout.Session.create(
                line_items=[{"price_data": price_data, "quantity": 1}],
                mode="payment",
                customer_email=email,
                client_reference_id=clerk_id,
                metadata={"plan_id": "lifetime", "clerk_id": clerk_id},
                success_url=f"{host_url}/app.html?session_id={{CHECKOUT_SESSION_ID}}&plan=lifetime",
                cancel_url=f"{host_url}/app.html?canceled=true",
            )

        elif test_type == "pro_monthly_notax":
            # Test pro_monthly without tax_code
            plan = Config.PLANS.get("pro_monthly")
            price_data = {
                "currency": plan.get("currency", "usd"),
                "product_data": {
                    "name": plan["name"],
                    "description": ", ".join(plan["features"][:2]),
                },
                "unit_amount": int(plan["price"] * 100),
                "recurring": {"interval": "month"},
            }
            session = stripe.checkout.Session.create(
                line_items=[{"price_data": price_data, "quantity": 1}],
                mode="subscription",
                customer_email=email,
                client_reference_id=clerk_id,
                metadata={"plan_id": "pro_monthly", "clerk_id": clerk_id},
                success_url=f"{host_url}/app.html?session_id={{CHECKOUT_SESSION_ID}}&plan=pro_monthly",
                cancel_url=f"{host_url}/app.html?canceled=true",
            )

        elif test_type == "pro_monthly_managed_false":
            # Test pro_monthly with managed_payments disabled
            plan = Config.PLANS.get("pro_monthly")
            price_data = {
                "currency": plan.get("currency", "usd"),
                "product_data": {
                    "name": plan["name"],
                    "description": ", ".join(plan["features"][:2]),
                    "tax_code": "txcd_10000000",
                },
                "unit_amount": int(plan["price"] * 100),
                "recurring": {"interval": "month"},
            }
            session = stripe.checkout.Session.create(
                line_items=[{"price_data": price_data, "quantity": 1}],
                mode="subscription",
                customer_email=email,
                client_reference_id=clerk_id,
                metadata={"plan_id": "pro_monthly", "clerk_id": clerk_id},
                success_url=f"{host_url}/app.html?session_id={{CHECKOUT_SESSION_ID}}&plan=pro_monthly",
                cancel_url=f"{host_url}/app.html?canceled=true",
                managed_payments={"enabled": False},
            )

        elif test_type == "pro_monthly_notax":
            # Test pro_monthly without tax_code, managed_payments disabled
            plan = Config.PLANS.get("pro_monthly")
            price_data = {
                "currency": plan.get("currency", "usd"),
                "product_data": {
                    "name": plan["name"],
                    "description": ", ".join(plan["features"][:2]),
                },
                "unit_amount": int(plan["price"] * 100),
                "recurring": {"interval": "month"},
            }
            session = stripe.checkout.Session.create(
                line_items=[{"price_data": price_data, "quantity": 1}],
                mode="subscription",
                customer_email=email,
                client_reference_id=clerk_id,
                metadata={"plan_id": "pro_monthly", "clerk_id": clerk_id},
                success_url=f"{host_url}/app.html?session_id={{CHECKOUT_SESSION_ID}}&plan=pro_monthly",
                cancel_url=f"{host_url}/app.html?canceled=true",
                managed_payments={"enabled": False},
            )

        elif test_type == "lifetime_notax":
            # Test lifetime without tax_code, managed_payments disabled
            plan = Config.PLANS.get("lifetime")
            price_data = {
                "currency": plan.get("currency", "usd"),
                "product_data": {
                    "name": plan["name"],
                    "description": ", ".join(plan["features"][:2]),
                },
                "unit_amount": int(plan["price"] * 100),
            }
            session = stripe.checkout.Session.create(
                line_items=[{"price_data": price_data, "quantity": 1}],
                mode="payment",
                customer_email=email,
                client_reference_id=clerk_id,
                metadata={"plan_id": "lifetime", "clerk_id": clerk_id},
                success_url=f"{host_url}/app.html?session_id={{CHECKOUT_SESSION_ID}}&plan=lifetime",
                cancel_url=f"{host_url}/app.html?canceled=true",
                managed_payments={"enabled": False},
            )

        elif test_type == "pro_monthly_different_tax":
            # Test pro_monthly with a different tax code (Digital Goods)
            plan = Config.PLANS.get("pro_monthly")
            price_data = {
                "currency": plan.get("currency", "usd"),
                "product_data": {
                    "name": plan["name"],
                    "description": ", ".join(plan["features"][:2]),
                    "tax_code": "txcd_30011000",
                },
                "unit_amount": int(plan["price"] * 100),
                "recurring": {"interval": "month"},
            }
            session = stripe.checkout.Session.create(
                line_items=[{"price_data": price_data, "quantity": 1}],
                mode="subscription",
                customer_email=email,
                client_reference_id=clerk_id,
                metadata={"plan_id": "pro_monthly", "clerk_id": clerk_id},
                success_url=f"{host_url}/app.html?session_id={{CHECKOUT_SESSION_ID}}&plan=pro_monthly",
                cancel_url=f"{host_url}/app.html?canceled=true",
            )

        elif test_type == "pro_monthly_price_id":
            # Test pro_monthly using pre-created Price ID
            plan = Config.PLANS.get("pro_monthly")
            session = stripe.checkout.Session.create(
                line_items=[{
                    "price": plan.get("stripe_price_id"),
                    "quantity": 1,
                }],
                mode="subscription",
                customer_email=email,
                client_reference_id=clerk_id,
                metadata={"plan_id": "pro_monthly", "clerk_id": clerk_id},
                success_url=f"{host_url}/app.html?session_id={{CHECKOUT_SESSION_ID}}&plan=pro_monthly",
                cancel_url=f"{host_url}/app.html?canceled=true",
            )

        elif test_type == "lifetime_price_id":
            # Test lifetime using pre-created Price ID
            plan = Config.PLANS.get("lifetime")
            session = stripe.checkout.Session.create(
                line_items=[{
                    "price": plan.get("stripe_price_id"),
                    "quantity": 1,
                }],
                mode="payment",
                customer_email=email,
                client_reference_id=clerk_id,
                metadata={"plan_id": "lifetime", "clerk_id": clerk_id},
                success_url=f"{host_url}/app.html?session_id={{CHECKOUT_SESSION_ID}}&plan=lifetime",
                cancel_url=f"{host_url}/app.html?canceled=true",
            )

        elif test_type == "minimal_payment_no_tax":
            # Minimal payment with managed_payments disabled (raw parameter)
            session = stripe.checkout.Session.create(
                line_items=[{
                    "price_data": {
                        "currency": "usd",
                        "product_data": {
                            "name": "SignBridge Test Product",
                        },
                        "unit_amount": 1000,
                    },
                    "quantity": 1,
                }],
                mode="payment",
                success_url=f"{host_url}/app.html?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=f"{host_url}/app.html?canceled=true",
                **{"managed_payments[enabled]": "false"},
            )

        elif test_type == "minimal_subscription_no_tax":
            # Minimal subscription with managed_payments disabled (raw parameter)
            session = stripe.checkout.Session.create(
                line_items=[{
                    "price_data": {
                        "currency": "usd",
                        "product_data": {
                            "name": "SignBridge Test Subscription",
                        },
                        "unit_amount": 1000,
                        "recurring": {"interval": "month"},
                    },
                    "quantity": 1,
                }],
                mode="subscription",
                success_url=f"{host_url}/app.html?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=f"{host_url}/app.html?canceled=true",
                **{"managed_payments[enabled]": "false"},
            )

        elif test_type == "pro_monthly_no_tax_managed_false":
            # pro_monthly without tax_code, managed_payments disabled
            plan = Config.PLANS.get("pro_monthly")
            price_data = {
                "currency": plan.get("currency", "usd"),
                "product_data": {
                    "name": plan["name"],
                    "description": ", ".join(plan["features"][:2]),
                },
                "unit_amount": int(plan["price"] * 100),
                "recurring": {"interval": "month"},
            }
            session = stripe.checkout.Session.create(
                line_items=[{"price_data": price_data, "quantity": 1}],
                mode="subscription",
                customer_email=email,
                client_reference_id=clerk_id,
                metadata={"plan_id": "pro_monthly", "clerk_id": clerk_id},
                success_url=f"{host_url}/app.html?session_id={{CHECKOUT_SESSION_ID}}&plan=pro_monthly",
                cancel_url=f"{host_url}/app.html?canceled=true",
                **{"managed_payments[enabled]": "false"},
            )

        elif test_type == "lifetime_no_tax_managed_false":
            # lifetime without tax_code, managed_payments disabled
            plan = Config.PLANS.get("lifetime")
            price_data = {
                "currency": plan.get("currency", "usd"),
                "product_data": {
                    "name": plan["name"],
                    "description": ", ".join(plan["features"][:2]),
                },
                "unit_amount": int(plan["price"] * 100),
            }
            session = stripe.checkout.Session.create(
                line_items=[{"price_data": price_data, "quantity": 1}],
                mode="payment",
                customer_email=email,
                client_reference_id=clerk_id,
                metadata={"plan_id": "lifetime", "clerk_id": clerk_id},
                success_url=f"{host_url}/app.html?session_id={{CHECKOUT_SESSION_ID}}&plan=lifetime",
                cancel_url=f"{host_url}/app.html?canceled=true",
                **{"managed_payments[enabled]": "false"},
            )

        else:
            return api_response(success=False, error=f"Unknown test type: {test_type}", status_code=400)

        logger.info(
            "DEBUG Checkout Session: id=%s mode=%s status=%s payment_status=%s currency=%s amount_total=%s url_exists=%s",
            session.id,
            session.mode,
            session.status,
            session.payment_status,
            getattr(session, "currency", None),
            getattr(session, "amount_total", None),
            bool(session.url),
        )

        # Also retrieve to verify
        verified = stripe.checkout.Session.retrieve(session.id)
        logger.info(
            "DEBUG Retrieved Session: id=%s mode=%s status=%s payment_status=%s",
            verified.id,
            verified.mode,
            verified.status,
            verified.payment_status,
        )

        return api_response(data={
            "checkout_url": session.url,
            "session_id": session.id,
            "test_type": test_type,
        })

    except stripe.error.StripeError as e:
        logger.exception(
            "DEBUG Stripe error: user_message=%s code=%s param=%s http_status=%s",
            getattr(e, "user_message", None),
            getattr(e, "code", None),
            getattr(e, "param", None),
            getattr(e, "http_status", None),
        )
        return api_response(success=False, error=str(e), status_code=500)
    except Exception as e:
        logger.exception("DEBUG checkout creation failed")
        return api_response(success=False, error=str(e), status_code=500)

"""
backend/routes/payment_routes.py

Stripe Payment Gateway integration.
Handles checkout sessions, webhooks, and subscription management.
"""

import os
import stripe
from flask import Blueprint, request, g
import logging
from datetime import datetime
from backend.config import Config
from backend.models.user_model import UserModel
from backend.models.payment_model import PaymentModel
from backend.utils.clerk_auth import require_auth, optional_auth
from backend.utils.helpers import api_response
from backend.db import db_manager

logger = logging.getLogger("signbridge.payment")

payment_bp = Blueprint("payment", __name__, url_prefix="/api/payment")

if Config.STRIPE_SECRET_KEY:
    stripe.api_key = Config.STRIPE_SECRET_KEY
    logger.info("Stripe SDK version: %s", getattr(stripe, "_version", "unknown"))
    logger.info("Stripe key type: %s", "test" if Config.STRIPE_SECRET_KEY.startswith("sk_test_") else "live")


@payment_bp.get("/plans")
def get_plans():
    """Returns available pricing tiers with calculated INR prices."""
    return api_response(data=Config.get_all_plans())


@payment_bp.post("/create-checkout-session")
@optional_auth
def create_checkout_session():
    """
    Creates a Stripe Checkout Session for subscription or one-time upgrade.
    Body: {"plan_id": "premium|lifetime|custom_training", "email": "user@example.com"}
    """
    data = request.get_json() or {}
    plan_id = data.get("plan_id", "premium")
    clerk_id = g.clerk_id or "anonymous_user"
    email = data.get("email", "")

    plan = Config.get_plan(plan_id)
    if not plan:
        return api_response(success=False, error=f"Invalid plan: {plan_id}", status_code=400)

    # In Dev Mode / Placeholder Keys, simulate checkout session
    if not Config.STRIPE_SECRET_KEY or Config.STRIPE_SECRET_KEY.startswith("sk_test_signbridge"):
        import uuid
        mock_session_id = f"cs_test_mock_{uuid.uuid4().hex[:12]}"
        
        payment_type = "subscription" if plan_id == "premium" else "one_time"
        PaymentModel.record_checkout_session(
            session_id=mock_session_id,
            user_id=clerk_id,
            plan=plan_id,
            amount=plan["price_usd"],
            currency=plan.get("currency", "usd"),
            status="simulated_ready",
            payment_type=payment_type
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
        
        # Determine mode and payment type
        is_subscription = plan_id == "premium"
        mode = "subscription" if is_subscription else "payment"
        payment_type = "subscription" if is_subscription else "one_time"

        # Use pre-created Price ID if available, otherwise create ad-hoc price
        stripe_price_id = plan.get("stripe_price_id")
        use_price_id = stripe_price_id and not stripe_price_id.startswith("price_signbridge_")

        if use_price_id:
            # Use existing Price ID
            line_items = [{"price": stripe_price_id, "quantity": 1}]
            price_data = None
        else:
            # Create ad-hoc price
            price_data = {
                "currency": plan.get("currency", "usd"),
                "product_data": {
                    "name": plan["name"],
                    "description": plan["description"],
                    "tax_code": "txcd_10000000",
                },
                "unit_amount": int(plan["price_usd"] * 100),
            }
            if mode == "subscription":
                price_data["recurring"] = {"interval": "month"}
            line_items = [{"price_data": price_data, "quantity": 1}]

        try:
            session = stripe.checkout.Session.create(
                line_items=line_items,
                mode=mode,
                customer_email=email if email else None,
                client_reference_id=clerk_id,
                metadata={"plan_id": plan_id, "clerk_id": clerk_id},
                success_url=f"{host_url}/app.html?session_id={{CHECKOUT_SESSION_ID}}&plan={plan_id}",
                cancel_url=f"{host_url}/app.html?canceled=true",
            )
        except stripe.error.InvalidRequestError as price_err:
            if "tax_code" in str(price_err) and use_price_id:
                logger.warning("Pre-created price_id %s missing tax_code; falling back to ad-hoc price_data.", stripe_price_id)
                price_data = {
                    "currency": plan.get("currency", "usd"),
                    "product_data": {
                        "name": plan["name"],
                        "description": plan["description"],
                        "tax_code": "txcd_10000000",
                    },
                    "unit_amount": int(plan["price_usd"] * 100),
                }
                if mode == "subscription":
                    price_data["recurring"] = {"interval": "month"}
                line_items = [{"price_data": price_data, "quantity": 1}]
                session = stripe.checkout.Session.create(
                    line_items=line_items,
                    mode=mode,
                    customer_email=email if email else None,
                    client_reference_id=clerk_id,
                    metadata={"plan_id": plan_id, "clerk_id": clerk_id},
                    success_url=f"{host_url}/app.html?session_id={{CHECKOUT_SESSION_ID}}&plan={plan_id}",
                    cancel_url=f"{host_url}/app.html?canceled=true",
                )
            else:
                raise price_err

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
            amount=plan["price_usd"],
            currency=plan.get("currency", "usd"),
            payment_type=payment_type
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
    plan_id = data.get("plan_id", "premium")

    if session_id:
        PaymentModel.update_payment_status(session_id, status="paid")
    if clerk_id:
        if plan_id == "lifetime":
            UserModel.grant_lifetime_access(clerk_id)
        elif plan_id == "custom_training":
            UserModel.grant_custom_training_access(clerk_id)
        else:
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
    if not session_id or not str(session_id).strip():
        return api_response(success=False, error="Missing session_id in request.", status_code=400)

    session_id = str(session_id).strip()

    def _clean_id(val):
        if not val:
            return None
        if isinstance(val, str):
            return val.strip() or None
        if hasattr(val, "id"):
            return str(val.id)
        if isinstance(val, dict):
            return str(val.get("id")) or None
        return str(val)

    try:
        if Config.STRIPE_SECRET_KEY and not Config.STRIPE_SECRET_KEY.startswith("sk_test_signbridge"):
            stripe.api_key = Config.STRIPE_SECRET_KEY
            try:
                session = stripe.checkout.Session.retrieve(session_id)
            except stripe.error.StripeError as stripe_err:
                logger.warning(f"Stripe session lookup failed for {session_id}: {stripe_err}")
                return api_response(
                    success=False,
                    error=f"Invalid or expired Stripe Checkout Session: {stripe_err.user_message or str(stripe_err)}",
                    status_code=400
                )

            payment_status = getattr(session, "payment_status", None) or (session.get("payment_status") if isinstance(session, dict) else "unpaid")
            if payment_status != "paid":
                return api_response(
                    success=False,
                    error="Payment has not been completed.",
                    data={"payment_status": payment_status},
                    status_code=400
                )

            metadata = getattr(session, "metadata", {}) or {}
            if isinstance(metadata, dict):
                plan_id = metadata.get("plan_id") or "premium"
                session_clerk_id = metadata.get("clerk_id")
            else:
                plan_id = getattr(metadata, "plan_id", "premium") or "premium"
                session_clerk_id = getattr(metadata, "clerk_id", None)

            client_ref = getattr(session, "client_reference_id", None) or (session.get("client_reference_id") if isinstance(session, dict) else None)
            clerk_id = session_clerk_id or client_ref or g.clerk_id

            raw_cust = getattr(session, "customer", None) or (session.get("customer") if isinstance(session, dict) else None)
            raw_sub = getattr(session, "subscription", None) or (session.get("subscription") if isinstance(session, dict) else None)
            
            cust_id = _clean_id(raw_cust)
            sub_id = _clean_id(raw_sub)

            # Ownership security check: ensure session belongs to requesting authenticated user if logged in
            if g.clerk_id and session_clerk_id and g.clerk_id != session_clerk_id:
                logger.warning(f"[SECURITY] Session user mismatch: token user={g.clerk_id}, session user={session_clerk_id}")
                return api_response(
                    success=False,
                    error="Unauthorized: Checkout session belongs to a different account.",
                    status_code=403
                )

            PaymentModel.update_payment_status(
                session_id, "paid", 
                stripe_customer_id=cust_id, 
                stripe_subscription_id=sub_id
            )
            if clerk_id:
                if plan_id == "lifetime":
                    UserModel.grant_lifetime_access(clerk_id, stripe_customer_id=cust_id)
                elif plan_id == "custom_training":
                    UserModel.grant_custom_training_access(clerk_id)
                else:
                    UserModel.update_subscription(
                        clerk_id, 
                        plan=plan_id, 
                        stripe_customer_id=cust_id,
                        stripe_subscription_id=sub_id,
                        stripe_subscription_status="active"
                    )
                logger.info(f"User {clerk_id} granted access for plan '{plan_id}' via verified Checkout Session {session_id}.")

            session_response_id = getattr(session, "id", session_id)
            return api_response(
                data={
                    "session_id": session_response_id,
                    "payment_status": payment_status,
                    "plan_id": plan_id,
                    "verified": True,
                },
                message="Payment verified successfully."
            )

        # Simulation mode fallback
        payment = PaymentModel.get_payment(session_id)
        if payment:
            PaymentModel.update_payment_status(session_id, status="paid")
            plan_id = payment.get("plan", "premium")
            clerk_id = payment.get("user_id") or g.clerk_id
            if clerk_id and clerk_id != "anonymous_user":
                if plan_id == "lifetime":
                    UserModel.grant_lifetime_access(clerk_id)
                elif plan_id == "custom_training":
                    UserModel.grant_custom_training_access(clerk_id)
                else:
                    UserModel.update_subscription(clerk_id, plan=plan_id)
            return api_response(
                data={
                    "session_id": session_id,
                    "payment_status": "paid",
                    "plan_id": plan_id,
                    "verified": True,
                },
                message="Payment verified (development simulation mode)."
            )
        return api_response(success=False, error="Checkout session not found.", status_code=404)

    except Exception as e:
        logger.exception("Unexpected error during Stripe session verification")
        return api_response(success=False, error=f"Internal server error during verification: {str(e)}", status_code=500)


@payment_bp.post("/webhook")
def stripe_webhook():
    """Handles Stripe webhook events for all payment types."""
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
    logger.info(f"Stripe webhook received: {event_type}")

    # Handle checkout.session.completed (one-time payments and initial subscription)
    if event_type == "checkout.session.completed":
        session = event.get("data", {}).get("object", {})
        session_id = session.get("id")
        metadata = session.get("metadata", {})
        clerk_id = metadata.get("clerk_id")
        plan_id = metadata.get("plan_id", "premium")
        cust_id = session.get("customer")
        sub_id = session.get("subscription")

        PaymentModel.update_payment_status(
            session_id, "paid", 
            stripe_customer_id=cust_id, 
            stripe_subscription_id=sub_id
        )
        if clerk_id:
            if plan_id == "lifetime":
                UserModel.grant_lifetime_access(clerk_id, stripe_customer_id=cust_id)
            elif plan_id == "custom_training":
                UserModel.grant_custom_training_access(clerk_id)
                # Also update custom training request
                from backend.models.custom_training_model import CustomTrainingRequest, TrainingPayment
                request_id = metadata.get("request_id")
                if request_id:
                    CustomTrainingRequest.update_payment_info(request_id, session_id, session.get("payment_intent"))
                    TrainingPayment.update_payment_status(session_id, "paid", session.get("payment_intent"))
            else:
                UserModel.update_subscription(
                    clerk_id, 
                    plan=plan_id, 
                    stripe_customer_id=cust_id,
                    stripe_subscription_id=sub_id,
                    stripe_subscription_status="active"
                )
            logger.info(f"User {clerk_id} upgraded to {plan_id} via Stripe Checkout webhook.")

    # Handle subscription lifecycle events
    elif event_type == "customer.subscription.created":
        subscription = event.get("data", {}).get("object", {})
        cust_id = subscription.get("customer")
        sub_id = subscription.get("id")
        status = subscription.get("status")
        current_period_end = subscription.get("current_period_end")

        # Find user by stripe customer id
        user = db_manager.users.find_one({"stripe_customer_id": cust_id})
        if user:
            UserModel.update_subscription(
                user["clerk_id"],
                plan="premium",
                stripe_customer_id=cust_id,
                stripe_subscription_id=sub_id,
                stripe_subscription_status=status,
                stripe_subscription_current_period_end=datetime.utcfromtimestamp(current_period_end) if current_period_end else None
            )
            logger.info(f"Subscription created for user {user['clerk_id']}: {sub_id}")

    elif event_type == "customer.subscription.updated":
        subscription = event.get("data", {}).get("object", {})
        cust_id = subscription.get("customer")
        sub_id = subscription.get("id")
        status = subscription.get("status")
        current_period_end = subscription.get("current_period_end")
        cancel_at_period_end = subscription.get("cancel_at_period_end")

        user = db_manager.users.find_one({"stripe_customer_id": cust_id})
        if user:
            update_data = {
                "stripe_subscription_status": status,
                "stripe_subscription_current_period_end": datetime.utcfromtimestamp(current_period_end) if current_period_end else None,
                "updated_at": datetime.utcnow(),
            }
            if cancel_at_period_end:
                update_data["stripe_cancel_at_period_end"] = True
            db_manager.users.update_one({"clerk_id": user["clerk_id"]}, {"$set": update_data})
            logger.info(f"Subscription updated for user {user['clerk_id']}: {sub_id} status={status}")

    elif event_type == "customer.subscription.deleted":
        subscription = event.get("data", {}).get("object", {})
        cust_id = subscription.get("customer")
        sub_id = subscription.get("id")

        user = db_manager.users.find_one({"stripe_customer_id": cust_id})
        if user:
            # Downgrade to free when subscription is cancelled
            UserModel.revoke_subscription(user["clerk_id"])
            logger.info(f"Subscription cancelled for user {user['clerk_id']}: {sub_id}, downgraded to free")

    elif event_type == "invoice.payment_succeeded":
        invoice = event.get("data", {}).get("object", {})
        cust_id = invoice.get("customer")
        sub_id = invoice.get("subscription")
        amount_paid = invoice.get("amount_paid", 0) / 100

        user = db_manager.users.find_one({"stripe_customer_id": cust_id})
        if user:
            # Record successful renewal payment
            PaymentModel.record_checkout_session(
                session_id=f"invoice_{invoice.get('id')}",
                user_id=user["clerk_id"],
                plan="premium",
                amount=amount_paid,
                currency=invoice.get("currency", "usd"),
                status="paid",
                payment_type="subscription_renewal"
            )
            # Ensure subscription is active
            db_manager.users.update_one(
                {"clerk_id": user["clerk_id"]},
                {"$set": {"stripe_subscription_status": "active", "updated_at": datetime.utcnow()}}
            )
            logger.info(f"Invoice payment succeeded for user {user['clerk_id']}: ${amount_paid}")

    elif event_type == "invoice.payment_failed":
        invoice = event.get("data", {}).get("object", {})
        cust_id = invoice.get("customer")
        attempt_count = invoice.get("attempt_count", 0)

        user = db_manager.users.find_one({"stripe_customer_id": cust_id})
        if user:
            # Mark subscription as past_due after failed payment
            if attempt_count >= 3:
                db_manager.users.update_one(
                    {"clerk_id": user["clerk_id"]},
                    {"$set": {"stripe_subscription_status": "past_due", "updated_at": datetime.utcnow()}}
                )
            logger.warning(f"Invoice payment failed for user {user['clerk_id']}, attempt {attempt_count}")

    return api_response(message="Webhook handled successfully.")


@payment_bp.post("/debug-checkout-session")
@optional_auth
def debug_checkout_session():
    """
    Diagnostic endpoint: creates minimal Stripe Checkout Sessions for testing.
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

        elif test_type == "premium":
            plan = Config.get_plan("premium")
            price_data = {
                "currency": plan.get("currency", "usd"),
                "product_data": {
                    "name": plan["name"],
                    "description": plan["description"],
                    "tax_code": "txcd_10000000",
                },
                "unit_amount": int(plan["price_usd"] * 100),
                "recurring": {"interval": "month"},
            }
            session = stripe.checkout.Session.create(
                line_items=[{"price_data": price_data, "quantity": 1}],
                mode="subscription",
                customer_email=email,
                client_reference_id=clerk_id,
                metadata={"plan_id": "premium", "clerk_id": clerk_id},
                success_url=f"{host_url}/app.html?session_id={{CHECKOUT_SESSION_ID}}&plan=premium",
                cancel_url=f"{host_url}/app.html?canceled=true",
            )

        elif test_type == "lifetime":
            plan = Config.get_plan("lifetime")
            price_data = {
                "currency": plan.get("currency", "usd"),
                "product_data": {
                    "name": plan["name"],
                    "description": plan["description"],
                    "tax_code": "txcd_10000000",
                },
                "unit_amount": int(plan["price_usd"] * 100),
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

        elif test_type == "custom_training":
            plan = Config.get_plan("custom_training")
            price_data = {
                "currency": plan.get("currency", "usd"),
                "product_data": {
                    "name": plan["name"],
                    "description": plan["description"],
                    "tax_code": "txcd_10000000",
                },
                "unit_amount": int(plan["price_usd"] * 100),
            }
            session = stripe.checkout.Session.create(
                line_items=[{"price_data": price_data, "quantity": 1}],
                mode="payment",
                customer_email=email,
                client_reference_id=clerk_id,
                metadata={"plan_id": "custom_training", "clerk_id": clerk_id},
                success_url=f"{host_url}/app.html?session_id={{CHECKOUT_SESSION_ID}}&plan=custom_training",
                cancel_url=f"{host_url}/app.html?canceled=true",
            )

        elif test_type == "premium_price_id":
            plan = Config.get_plan("premium")
            session = stripe.checkout.Session.create(
                line_items=[{"price": plan.get("stripe_price_id"), "quantity": 1}],
                mode="subscription",
                customer_email=email,
                client_reference_id=clerk_id,
                metadata={"plan_id": "premium", "clerk_id": clerk_id},
                success_url=f"{host_url}/app.html?session_id={{CHECKOUT_SESSION_ID}}&plan=premium",
                cancel_url=f"{host_url}/app.html?canceled=true",
            )

        elif test_type == "lifetime_price_id":
            plan = Config.get_plan("lifetime")
            session = stripe.checkout.Session.create(
                line_items=[{"price": plan.get("stripe_price_id"), "quantity": 1}],
                mode="payment",
                customer_email=email,
                client_reference_id=clerk_id,
                metadata={"plan_id": "lifetime", "clerk_id": clerk_id},
                success_url=f"{host_url}/app.html?session_id={{CHECKOUT_SESSION_ID}}&plan=lifetime",
                cancel_url=f"{host_url}/app.html?canceled=true",
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
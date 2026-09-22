"""
backend/models/payment_model.py

Payment and Stripe transaction model for MongoDB.
"""

from datetime import datetime
from backend.db import db_manager

class PaymentModel:
    @staticmethod
    def record_checkout_session(session_id, user_id, plan, amount, currency="usd", status="pending"):
        doc = {
            "session_id": session_id,
            "user_id": user_id,
            "plan": plan,
            "amount": amount,
            "currency": currency,
            "status": status,
            "created_at": datetime.utcnow(),
        }
        res = db_manager.payments.insert_one(doc)
        return str(res.inserted_id)

    @staticmethod
    def update_payment_status(session_id, status, stripe_customer_id=None):
        update = {"status": status, "updated_at": datetime.utcnow()}
        if stripe_customer_id:
            update["stripe_customer_id"] = stripe_customer_id
        db_manager.payments.update_one({"session_id": session_id}, {"$set": update})
        return db_manager.payments.find_one({"session_id": session_id})

    @staticmethod
    def get_user_payments(user_id):
        return list(db_manager.payments.find({"user_id": user_id}))

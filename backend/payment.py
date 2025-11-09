import razorpay
from fastapi import HTTPException, Request
from datetime import datetime, timezone, timedelta
import os
import hmac
import hashlib

# Initialize Razorpay client
razorpay_client = razorpay.Client(auth=(
    os.environ.get('RAZORPAY_KEY_ID', 'rzp_test_dummy'),
    os.environ.get('RAZORPAY_KEY_SECRET', 'dummy_secret')
))

class PaymentService:
    def __init__(self, db):
        self.db = db
    
    async def create_subscription_order(self, user_id: str, plan_type: str):
        """
        Create Razorpay order for subscription
        """
        # Plan amounts in paise
        plans = {
            "monthly": 49900,  # ₹499
            "yearly": 399900,  # ₹3,999
        }
        
        if plan_type not in plans:
            raise HTTPException(status_code=400, detail="Invalid plan type")
        
        amount = plans[plan_type]
        
        # Create Razorpay order
        order = razorpay_client.order.create({
            "amount": amount,
            "currency": "INR",
            "payment_capture": 1,
            "notes": {
                "user_id": user_id,
                "plan_type": plan_type
            }
        })
        
        # Save order to database
        await self.db.payment_orders.insert_one({
            "order_id": order["id"],
            "user_id": user_id,
            "plan_type": plan_type,
            "amount": amount,
            "currency": "INR",
            "status": "created",
            "created_at": datetime.now(timezone.utc)
        })
        
        return {
            "order_id": order["id"],
            "amount": amount,
            "currency": "INR",
            "key_id": os.environ.get('RAZORPAY_KEY_ID', 'rzp_test_dummy')
        }
    
    async def verify_payment(self, payment_data: dict):
        """
        Verify Razorpay payment signature
        """
        try:
            # Verify signature
            razorpay_client.utility.verify_payment_signature({
                'razorpay_order_id': payment_data['order_id'],
                'razorpay_payment_id': payment_data['payment_id'],
                'razorpay_signature': payment_data['signature']
            })
            
            # Get order details
            order = await self.db.payment_orders.find_one({
                "order_id": payment_data['order_id']
            })
            
            if not order:
                raise HTTPException(status_code=404, detail="Order not found")
            
            # Update order status
            await self.db.payment_orders.update_one(
                {"order_id": payment_data['order_id']},
                {"$set": {
                    "payment_id": payment_data['payment_id'],
                    "status": "completed",
                    "completed_at": datetime.now(timezone.utc)
                }}
            )
            
            # Calculate subscription dates
            starts_at = datetime.now(timezone.utc)
            if order["plan_type"] == "monthly":
                ends_at = starts_at + timedelta(days=30)
            else:  # yearly
                ends_at = starts_at + timedelta(days=365)
            
            # Create/update subscription
            await self.db.subscriptions.update_one(
                {"user_id": order["user_id"]},
                {"$set": {
                    "user_id": order["user_id"],
                    "plan_type": order["plan_type"],
                    "status": "active",
                    "payment_id": payment_data['payment_id'],
                    "order_id": payment_data['order_id'],
                    "starts_at": starts_at,
                    "ends_at": ends_at,
                    "updated_at": datetime.now(timezone.utc)
                }},
                upsert=True
            )
            
            # Update user premium status
            await self.db.users.update_one(
                {"id": order["user_id"]},
                {"$set": {"isPremium": True}}
            )
            
            return {"status": "success", "subscription_ends": ends_at.isoformat()}
            
        except razorpay.errors.SignatureVerificationError:
            raise HTTPException(status_code=400, detail="Invalid payment signature")
    
    async def handle_webhook(self, request: Request):
        """
        Handle Razorpay webhooks
        """
        payload = await request.body()
        signature = request.headers.get('X-Razorpay-Signature', '')
        
        # Verify webhook signature
        webhook_secret = os.environ.get('RAZORPAY_WEBHOOK_SECRET', '')
        expected_signature = hmac.new(
            webhook_secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        if signature != expected_signature:
            raise HTTPException(status_code=400, detail="Invalid signature")
        
        event = await request.json()
        
        # Handle different events
        if event['event'] == 'payment.captured':
            payment = event['payload']['payment']['entity']
            # Update payment status
            await self.db.payment_orders.update_one(
                {"order_id": payment['order_id']},
                {"$set": {"webhook_received": True}}
            )
        
        return {"status": "processed"}

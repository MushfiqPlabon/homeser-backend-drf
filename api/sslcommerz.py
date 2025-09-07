import requests
import uuid
from django.conf import settings
from payments.models import Payment, PaymentLog


class SSLCommerzService:
    """Service class for SSLCOMMERZ payment gateway integration"""
    
    def __init__(self):
        self.store_id = settings.SSLCOMMERZ_STORE_ID
        self.store_pass = settings.SSLCOMMERZ_STORE_PASS
        self.is_sandbox = getattr(settings, 'SSLCOMMERZ_IS_SANDBOX', True)
        
        if self.is_sandbox:
            self.base_url = 'https://sandbox.sslcommerz.com'
        else:
            self.base_url = 'https://securepay.sslcommerz.com'

    def create_session(self, order, customer_data):
        """Create payment session with SSLCOMMERZ"""
        
        # Generate unique transaction ID
        tran_id = f"homeser_{order.order_id}_{uuid.uuid4().hex[:8]}"
        
        # Prepare payment data
        payment_data = {
            'store_id': self.store_id,
            'store_passwd': self.store_pass,
            'total_amount': str(order.total),
            'currency': 'BDT',
            'tran_id': tran_id,
            'product_category': 'service',
            'success_url': f"{settings.BACKEND_URL}/api/payments/success/",
            'fail_url': f"{settings.BACKEND_URL}/api/payments/fail/",
            'cancel_url': f"{settings.BACKEND_URL}/api/payments/cancel/",
            'ipn_url': f"{settings.BACKEND_URL}/api/payments/ipn/",
            'cus_name': customer_data.get('name', order.user.get_full_name()),
            'cus_email': order.user.email,
            'cus_add1': customer_data.get('address', ''),
            'cus_city': 'Dhaka',
            'cus_postcode': '1000',
            'cus_country': 'Bangladesh',
            'cus_phone': customer_data.get('phone', ''),
        }

        try:
            # Make request to SSLCOMMERZ
            response = requests.post(
                f"{self.base_url}/gwprocess/v4/api.php",
                data=payment_data,
                timeout=30
            )
            response.raise_for_status()
            result = response.json()

            # Create payment record
            payment = Payment.objects.create(
                order=order,
                transaction_id=tran_id,
                amount=order.total,
                gateway_response=result
            )

            # Log the session creation
            PaymentLog.objects.create(
                payment=payment,
                action='session_created',
                data=result
            )

            if result.get('status') == 'SUCCESS':
                payment.session_key = result.get('sessionkey', '')
                payment.save()
                
                return {
                    'success': True,
                    'gateway_url': result.get('GatewayPageURL') or result.get('redirectGatewayURL'),
                    'sessionkey': result.get('sessionkey'),
                    'transaction_id': tran_id
                }
            else:
                return {
                    'success': False,
                    'error': result.get('failedreason', 'Payment session creation failed')
                }

        except requests.RequestException as e:
            # Log the error
            PaymentLog.objects.create(
                payment=payment if 'payment' in locals() else None,
                action='session_error',
                data={'error': str(e)}
            )
            return {
                'success': False,
                'error': f'Payment gateway error: {str(e)}'
            }

    def validate_payment(self, val_id, tran_id):
        """Validate payment with SSLCOMMERZ"""
        
        validation_data = {
            'val_id': val_id,
            'store_id': self.store_id,
            'store_passwd': self.store_pass
        }

        try:
            response = requests.post(
                f"{self.base_url}/validator/api/validationserverAPI.php",
                data=validation_data,
                timeout=30
            )
            response.raise_for_status()
            result = response.json()

            # Find payment record
            try:
                payment = Payment.objects.get(transaction_id=tran_id)
                payment.validation_response = result
                payment.val_id = val_id
                
                # Log validation
                PaymentLog.objects.create(
                    payment=payment,
                    action='validation_response',
                    data=result
                )

                # Check if validation is successful
                if (result.get('status') == 'VALID' and 
                    result.get('tran_id') == tran_id and
                    float(result.get('amount', 0)) == float(payment.amount)):
                    
                    payment.status = 'completed'
                    payment.bank_tran_id = result.get('bank_tran_id', '')
                    payment.card_type = result.get('card_type', '')
                    payment.card_no = result.get('card_no', '')
                    payment.save()

                    # Update order status
                    order = payment.order
                    order.payment_status = 'paid'
                    order.status = 'confirmed'
                    order.transaction_id = tran_id
                    order.save()

                    return {
                        'success': True,
                        'payment': payment,
                        'order': order
                    }
                else:
                    payment.status = 'failed'
                    payment.save()
                    return {
                        'success': False,
                        'error': 'Payment validation failed'
                    }

            except Payment.DoesNotExist:
                return {
                    'success': False,
                    'error': 'Payment record not found'
                }

        except requests.RequestException as e:
            return {
                'success': False,
                'error': f'Validation error: {str(e)}'
            }
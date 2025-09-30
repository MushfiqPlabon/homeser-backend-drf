# api/services/payment_strategies.py
# SSLCommerz payment strategy implementation


class SSLCommerzPaymentStrategy:
    """SSLCommerz payment strategy"""

    def process_payment(self, order, customer_data):
        """Process payment using SSLCommerz"""
        from api.sslcommerz import SSLCommerzService

        sslcommerz = SSLCommerzService()
        return sslcommerz.create_session(order, customer_data)

    def validate_payment(self, val_id, tran_id):
        """Validate payment using SSLCommerz"""
        from api.sslcommerz import SSLCommerzService

        sslcommerz = SSLCommerzService()
        return sslcommerz.validate_payment(val_id, tran_id)

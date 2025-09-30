# api/services/order_processing_template.py
# Template method pattern for order processing

from abc import ABC, abstractmethod


class OrderProcessingTemplate(ABC):
    """Abstract base class for order processing using template method pattern"""

    def process_order(self, order, user):
        """Template method for order processing"""
        self.validate_order(order, user)
        self.prepare_order(order)
        result = self.execute_processing(order, user)
        self.post_process(order, result)
        return result

    def validate_order(self, order, user):
        """Validate order before processing"""
        if not order:
            raise ValueError("Order is required")
        if not user:
            raise ValueError("User is required")

    def prepare_order(self, order):
        """Prepare order for processing"""
        # Default implementation - can be overridden

    @abstractmethod
    def execute_processing(self, order, user):
        """Execute the actual order processing (to be implemented by subclasses)"""

    def post_process(self, order, result):
        """Post-process after order execution"""
        # Default implementation - can be overridden


class StandardOrderProcessing(OrderProcessingTemplate):
    """Standard order processing implementation"""

    def execute_processing(self, order, user):
        """Execute standard order processing"""
        # Implementation would go here
        return {"status": "processed", "order_id": order.id}


class AdminOrderProcessing(OrderProcessingTemplate):
    """Admin order processing implementation"""

    def validate_order(self, order, user):
        """Validate order with admin privileges"""
        super().validate_order(order, user)
        if not user.is_staff:
            raise PermissionError("Only admin users can process orders this way")

    def execute_processing(self, order, user):
        """Execute admin order processing"""
        # Implementation would go here
        return {"status": "admin_processed", "order_id": order.id}

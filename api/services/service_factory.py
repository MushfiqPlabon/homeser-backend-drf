# api/services/service_factory.py
# Factory pattern for creating service instances

from .category_service import CategoryService
from .order_service import OrderService
from .payment_service import PaymentService
from .review_service import ReviewService
from .service_service import ServiceService
from .user_service import UserService


class ServiceFactory:
    """Factory class for creating service instances"""

    _services = {
        "user": UserService,
        "category": CategoryService,
        "service": ServiceService,
        "order": OrderService,
        "payment": PaymentService,
        "review": ReviewService,
    }

    @classmethod
    def create_service(cls, service_type):
        """Create a service instance based on type"""
        if service_type not in cls._services:
            raise ValueError(f"Unknown service type: {service_type}")

        return cls._services[service_type]

    @classmethod
    def register_service(cls, service_type, service_class):
        """Register a new service type"""
        cls._services[service_type] = service_class

    @classmethod
    def get_available_services(cls):
        """Get list of available service types"""
        return list(cls._services.keys())

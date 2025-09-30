# api/services/admin_service.py
# Specialized service base class for admin operations

from .base_service import BaseService


class AdminService(BaseService):
    """Base service class for admin-only operations"""

    @classmethod
    def _require_admin(cls, user):
        """Check if user has admin privileges"""
        if not user or not user.is_staff:
            raise PermissionError("Only admin users can perform this action")

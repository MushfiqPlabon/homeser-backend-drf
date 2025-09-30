# api/services/abstract_service.py
# Abstract service interface for polymorphic behavior

from abc import ABC, abstractmethod


class AbstractService(ABC):
    """Abstract service interface for polymorphic behavior"""

    @classmethod
    @abstractmethod
    def get_detail(cls, obj_id, user=None):
        """Get detailed information for a specific object"""

    @classmethod
    @abstractmethod
    def create_obj(cls, data, user=None):
        """Create a new object"""

    @classmethod
    @abstractmethod
    def update_obj(cls, obj_id, data, user=None):
        """Update an existing object"""

    @classmethod
    @abstractmethod
    def delete_obj(cls, obj_id, user=None):
        """Delete an object"""

# api/services/review_service.py
# Review service for handling review operations

import logging

from services.models import Review

from .base_service import log_service_method  # Add this import
from .base_service import BaseService

logger = logging.getLogger(__name__)


class ReviewService(BaseService):
    """Service class for handling review-related operations"""

    model = Review

    @classmethod
    @log_service_method
    def get_reviews(cls, user=None, admin_mode=False):
        """Get all reviews.

        Args:
            user (User): User requesting reviews
            admin_mode (bool): Whether to enforce admin permissions

        Returns:
            QuerySet: Review queryset

        Raises:
            PermissionError: If user is not admin and admin_mode is True

        """
        # Check if user is admin when in admin mode
        if admin_mode:
            cls._require_staff_permission(user)

        return super().get_all()

    @classmethod
    @log_service_method
    def get_review_detail(cls, review_id, user=None):
        """Get detailed information for a specific review.

        Args:
            review_id (int): ID of the review
            user (User): User requesting the review (for permission check)

        Returns:
            Review: Review instance

        Raises:
            PermissionError: If user doesn't have permission to view the review

        """
        review = cls.get_by_id(review_id)
        if review is None:
            from django.shortcuts import get_object_or_404

            from services.models import Review

            review = get_object_or_404(Review, id=review_id)

        # Check permissions for non-admin users
        if user and not user.is_staff and review.user != user:
            raise PermissionError("You don't have permission to view this review.")

        return review

    @classmethod
    @log_service_method
    def update_review(cls, review_id, data, user):
        """Update an existing review.

        Args:
            review_id (int): ID of the review to update
            data (dict): Updated review data
            user (User): User updating the review

        Returns:
            Review: Updated review instance

        Raises:
            PermissionError: If user doesn't have permission to update the review

        """
        try:
            # Check permissions
            review = cls.get_or_404(review_id)
            if not (review.user == user or user.is_staff):
                raise PermissionError("You can only edit your own reviews.")

            # Validate review data
            from utils.validation_utils import (validate_rating,
                                                validate_text_length)

            # Validate rating if provided
            if "rating" in data and data["rating"] is not None:
                try:
                    rating = validate_rating(data["rating"])
                    data["rating"] = rating
                except Exception as e:
                    raise ValueError(f"Invalid rating: {e!s}")

            # Validate text if provided
            if data.get("text"):
                try:
                    text = validate_text_length(
                        data["text"],
                        min_length=10,
                        max_length=1000,
                        field_name="Review text",
                    )
                    data["text"] = text
                except Exception as e:
                    raise ValueError(f"Invalid review text: {e!s}")

            # Update review
            review = cls.update(review_id, data, user)

            # Manual logger.info removed

            return review
        except Exception:
            # Manual logger.error removed, decorator handles it
            raise

    @classmethod
    @log_service_method
    def delete_review(cls, review_id, user):
        """Delete a review.

        Args:
            review_id (int): ID of the review to delete
            user (User): User deleting the review

        Returns:
            bool: True if successful

        Raises:
            PermissionError: If user doesn't have permission to delete the review

        """
        try:
            # Check permissions
            review = cls.get_or_404(review_id)
            if not (review.user == user or user.is_staff):
                raise PermissionError("You can only delete your own reviews.")

            # Get review before deletion for cache invalidation

            # Delete review
            result = cls.delete(review_id, user)

            # Manual logger.info removed

            return result
        except Exception:
            # Manual logger.error removed, decorator handles it
            raise

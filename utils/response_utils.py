# utils/response_utils.py
# Shared response formatting utilities

from datetime import datetime

from rest_framework import status
from rest_framework.response import Response


def format_success_response(
    data=None,
    message="Operation completed successfully",
    status_code=status.HTTP_200_OK,
    meta=None,
):
    """Format a standardized success response.

    Args:
        data: The data to include in the response
        message: A descriptive message
        status_code: HTTP status code
        meta: Optional metadata

    Returns:
        Response: Formatted DRF Response

    """
    response_data = {
        "success": True,
        "data": data if data is not None else {},
        "message": message,
        "timestamp": datetime.now().isoformat(),
    }

    if meta:
        response_data["meta"] = meta

    return Response(response_data, status=status_code)


def format_error_response(
    error_code, message, details=None, status_code=status.HTTP_400_BAD_REQUEST,
):
    """Format a standardized error response.

    Args:
        error_code: Error code identifier
        message: Human-readable error message
        details: Optional structured error details
        status_code: HTTP status code

    Returns:
        Response: Formatted DRF Response

    """
    response_data = {
        "success": False,
        "error": {
            "code": error_code,
            "message": message,
        },
        "timestamp": datetime.now().isoformat(),
    }

    if details:
        response_data["error"]["details"] = details

    return Response(response_data, status=status_code)


def format_paginated_response(
    items, page, per_page, total, message="Items retrieved successfully",
):
    """Format a standardized paginated response.

    Args:
        items: List of items
        page: Current page number
        per_page: Items per page
        total: Total number of items
        message: A descriptive message

    Returns:
        Response: Formatted DRF Response

    """
    total_pages = (total + per_page - 1) // per_page

    data = {
        "items": items,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": total_pages,
        },
    }

    return format_success_response(
        data=data, message=message, meta={"pagination": data["pagination"]},
    )

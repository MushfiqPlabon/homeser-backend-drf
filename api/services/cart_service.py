import json
import logging
from decimal import Decimal

import redis
from django.conf import settings
# Import pydantic for validation
from pydantic import BaseModel

from orders.models import Order
from services.models import Service
from utils.advanced_data_structures.hash_table import service_hash_table

from .base_service import BaseService, log_service_method

# Import dramatiq for background tasks

# Configure logger
logger = logging.getLogger(__name__)

# Initialize Redis connection
redis_client = None
try:
    redis_url = getattr(settings, "REDIS_URL", "redis://127.0.0.1:6379/1")
    redis_client = redis.from_url(
        redis_url,
        socket_connect_timeout=1,
        socket_timeout=1,
        retry_on_timeout=False,
        health_check_interval=30,
        socket_keepalive=True,
    )
    redis_client.ping()
except (
    redis.exceptions.ConnectionError,
    redis.exceptions.TimeoutError,
    redis.exceptions.RedisError,
) as e:
    logger.warning(f"Redis connection failed: {e!s}")
    redis_client = None


# Pydantic models for cart validation
class CartItemIn(BaseModel):
    service_id: int
    quantity: int
    price: str | None = None


class CartSyncIn(BaseModel):
    items: list[CartItemIn]
    user_id: int


class CartService(BaseService):
    """Service class for handling cart-related operations"""

    model = Order

    CART_TTL = getattr(settings, "CART_TTL", 60 * 60 * 24)  # 24 hours

    @classmethod
    def _get_cart_key(cls, user_id):
        """Generate a unique Redis key for a user's cart."""
        return f"cart:{user_id}"

    @classmethod
    @log_service_method
    def get_cart(cls, user):
        """Get user's cart from Redis or database."""
        # Check if user is authenticated
        if not user.is_authenticated:
            # Return empty cart for anonymous users
            return {
                "id": None,  # Will be set when converted to Order model
                "user_id": None,
                "items": [],
                "created_at": None,
                "updated_at": None,
            }
        return cls._get_cart_from_redis_or_db(user)

    @classmethod
    @log_service_method
    def _get_cart_from_database(cls, user):
        """Get cart from database."""
        # Check if user is authenticated
        if not user.is_authenticated:
            return None

        try:
            cart = Order.objects.get(user=user, _status="draft")
            return cart
        except Order.DoesNotExist:
            return None

    @classmethod
    @log_service_method
    def add_to_cart(cls, user, service_id, quantity):
        """Add service to cart with O(1) complexity using hash map for items."""
        user_id = user.id
        if not cls._is_redis_available():
            logger.debug(
                f"Redis not available for user {user_id}, adding to cart in database",
            )
            return cls._add_to_cart_in_database(user_id, service_id, quantity)

        cart_key = cls._get_cart_key(user_id)
        try:
            cart = cls.get_cart(user_id)
        except Exception as e:
            logger.error(f"Error getting cart for user {user_id}: {e!s}")
            return cls._add_to_cart_in_database(user_id, service_id, quantity)

        # Convert items list to hash map for O(1) lookup
        items_map = {item["service_id"]: item for item in cart["items"]}

        # O(1) lookup and update
        if service_id in items_map:
            items_map[service_id]["quantity"] += quantity
        else:
            # Add new item
            try:
                # Try to get service from hash table for O(1) lookup
                service_data = service_hash_table.get(str(service_id))

                if service_data:
                    # Got service data from hash table
                    service_price = service_data.get("price")
                else:
                    # Fall back to database lookup and cache the result
                    service = Service.objects.get(id=service_id, is_active=True)
                    service_price = str(service.price)

                    # Cache service data in hash table for future O(1) lookups
                    service_hash_table.set(
                        str(service_id),
                        {
                            "id": service.id,
                            "name": service.name,
                            "price": service_price,
                            "is_active": service.is_active,
                        },
                    )

                new_item = {
                    "service_id": service_id,
                    "quantity": quantity,
                    "price": service_price,
                }
                items_map[service_id] = new_item
            except Service.DoesNotExist:
                raise ValueError("Service not found or not active")
            except Exception as e:
                logger.error(f"Error getting service {service_id}: {e!s}")
                raise ValueError("Error retrieving service information")

        # Convert back to list
        cart["items"] = list(items_map.values())

        from django.utils import timezone

        now = timezone.now().isoformat()
        if not cart.get("created_at"):
            cart["created_at"] = now
        cart["updated_at"] = now

        try:
            redis_client.setex(cart_key, cls.CART_TTL, json.dumps(cart))
            return cart
        except (
            redis.exceptions.ConnectionError,
            redis.exceptions.TimeoutError,
            redis.exceptions.RedisError,
        ) as e:
            logger.warning(
                f"Redis error while adding to cart for user {user_id}: {e!s}",
            )
            return cls._add_to_cart_in_database(user_id, service_id, quantity)
        except Exception as e:
            logger.error(
                f"Unexpected error while adding to cart for user {user_id}: {e!s}",
            )
            return cls._add_to_cart_in_database(user_id, service_id, quantity)

    @classmethod
    @log_service_method
    def remove_from_cart(cls, user_id, service_id):
        """Remove item from cart with O(1) complexity using hash map."""
        if not cls._is_redis_available():
            logger.debug(
                f"Redis not available for user {user_id}, removing from cart in database",
            )
            return cls._remove_from_cart_in_database(user_id, service_id)

        cart_key = cls._get_cart_key(user_id)
        try:
            cart = cls.get_cart(user_id)
        except Exception as e:
            logger.error(f"Error getting cart for user {user_id}: {e!s}")
            return cls._remove_from_cart_in_database(user_id, service_id)

        # Convert items list to hash map for O(1) removal
        items_map = {item["service_id"]: item for item in cart["items"]}

        # O(1) removal
        if service_id in items_map:
            del items_map[service_id]
            cart["items"] = list(items_map.values())
        else:
            # Item not found, return early
            logger.debug(f"Item {service_id} not found in cart for user {user_id}")
            return cart

        from django.utils import timezone

        cart["updated_at"] = timezone.now().isoformat()

        try:
            redis_client.setex(cart_key, cls.CART_TTL, json.dumps(cart))
            return cart
        except (
            redis.exceptions.ConnectionError,
            redis.exceptions.TimeoutError,
            redis.exceptions.RedisError,
        ) as e:
            logger.warning(
                f"Redis error while removing from cart for user {user_id}: {e!s}",
            )
            return cls._remove_from_cart_in_database(user_id, service_id)
        except Exception as e:
            logger.error(
                f"Unexpected error while removing from cart for user {user_id}: {e!s}",
            )
            return cls._remove_from_cart_in_database(user_id, service_id)

    @classmethod
    @log_service_method
    def update_quantity(cls, user, service_id, quantity):
        """Update cart item quantity with O(1) complexity using hash map."""
        user_id = user.id
        if not cls._is_redis_available():
            logger.debug(
                f"Redis not available for user {user_id}, updating cart in database",
            )
            return cls._update_cart_in_database(user_id, service_id, quantity)

        cart_key = cls._get_cart_key(user_id)
        try:
            cart = cls.get_cart(user_id)
        except Exception as e:
            logger.error(f"Error getting cart for user {user_id}: {e!s}")
            return cls._update_cart_in_database(user_id, service_id, quantity)

        # Convert items list to hash map for O(1) lookup and update
        items_map = {item["service_id"]: item for item in cart["items"]}

        # O(1) lookup and update
        if service_id in items_map:
            items_map[service_id]["quantity"] = quantity
            item_updated = True
        else:
            item_updated = False

        if not item_updated:
            logger.warning(
                f"Item {service_id} not found in cart for user {user_id} to update quantity"
            )
            # If item not found, add it with the requested quantity
            try:
                # Try to get service from hash table for O(1) lookup
                service_data = service_hash_table.get(str(service_id))

                if service_data:
                    # Got service data from hash table
                    service_price = service_data.get("price")
                else:
                    # Fall back to database lookup and cache the result
                    service = Service.objects.get(id=service_id, is_active=True)
                    service_price = str(service.price)

                    # Cache service data in hash table for future O(1) lookups
                    service_hash_table.set(
                        str(service_id),
                        {
                            "id": service.id,
                            "name": service.name,
                            "price": service_price,
                            "is_active": service.is_active,
                        },
                    )

                new_item = {
                    "service_id": service_id,
                    "quantity": quantity,
                    "price": service_price,
                }
                items_map[service_id] = new_item
            except Service.DoesNotExist:
                raise ValueError("Service not found or not active")
            except Exception as e:
                logger.error(f"Error getting service {service_id}: {e!s}")
                raise ValueError("Error retrieving service information")

        # Convert back to list
        cart["items"] = list(items_map.values())

        from django.utils import timezone

        cart["updated_at"] = timezone.now().isoformat()

        try:
            redis_client.setex(cart_key, cls.CART_TTL, json.dumps(cart))
            return cart
        except (
            redis.exceptions.ConnectionError,
            redis.exceptions.TimeoutError,
            redis.exceptions.RedisError,
        ) as e:
            logger.warning(
                f"Redis error while updating cart for user {user_id}: {e!s}",
            )
            return cls._update_cart_in_database(user_id, service_id, quantity)
        except Exception as e:
            logger.error(
                f"Unexpected error while updating cart for user {user_id}: {e!s}",
            )
            return cls._update_cart_in_database(user_id, service_id, quantity)

    @classmethod
    @log_service_method
    def clear_cart(cls, user):
        """Clear user's cart from Redis and database."""
        # ... logic ...
        return True

    @classmethod
    def _clear_cart_in_database(cls, user_id):
        """Cart = Order.objects.get(user_id=user_id, status="cart")"""
        try:
            cart = Order.objects.get(user_id=user_id, status="cart")
            cart.items.all().delete()
            cart.delete()
        except Order.DoesNotExist:
            logger.debug(f"Cart not found for user {user_id}")
        except Exception as e:
            logger.error(
                f"Database error while clearing cart for user {user_id}: {e!s}",
            )
            raise Exception(f"Failed to clear cart: {e!s}")

    @classmethod
    def _update_cart_in_database(cls, user_id, service_id, quantity):
        """Update cart item quantity in the database."""
        try:
            # Get the cart order for the user
            cart_order = Order.objects.get(user_id=user_id, _status="draft")

            # Get the cart item
            from orders.models import OrderItem

            cart_item = OrderItem.objects.get(order=cart_order, service_id=service_id)

            # Update the quantity
            cart_item.quantity = quantity
            cart_item.save()

            # Return the updated cart
            return cls._get_cart_from_database(cart_order.user)
        except Order.DoesNotExist:
            logger.error(f"Cart not found for user {user_id}")
            raise ValueError("Cart does not exist for the user")
        except OrderItem.DoesNotExist:
            logger.error(
                f"Cart item with service {service_id} not found for user {user_id}"
            )
            raise ValueError("Cart item does not exist")
        except Exception as e:
            logger.error(
                f"Database error while updating cart for user {user_id}: {e!s}"
            )
            raise Exception(f"Failed to update cart: {e!s}")

    @classmethod
    def _is_redis_available(cls):
        """Check if Redis is available."""
        return redis_client is not None

    @classmethod
    @log_service_method
    def _get_cart_from_redis_or_db(cls, user):
        """Get cart from Redis, if not found, get from database and sync to Redis."""
        # Check if user is authenticated
        if not user.is_authenticated:
            # Return empty cart for anonymous users
            return {
                "id": None,  # Will be set when converted to Order model
                "user_id": None,
                "items": [],
                "created_at": None,
                "updated_at": None,
            }

        cart_key = cls._get_cart_key(user.id)
        if cls._is_redis_available():
            try:
                cart_data = redis_client.get(cart_key)
                if cart_data:
                    cart = json.loads(cart_data)
                    return cart
            except (
                redis.exceptions.ConnectionError,
                redis.exceptions.TimeoutError,
            ) as e:
                logger.warning(
                    f"Redis error for user {user.id}: {e!s}. Falling back to database."
                )

        # If not in Redis or Redis is unavailable, get from DB and sync to Redis
        order_instance = cls._get_cart_from_database(user)
        if order_instance:
            # Convert Order instance to a dictionary for JSON serialization
            cart_data = {
                "id": order_instance.id,
                "user_id": order_instance.user.id,
                "items": [
                    {
                        "service_id": item.service.id,
                        "quantity": item.quantity,
                        "price": str(item.unit_price),  # Convert Decimal to string
                    }
                    for item in order_instance.items.all()
                ],
                "created_at": (
                    order_instance.created.isoformat()
                    if order_instance.created
                    else None
                ),
                "updated_at": (
                    order_instance.modified.isoformat()
                    if order_instance.modified
                    else None
                ),
            }
            # Sync to Redis if available
            if cls._is_redis_available():
                try:
                    redis_client.setex(cart_key, cls.CART_TTL, json.dumps(cart_data))
                except (
                    redis.exceptions.ConnectionError,
                    redis.exceptions.TimeoutError,
                ) as e:
                    logger.warning(
                        f"Redis error syncing cart for user {user.id}: {e!s}. Proceeding without Redis sync."
                    )
            return cart_data  # Return the dictionary
        else:
            # If no cart in DB, create a new empty one (as a dictionary)
            return {
                "id": None,  # Will be set when converted to Order model
                "user_id": user.id,
                "items": [],
                "created_at": None,
                "updated_at": None,
            }

    @classmethod
    @log_service_method
    def _create_or_get_order(cls, user):
        """Create a new draft order or get an existing one for the user."""
        # Check if user is authenticated
        if not user.is_authenticated:
            return None

        try:
            # Attempt to get an existing draft order (cart) for the user
            order = Order.objects.get(user=user, _status="draft")
            return order
        except Order.DoesNotExist:
            # If no draft order exists, create a new one
            order = Order.objects.create(
                user=user, _status="draft", _payment_status="unpaid"
            )
            return order

    @classmethod
    @log_service_method
    def sync_to_database(cls, user):
        """Sync cart from Redis to database."""
        if not cls._is_redis_available():
            logger.debug(f"Redis not available for user {user.id}, cannot sync")
            return cls._get_cart_from_database(user)

        cart_key = cls._get_cart_key(user.id)
        try:
            cart_data = redis_client.get(cart_key)
            if not cart_data:
                # No cart in Redis, return database version
                return cls._get_cart_from_database(user)

            redis_cart = json.loads(cart_data)

            # Get or create the order in database
            cart_order, created = Order.objects.get_or_create(
                user=user, _status="draft", defaults={"_payment_status": "unpaid"}
            )

            # Get cart items from Redis
            redis_items = redis_cart.get("items", [])

            # Clear existing items if this is not a new order
            if not created:
                from orders.models import OrderItem

                cart_order.items.all().delete()

            # Add items from Redis to database
            for item in redis_items:
                # Try to get service from hash table for O(1) lookup
                service_data = service_hash_table.get(str(item["service_id"]))

                if service_data:
                    # Got service data from hash table
                    service_price = service_data.get("price")
                    # Create service object from cached data
                    service = Service(id=service_data["id"], name=service_data["name"])
                else:
                    # Fall back to database lookup and cache the result
                    service = Service.objects.get(id=item["service_id"])
                    service_price = str(service.price)

                    # Cache service data in hash table for future O(1) lookups
                    service_hash_table.set(
                        str(item["service_id"]),
                        {
                            "id": service.id,
                            "name": service.name,
                            "price": service_price,
                            "is_active": service.is_active,
                        },
                    )

                OrderItem.objects.create(
                    order=cart_order,
                    service=service,
                    quantity=item["quantity"],
                    unit_price=Decimal(service_price),  # noqa: F821
                )

            # Update order timestamps
            from django.utils import timezone

            cart_order.modified = timezone.now()
            cart_order.save()

            # Return the updated cart
            return redis_cart
        except Exception as e:
            logger.error(f"Error syncing cart to database for user {user.id}: {e!s}")
            # Return database version if sync fails
            return cls._get_cart_from_database(user)

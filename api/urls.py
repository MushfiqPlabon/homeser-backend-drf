from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .drf_extensions_views import CategoryExtendedViewSet, ServiceExtendedViewSet
from .views.auth import LoginView, RegisterView, TokenRefreshView
from .views.cart import (
    CartView,
    AddToCartView,
    RemoveFromCartView,
    UpdateCartItemQuantityView,
)
from .views.category import CategoryViewSet
from .views.order import (
    CheckoutView,
    AdminOrderViewSet,
    AdminOrderStatusUpdateView,
    UserOrderViewSet,
)
from .views.review import (
    ServiceReviewsView,
    AdminReviewViewSet,
    ReviewDeleteView,
    UserReviewsView,
)
from .views.search import AdvancedSearchView, SearchAnalyticsView, PopularSearchesView
from .views.service import AdminServiceViewSet, ServiceListView, ServiceDetailView
from .views.user import AdminUserViewSet, AdminPromoteUserView, ProfileView
from .views.payment import (
    PaymentIPNView,
    PaymentAnalyticsView,
    PaymentRefundView,
    PaymentDisputeView,
)
from .views.password_reset_views import (
    PasswordResetRequestView,
    PasswordResetConfirmView,
    PasswordResetValidateTokenView,
)
from .views.category import CategoryListView, CategoryDetailView
from .views.analytics import EmailAnalyticsView, SentimentAnalyticsView

# Default router for existing endpoints
router = DefaultRouter()

# Include existing viewsets
router.register(r"staff/services", AdminServiceViewSet, basename="service")
router.register(r"staff/categories", CategoryViewSet, basename="category")
router.register(r"admin/orders", AdminOrderViewSet, basename="admin-order")
router.register(r"admin/reviews", AdminReviewViewSet, basename="admin-review")
router.register(r"admin/users", AdminUserViewSet, basename="admin-user")

# Additional router for user orders
user_orders_router = DefaultRouter()
user_orders_router.register(r"orders", UserOrderViewSet, basename="user-order")

# Define URL patterns - PUBLIC ENDPOINTS FIRST to avoid conflicts
urlpatterns = [
    # Publicly accessible service and category list/detail views (MUST COME BEFORE ROUTER URLS)
    path("services/", ServiceListView.as_view(), name="service-list"),
    path("services/<int:id>/", ServiceDetailView.as_view(), name="service-detail"),
    path("categories/", CategoryListView.as_view(), name="category-list"),
    path("categories/<int:id>/", CategoryDetailView.as_view(), name="category-detail"),
    # Router URLs for admin endpoints
    path("", include(router.urls)),
    path("user/", include(user_orders_router.urls)),  # User-specific endpoints
    # Additional drf-extensions enhanced endpoints
    path(
        "ext/services/",
        ServiceExtendedViewSet.as_view({"get": "list", "post": "create"}),
        name="ext-service-list",
    ),
    path(
        "ext/services/<int:pk>/",
        ServiceExtendedViewSet.as_view(
            {
                "get": "retrieve",
                "put": "update",
                "patch": "partial_update",
                "delete": "destroy",
            },
        ),
        name="ext-service-detail",
    ),
    path(
        "ext/categories/",
        CategoryExtendedViewSet.as_view({"get": "list", "post": "create"}),
        name="ext-category-list",
    ),
    path(
        "ext/categories/<int:pk>/",
        CategoryExtendedViewSet.as_view(
            {
                "get": "retrieve",
                "put": "update",
                "patch": "partial_update",
                "delete": "destroy",
            },
        ),
        name="ext-category-detail",
    ),
    # Admin-specific endpoints
    path(
        "admin/promote/",
        AdminPromoteUserView.as_view(),
        name="admin-promote-user",
    ),
    path(
        "admin/orders/<int:pk>/status/",
        AdminOrderStatusUpdateView.as_view(),
        name="admin-order-status-update",
    ),
    # Authentication endpoints
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    # Password reset endpoints
    path(
        "auth/password-reset/",
        PasswordResetRequestView.as_view(),
        name="password_reset",
    ),
    path(
        "auth/password-reset/confirm/",
        PasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path(
        "auth/password-reset/validate/",
        PasswordResetValidateTokenView.as_view(),
        name="password_reset_validate",
    ),
    # Service reviews endpoint
    path(
        "services/<int:service_id>/reviews/",
        ServiceReviewsView.as_view(),
        name="service-reviews",
    ),
    # User reviews endpoint (ADDED - fixes the missing endpoint)
    path(
        "reviews/user/",
        UserReviewsView.as_view(),
        name="user-reviews",
    ),
    # Review management endpoint
    path(
        "reviews/<int:pk>/",
        ReviewDeleteView.as_view(),
        name="review-detail",
    ),
    # Checkout endpoint
    path("checkout/", CheckoutView.as_view(), name="checkout"),
    # User profile endpoint
    path("profile/", ProfileView.as_view(), name="profile"),
    # Cart endpoints
    path("cart/", CartView.as_view(), name="cart"),
    path("cart/add/", AddToCartView.as_view(), name="add-to-cart"),
    path("cart/remove/", RemoveFromCartView.as_view(), name="remove-from-cart"),
    path(
        "cart/update-quantity/",
        UpdateCartItemQuantityView.as_view(),
        name="update-cart-quantity",
    ),
    # Search endpoints
    path("search/advanced/", AdvancedSearchView.as_view(), name="advanced-search"),
    path("search/analytics/", SearchAnalyticsView.as_view(), name="search-analytics"),
    path("search/popular/", PopularSearchesView.as_view(), name="popular-searches"),
    # Payment endpoints
    path("payments/ipn/", PaymentIPNView.as_view(), name="payment-ipn"),
    path(
        "payments/analytics/", PaymentAnalyticsView.as_view(), name="payment-analytics"
    ),
    path(
        "payments/refund/<str:payment_id>/",
        PaymentRefundView.as_view(),
        name="payment-refund",
    ),
    path(
        "payments/dispute/<str:payment_id>/",
        PaymentDisputeView.as_view(),
        name="payment-dispute",
    ),
    # Analytics endpoints
    path("analytics/email/", EmailAnalyticsView.as_view(), name="email-analytics"),
    path(
        "analytics/sentiment/",
        SentimentAnalyticsView.as_view(),
        name="sentiment-analytics",
    ),
]

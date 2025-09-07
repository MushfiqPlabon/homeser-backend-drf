from django.urls import path
from . import views

urlpatterns = [
    # Authentication
    path('auth/register/', views.RegisterView.as_view(), name='register'),
    path('auth/login/', views.LoginView.as_view(), name='login'),
    
    # Profile
    path('profile/', views.ProfileView.as_view(), name='profile'),
    
    # Services
    path('services/', views.ServiceListView.as_view(), name='service-list'),
    path('services/<int:id>/', views.ServiceDetailView.as_view(), name='service-detail'),
    path('services/<int:service_id>/reviews/', views.ServiceReviewsView.as_view(), name='service-reviews'),
    
    # Cart & Orders
    path('cart/', views.CartView.as_view(), name='cart'),
    path('cart/add/', views.add_to_cart, name='cart-add'),
    path('cart/remove/', views.remove_from_cart, name='cart-remove'),
    path('orders/checkout/', views.checkout, name='checkout'),
    
    # Payments
    path('payments/ipn/', views.payment_ipn, name='payment-ipn'),
    
    # Admin
    path('admin/promote/', views.admin_promote_user, name='admin-promote'),
]
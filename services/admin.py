from django.contrib import admin

from .models import Review, Service, ServiceCategory


@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "created")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "category",
        "price",
        "is_active",
        "created",
    )
    list_filter = ("category", "is_active", "created")
    search_fields = ("name", "short_desc")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "service",
        "rating",
        "is_flagged",
        "flagged_reason",
        "created",
    )
    list_filter = ("rating", "is_flagged", "created")
    search_fields = ("user__email", "service__name", "text")
    readonly_fields = ("created", "modified")

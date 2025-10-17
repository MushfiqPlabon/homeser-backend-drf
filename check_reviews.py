from services.models import Review, Service

service_8 = Service.objects.get(id=8)
print(f"Service 8: {service_8.name}")
reviews = Review.objects.filter(service=service_8)
print(f"Reviews for service 8: {reviews.count()}")
[print(f"  - User: {r.user.username}, Rating: {r.rating}") for r in reviews]
print(f"Total reviews: {Review.objects.count()}")

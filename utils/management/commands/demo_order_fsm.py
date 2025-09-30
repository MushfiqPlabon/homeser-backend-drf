# utils/management/commands/demo_order_fsm.py
# Management command to demonstrate the order state machine

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from orders.models import Order
from services.models import Service

User = get_user_model()


class Command(BaseCommand):
    help = "Demonstrate the order state machine functionality"

    def add_arguments(self, parser):
        parser.add_argument(
            "--order-id",
            type=int,
            help="Order ID to demonstrate with (creates a new order if not provided)",
        )

    def handle(self, *args, **options):
        if options["order_id"]:
            try:
                order = Order.objects.get(id=options["order_id"])
                self.stdout.write(f"Using existing order #{order.id}")
            except Order.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f"Order #{options['order_id']} not found"),
                )
                return
        else:
            # Create a demo order
            user = User.objects.first()
            if not user:
                self.stdout.write(
                    self.style.ERROR("No users found. Please create a user first."),
                )
                return

            service = Service.objects.first()
            if not service:
                self.stdout.write(
                    self.style.ERROR(
                        "No services found. Please create a service first.",
                    ),
                )
                return

            # Create order
            order = Order.objects.create(
                user=user,
                customer_name=f"{user.first_name} {user.last_name}",
                customer_address="123 Test Street",
                customer_phone="+1234567890",
                payment_method="sslcommerz",
            )

            self.stdout.write(self.style.SUCCESS(f"Created demo order #{order.id}"))

        # Show initial state
        self.stdout.write(
            f"Initial state: status={order.status}, payment_status={order.payment_status}",
        )

        # Demonstrate state transitions
        try:
            # Set payment to pending
            order.set_payment_pending()
            order.save()
            self.stdout.write(
                self.style.SUCCESS(
                    f"Success: Set payment to pending - New state: status={order.status}, payment_status={order.payment_status}",
                ),
            )

            # Move from cart to pending
            order.status = "pending"
            order.save()
            self.stdout.write(
                self.style.SUCCESS(
                    f"Success: Set status to pending - New state: status={order.status}, payment_status={order.payment_status}",
                ),
            )

            # Process order
            order.process()
            order.save()
            self.stdout.write(
                self.style.SUCCESS(
                    f"Success: Process order - New state: status={order.status}, payment_status={order.payment_status}",
                ),
            )

            # Ship order
            order.ship()
            order.save()
            self.stdout.write(
                self.style.SUCCESS(
                    f"Success: Ship order - New state: status={order.status}, payment_status={order.payment_status}",
                ),
            )

            # Deliver order
            order.deliver()
            order.save()
            self.stdout.write(
                self.style.SUCCESS(
                    f"Success: Deliver order - New state: status={order.status}, payment_status={order.payment_status}",
                ),
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Failed during transitions - Error: {e}"),
            )

        # Show final state
        self.stdout.write(
            self.style.SUCCESS(
                f"Final state: status={order.status}, payment_status={order.payment_status}",
            ),
        )

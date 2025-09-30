# utils/management/commands/test_email.py
# Management command to test email functionality

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from utils.email.email_service import EmailService

User = get_user_model()


class Command(BaseCommand):
    help = "Test email functionality"

    def add_arguments(self, parser):
        parser.add_argument("--welcome", action="store_true", help="Send welcome email")
        parser.add_argument(
            "--password-reset", action="store_true", help="Send password reset email",
        )
        parser.add_argument(
            "--verification",
            action="store_true",
            help="Send account verification email",
        )
        parser.add_argument(
            "--queue",
            action="store_true",
            help="Queue an email instead of sending immediately",
        )
        parser.add_argument("--to", type=str, help="Recipient email address")
        parser.add_argument(
            "--process-queue", action="store_true", help="Process queued emails",
        )

    def handle(self, *args, **options):
        if options["process_queue"]:
            # Process queued emails
            results = EmailService.process_email_queue()
            self.stdout.write(
                self.style.SUCCESS(
                    f"Processed {results['processed']} emails: "
                    f"{results['sent']} sent, {results['failed']} failed",
                ),
            )
            return

        if not options["to"]:
            self.stdout.write(
                self.style.ERROR("Please provide a recipient email address with --to"),
            )
            return

        # Create a mock user
        user = User(
            username="testuser",
            email=options["to"],
            first_name="Test",
            last_name="User",
        )

        if options["welcome"]:
            # Send welcome email
            if EmailService.send_welcome_email(user):
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Successfully sent welcome email to {options['to']}",
                    ),
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f"Failed to send welcome email to {options['to']}"),
                )
        elif options["password_reset"]:
            # Send password reset email
            reset_url = "https://example.com/reset-password/abc123"
            if EmailService.send_password_reset_email(user, reset_url):
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Successfully sent password reset email to {options['to']}",
                    ),
                )
            else:
                self.stdout.write(
                    self.style.ERROR(
                        f"Failed to send password reset email to {options['to']}",
                    ),
                )
        elif options["verification"]:
            # Send account verification email
            verification_url = "https://example.com/verify-account/xyz789"
            if EmailService.send_account_verification_email(user, verification_url):
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Successfully sent verification email to {options['to']}",
                    ),
                )
            else:
                self.stdout.write(
                    self.style.ERROR(
                        f"Failed to send verification email to {options['to']}",
                    ),
                )
        elif options["queue"]:
            # Queue an email
            if options["password_reset"]:
                reset_url = "https://example.com/reset-password/abc123"
                context = {"user": user, "site_name": "HomeSer", "reset_url": reset_url}
                queued_email = EmailService.queue_email(
                    email_type="password_reset",
                    subject="Password Reset Request",
                    template_name="password_reset",
                    context=context,
                    recipient_list=[user.email],
                    scheduled_at=timezone.now() + timedelta(minutes=1),
                )
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Successfully queued password reset email (ID: {queued_email.id})",
                    ),
                )
            elif options["verification"]:
                verification_url = "https://example.com/verify-account/xyz789"
                context = {
                    "user": user,
                    "site_name": "HomeSer",
                    "verification_url": verification_url,
                }
                queued_email = EmailService.queue_email(
                    email_type="account_verification",
                    subject="Verify Your Account",
                    template_name="account_verification",
                    context=context,
                    recipient_list=[user.email],
                    scheduled_at=timezone.now() + timedelta(minutes=1),
                )
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Successfully queued verification email (ID: {queued_email.id})",
                    ),
                )
            else:
                self.stdout.write(
                    self.style.ERROR(
                        "Please specify which email to queue (e.g., --password-reset or --verification)",
                    ),
                )
        else:
            self.stdout.write(
                self.style.ERROR(
                    "Please specify which email to send (e.g., --welcome, --password-reset, --verification)",
                ),
            )

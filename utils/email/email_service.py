# utils/email/email_service.py
# Email service for sending various types of emails

import json
import logging
from datetime import timedelta

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import models
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)


class EmailTracking(models.Model):
    """Model to track email analytics"""

    EMAIL_TYPES = [
        ("welcome", "Welcome Email"),
        ("order_confirmation", "Order Confirmation"),
        ("payment_confirmation", "Payment Confirmation"),
        ("review_notification", "Review Notification"),
        ("password_reset", "Password Reset"),
        ("account_verification", "Account Verification"),
        ("other", "Other"),
    ]

    email_type = models.CharField(max_length=50, choices=EMAIL_TYPES)
    recipient_email = models.EmailField()
    subject = models.CharField(max_length=200)
    sent_at = models.DateTimeField(auto_now_add=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    opened_at = models.DateTimeField(null=True, blank=True)
    clicked_at = models.DateTimeField(null=True, blank=True)
    is_opened = models.BooleanField(default=False)
    is_clicked = models.BooleanField(default=False)
    error_message = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "email_tracking"
        verbose_name = "Email Tracking"
        verbose_name_plural = "Email Tracking"

    def __str__(self):
        return f"{self.email_type} to {self.recipient_email}"


class EmailQueue(models.Model):
    """Model to queue emails for batch sending"""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("sent", "Sent"),
        ("failed", "Failed"),
    ]

    email_type = models.CharField(max_length=50)
    subject = models.CharField(max_length=200)
    template_name = models.CharField(max_length=100)
    context_data = models.TextField()  # JSON serialized context
    recipient_list = models.TextField()  # JSON serialized list
    from_email = models.EmailField(blank=True, null=True)
    attachments = models.TextField(blank=True, null=True)  # JSON serialized attachments
    created_at = models.DateTimeField(auto_now_add=True)
    scheduled_at = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    retry_count = models.IntegerField(default=0)
    max_retries = models.IntegerField(default=3)
    error_message = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "email_queue"
        verbose_name = "Email Queue"
        verbose_name_plural = "Email Queue"
        indexes = [
            models.Index(fields=["status", "scheduled_at"]),
        ]

    def __str__(self):
        return f"{self.email_type} - {self.subject}"


class EmailAnalytics:
    """Service for email analytics and tracking"""

    @staticmethod
    def get_email_statistics(days=30):
        """Get email statistics for the last N days.

        Args:
            days (int): Number of days to analyze

        Returns:
            dict: Email statistics

        """
        cutoff_date = timezone.now() - timedelta(days=days)

        # Get total emails sent
        total_emails = EmailTracking.objects.filter(sent_at__gte=cutoff_date).count()

        # Get email types distribution
        email_types = (
            EmailTracking.objects.filter(sent_at__gte=cutoff_date)
            .values("email_type")
            .annotate(count=models.Count("email_type"))
            .order_by("-count")
        )

        # Get delivery statistics
        delivered_emails = EmailTracking.objects.filter(
            sent_at__gte=cutoff_date,
            delivered_at__isnull=False,
        ).count()

        # Get open rate
        opened_emails = EmailTracking.objects.filter(
            sent_at__gte=cutoff_date,
            is_opened=True,
        ).count()

        # Get click rate
        clicked_emails = EmailTracking.objects.filter(
            sent_at__gte=cutoff_date,
            is_clicked=True,
        ).count()

        # Get error rate
        error_emails = (
            EmailTracking.objects.filter(
                sent_at__gte=cutoff_date,
                error_message__isnull=False,
            )
            .exclude(error_message="")
            .count()
        )

        return {
            "total_emails": total_emails,
            "delivered_emails": delivered_emails,
            "opened_emails": opened_emails,
            "clicked_emails": clicked_emails,
            "error_emails": error_emails,
            "open_rate": (
                round((opened_emails / total_emails * 100), 2)
                if total_emails > 0
                else 0
            ),
            "click_rate": (
                round((clicked_emails / total_emails * 100), 2)
                if total_emails > 0
                else 0
            ),
            "delivery_rate": (
                round((delivered_emails / total_emails * 100), 2)
                if total_emails > 0
                else 0
            ),
            "error_rate": (
                round((error_emails / total_emails * 100), 2) if total_emails > 0 else 0
            ),
            "email_types_distribution": list(email_types),
        }

    @staticmethod
    def get_email_trend(days=30):
        """Get email sending trend over time.

        Args:
            days (int): Number of days to analyze

        Returns:
            list: Email trend data

        """
        cutoff_date = timezone.now() - timedelta(days=days)

        # Group by date
        from django.db.models import Date

        trend_data = (
            EmailTracking.objects.filter(sent_at__gte=cutoff_date)
            .annotate(date=Date("sent_at"))
            .values("date")
            .annotate(count=models.Count("id"))
            .order_by("date")
        )

        return list(trend_data)


class EmailService:
    """Service for sending various types of emails."""

    @staticmethod
    def _track_email(email_type, recipient_list, subject, error_message=None):
        """Track email for analytics.

        Args:
            email_type (str): Type of email
            recipient_list (list): List of recipient emails
            subject (str): Email subject
            error_message (str): Error message if email failed

        """
        for recipient in recipient_list:
            EmailTracking.objects.create(
                email_type=email_type,
                recipient_email=recipient,
                subject=subject,
                error_message=error_message,
            )

    @staticmethod
    def queue_email(
        email_type,
        subject,
        template_name,
        context,
        recipient_list,
        from_email=None,
        attachments=None,
        scheduled_at=None,
        max_retries=3,
    ):
        """Queue an email for later sending.

        Args:
            email_type (str): Type of email for tracking
            subject (str): Email subject
            template_name (str): Template name (without .html extension)
            context (dict): Context data for template
            recipient_list (list): List of recipient email addresses
            from_email (str): Sender email address (optional)
            attachments (list): List of attachments (optional)
            scheduled_at (datetime): When to send the email (optional)
            max_retries (int): Maximum number of retries if sending fails

        Returns:
            EmailQueue: Queued email instance

        """
        if scheduled_at is None:
            scheduled_at = timezone.now()

        queued_email = EmailQueue.objects.create(
            email_type=email_type,
            subject=subject,
            template_name=template_name,
            context_data=json.dumps(context, default=str),
            recipient_list=json.dumps(recipient_list),
            from_email=from_email,
            attachments=json.dumps(attachments, default=str) if attachments else None,
            scheduled_at=scheduled_at,
            max_retries=max_retries,
        )

        logger.info(f"Email queued: {email_type} to {recipient_list}")
        return queued_email

    @staticmethod
    def process_email_queue(batch_size=50):
        """Process queued emails.

        Args:
            batch_size (int): Number of emails to process in one batch

        Returns:
            dict: Processing results

        """
        # Get pending emails that are scheduled to be sent
        pending_emails = EmailQueue.objects.filter(
            status="pending",
            scheduled_at__lte=timezone.now(),
        )[:batch_size]

        results = {"processed": 0, "sent": 0, "failed": 0}

        for queued_email in pending_emails:
            try:
                queued_email.status = "processing"
                queued_email.save()

                # Deserialize data
                context = json.loads(queued_email.context_data)
                recipient_list = json.loads(queued_email.recipient_list)
                attachments = (
                    json.loads(queued_email.attachments)
                    if queued_email.attachments
                    else None
                )

                # Send email
                success = EmailService._send_email_internal(
                    subject=queued_email.subject,
                    template_name=queued_email.template_name,
                    context=context,
                    recipient_list=recipient_list,
                    from_email=queued_email.from_email,
                    attachments=attachments,
                )

                if success:
                    queued_email.status = "sent"
                    results["sent"] += 1
                # Handle retries
                elif queued_email.retry_count < queued_email.max_retries:
                    queued_email.retry_count += 1
                    queued_email.status = "pending"
                    # Schedule for retry after 5 minutes
                    queued_email.scheduled_at = timezone.now() + timedelta(minutes=5)
                else:
                    queued_email.status = "failed"
                    results["failed"] += 1

                queued_email.save()
                results["processed"] += 1

            except Exception as e:
                logger.error(f"Error processing queued email {queued_email.id}: {e}")
                queued_email.status = "failed"
                queued_email.error_message = str(e)
                queued_email.save()
                results["failed"] += 1

        logger.info(f"Processed email queue: {results}")
        return results

    @staticmethod
    def _send_email_internal(
        subject,
        template_name,
        context,
        recipient_list,
        from_email=None,
        attachments=None,
    ):
        """Internal method to send an email.

        Args:
            subject (str): Email subject
            template_name (str): Template name (without .html extension)
            context (dict): Context data for template
            recipient_list (list): List of recipient email addresses
            from_email (str): Sender email address (optional)
            attachments (list): List of attachments (optional)

        Returns:
            bool: True if email was sent successfully

        """
        try:
            # Render HTML content
            html_content = render_to_string(f"emails/{template_name}.html", context)
            text_content = strip_tags(html_content)

            # Create email message
            from_email = from_email or getattr(
                settings,
                "DEFAULT_FROM_EMAIL",
                "webmaster@localhost",
            )
            msg = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=from_email,
                to=recipient_list,
            )
            msg.attach_alternative(html_content, "text/html")

            # Add attachments if provided
            if attachments:
                for attachment in attachments:
                    msg.attach(
                        attachment["name"],
                        attachment["content"],
                        attachment["mimetype"],
                    )

            # Send email
            msg.send()

            logger.info(f"Email sent successfully to {recipient_list}")
            return True
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return False

    @staticmethod
    def send_email(
        email_type,
        subject,
        template_name,
        context,
        recipient_list,
        from_email=None,
        attachments=None,
    ):
        """Send an email using a template with tracking.

        Args:
            email_type (str): Type of email for tracking
            subject (str): Email subject
            template_name (str): Template name (without .html extension)
            context (dict): Context data for template
            recipient_list (list): List of recipient email addresses
            from_email (str): Sender email address (optional)
            attachments (list): List of attachments (optional)

        Returns:
            bool: True if email was sent successfully

        """
        try:
            success = EmailService._send_email_internal(
                subject=subject,
                template_name=template_name,
                context=context,
                recipient_list=recipient_list,
                from_email=from_email,
                attachments=attachments,
            )

            # Track email
            EmailService._track_email(
                email_type,
                recipient_list,
                subject,
                error_message=None if success else "Failed to send",
            )

            return success
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            # Track email error
            EmailService._track_email(
                email_type,
                recipient_list,
                subject,
                error_message=str(e),
            )
            return False

    @staticmethod
    def send_welcome_email(user):
        """Send a welcome email to a new user.

        Args:
            user (User): User instance

        Returns:
            bool: True if email was sent successfully

        """
        context = {
            "user": user,
            "site_name": "HomeSer",
            "login_url": f"{settings.FRONTEND_URL}/login",
        }

        return EmailService.send_email(
            email_type="welcome",
            subject="Welcome to HomeSer!",
            template_name="welcome",
            context=context,
            recipient_list=[user.email],
        )

    @staticmethod
    def send_order_confirmation_email(order):
        """Send an order confirmation email.

        Args:
            order (Order): Order instance

        Returns:
            bool: True if email was sent successfully

        """
        context = {
            "order": order,
            "user": order.user,
            "site_name": "HomeSer",
            "order_url": f"{settings.FRONTEND_URL}/dashboard/orders/{order.id}",
        }

        return EmailService.send_email(
            email_type="order_confirmation",
            subject=f"Order Confirmation #{order.id}",
            template_name="order_confirmation",
            context=context,
            recipient_list=[order.user.email],
        )

    @staticmethod
    def send_payment_confirmation_email(order):
        """Send a payment confirmation email.

        Args:
            order (Order): Order instance

        Returns:
            bool: True if email was sent successfully

        """
        context = {
            "order": order,
            "user": order.user,
            "site_name": "HomeSer",
            "order_url": f"{settings.FRONTEND_URL}/dashboard/orders/{order.id}",
        }

        return EmailService.send_email(
            email_type="payment_confirmation",
            subject=f"Payment Confirmation for Order #{order.id}",
            template_name="payment_confirmation",
            context=context,
            recipient_list=[order.user.email],
        )

    @staticmethod
    def send_review_notification_email(review):
        """Send a review notification email to the service provider.

        Args:
            review (Review): Review instance

        Returns:
            bool: True if email was sent successfully

        """
        # In a real implementation, we would send this to the service provider
        # For now, we'll send it to the admin email
        admin_email = getattr(settings, "ADMIN_EMAIL", settings.DEFAULT_FROM_EMAIL)

        context = {
            "review": review,
            "service": review.service,
            "user": review.user,
            "site_name": "HomeSer",
            "service_url": f"{settings.FRONTEND_URL}/services/{review.service.id}",
        }

        return EmailService.send_email(
            email_type="review_notification",
            subject=f"New Review for {review.service.name}",
            template_name="review_notification",
            context=context,
            recipient_list=[admin_email],
        )

    @staticmethod
    def send_password_reset_email(user, reset_url):
        """Send a password reset email.

        Args:
            user (User): User instance
            reset_url (str): Password reset URL

        Returns:
            bool: True if email was sent successfully

        """
        context = {"user": user, "site_name": "HomeSer", "reset_url": reset_url}

        return EmailService.send_email(
            email_type="password_reset",
            subject="Password Reset Request",
            template_name="password_reset",
            context=context,
            recipient_list=[user.email],
        )

    @staticmethod
    def send_account_verification_email(user, verification_url):
        """Send an account verification email.

        Args:
            user (User): User instance
            verification_url (str): Account verification URL

        Returns:
            bool: True if email was sent successfully

        """
        context = {
            "user": user,
            "site_name": "HomeSer",
            "verification_url": verification_url,
        }

        return EmailService.send_email(
            email_type="account_verification",
            subject="Verify Your Account",
            template_name="account_verification",
            context=context,
            recipient_list=[user.email],
        )

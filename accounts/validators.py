import re

from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


class CustomPasswordValidator:
    """Custom password validator that enforces stronger password requirements:
    - At least 8 characters long
    - Contains at least one uppercase letter
    - Contains at least one lowercase letter
    - Contains at least one digit
    - Contains at least one special character
    """

    def validate(self, password, user=None):
        # Check minimum length
        if len(password) < 8:
            raise ValidationError(
                _("Password must be at least 8 characters long."),
                code="password_too_short",
            )

        # Check for uppercase letter
        if not re.search(r"[A-Z]", password):
            raise ValidationError(
                _("Password must contain at least one uppercase letter."),
                code="password_no_upper",
            )

        # Check for lowercase letter
        if not re.search(r"[a-z]", password):
            raise ValidationError(
                _("Password must contain at least one lowercase letter."),
                code="password_no_lower",
            )

        # Check for digit
        if not re.search(r"\d", password):
            raise ValidationError(
                _("Password must contain at least one digit."),
                code="password_no_digit",
            )

        # Check for special character
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            raise ValidationError(
                _(
                    'Password must contain at least one special character (!@#$%^&*(),.?":{}|<>).',
                ),
                code="password_no_special",
            )

    def get_help_text(self):
        return _(
            "Your password must be at least 8 characters long and contain at least "
            "one uppercase letter, one lowercase letter, one digit, and one special character.",
        )

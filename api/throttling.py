from rest_framework.throttling import AnonRateThrottle


class LoginAttemptsThrottle(AnonRateThrottle):
    """
    Custom throttling class for login attempts to prevent brute force attacks.
    Limits the number of login attempts from a single IP address.
    """
    scope = 'login_attempts'

    def allow_request(self, request, view):
        # Only apply throttling to POST requests (login attempts)
        if request.method != 'POST':
            return True
        # Only apply to login endpoint specifically
        if 'auth' in request.path and 'token' in request.path:
            return super().allow_request(request, view)
        return True


class RegistrationThrottle(AnonRateThrottle):
    """
    Custom throttling class for registration attempts.
    Limits the number of registration attempts from a single IP address.
    """
    scope = 'registration'
    
    def allow_request(self, request, view):
        # Only apply throttling to POST requests (registrations)
        if request.method != 'POST':
            return True
        # Only apply to register endpoint specifically
        if 'auth' in request.path and 'register' in request.path:
            return super().allow_request(request, view)
        return True
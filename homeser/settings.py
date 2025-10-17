import os
from datetime import timedelta
from pathlib import Path

from decouple import Config, RepositoryEmpty, RepositoryEnv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load configuration with .env file taking precedence over system environment variables
# Check if .env file exists in BASE_DIR
env_file_path = BASE_DIR / ".env"
if env_file_path.exists():
    # To ensure .env file takes precedence over environment variables,
    # we'll create a custom config class that checks the .env file first
    import os

    from decouple import RepositoryEmpty, RepositoryEnv

    class EnvFileFirstConfig:
        def __init__(self, env_file_path):
            self.env_repo = RepositoryEnv(str(env_file_path))
            self.sys_repo = RepositoryEmpty()

        def __call__(self, key, default=None, cast=None):
            # First try to get from .env file
            try:
                value = self.env_repo[key]
                if value is not None:
                    if cast is not None:
                        if cast is bool:
                            value = value.lower() in [
                                "1",
                                "yes",
                                "true",
                                "on",
                                "y",
                                "t",
                            ]
                        elif cast is int:
                            value = int(value)
                        elif cast is float:
                            value = float(value)
                        else:
                            value = cast(value)
                    return value
            except KeyError:
                pass

            # Then try system environment
            try:
                value = self.sys_repo[key]
                if value is not None:
                    if cast is not None:
                        if cast is bool:
                            value = value.lower() in [
                                "1",
                                "yes",
                                "true",
                                "on",
                                "y",
                                "t",
                            ]
                        elif cast is int:
                            value = int(value)
                        elif cast is float:
                            value = float(value)
                        else:
                            value = cast(value)
                    return value
            except KeyError:
                pass

            # Return default if both sources fail
            return default

    config = EnvFileFirstConfig(str(env_file_path))
else:
    # Load only from system environment variables
    config = Config(RepositoryEmpty())

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config("SECRET_KEY", default="django-insecure-change-me-in-production")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config("DEBUG", default=True, cast=bool)

# Control whether to populate advanced structures on startup
POPULATE_ADVANCED_STRUCTURES_ON_STARTUP = config(
    "POPULATE_ADVANCED_STRUCTURES_ON_STARTUP", default=False, cast=bool
)

# Vercel deployment settings
VERCEL_URL = os.environ.get("VERCEL_URL")
if VERCEL_URL:
    ALLOWED_HOSTS = [VERCEL_URL, "localhost", "127.0.0.1", "testserver", ".vercel.app"]
    CSRF_TRUSTED_ORIGINS = [f"https://{VERCEL_URL}", "https://*.vercel.app"]
else:
    ALLOWED_HOSTS = config(
        "ALLOWED_HOSTS", default="localhost,127.0.0.1,testserver"
    ).split(",")


# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "whitenoise.runserver_nostatic",
    "django.contrib.staticfiles",
    # Third party apps
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",  # Required for refresh token rotation
    "corsheaders",
    "cloudinary_storage",
    "cloudinary",
    "drf_spectacular",  # Add this for Swagger/OpenAPI documentation
    "guardian",  # Add django-guardian for RBAC
    "django_ratelimit",  # Add django-ratelimit for rate limiting
    "channels",  # Add channels for WebSocket support
    # Local apps
    "accounts",
    "services",
    "orders",
    "payments",
    "api",
    "utils",
    # Third party apps (added for complexity reduction)
    "model_utils",
    "cachalot",
    "rest_framework_extensions",
    # Additional apps for performance optimization
    # "dramatiq",  # Not used in Vercel deployment - background tasks are synchronous
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "homeser.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            BASE_DIR / "templates",  # Add this line
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "homeser.wsgi.app"
ASGI_APPLICATION = "homeser.asgi.application"

# Database
# Always use SQLite for local development unless explicitly overridden
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    },
}

# Check if we have individual database credentials
# Explicitly check for empty strings since python-dotenv returns None for missing keys
DB_NAME = config("dbname", default=None)
DB_USER = config("user", default=None)
DB_PASSWORD = config("password", default=None)
DB_HOST = config("host", default=None)
DB_PORT = config("port", default=None)

# Only use PostgreSQL if ALL database credentials are provided and not empty/null
# This ensures we don't accidentally try to connect to PostgreSQL with partial credentials
DB_CREDENTIALS = [DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT]
if all(cred is not None and str(cred).strip() != "" for cred in DB_CREDENTIALS):
    DATABASES["default"] = {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": DB_NAME,
        "USER": DB_USER,
        "PASSWORD": DB_PASSWORD,
        "HOST": DB_HOST,
        "PORT": DB_PORT,
    }
elif config("DATABASE_URL", default=None):
    # Fallback to DATABASE_URL if individual credentials are not provided
    import dj_database_url

    DATABASES["default"] = dj_database_url.parse(config("DATABASE_URL"))

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {
            "min_length": 8,
        },
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {
            "min_length": 12,
        },
    },
]

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"  # For production, handles compression and unique filenames for caching.

# Media files
MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Custom User Model
AUTH_USER_MODEL = "accounts.User"

# Authentication backends
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",  # Default backend
    "guardian.backends.ObjectPermissionBackend",  # Django Guardian backend
]

# REST Framework configuration
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",  # Allow read-only access for unauthenticated users
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",  # Add this for DRF Spectacular
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",  # Only return JSON by default
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "100/hour",
        "user": "1000/hour",
        "login_attempts": "5/hour",  # Specific rate limit for login attempts to prevent brute force
        "registration": "5/hour",  # Rate limit for registration attempts
    },
}

# JWT Configuration

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(
        minutes=15
    ),  # Reduced from 60 to 15 minutes for better security
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),  # Reduced from 7 to 1 day
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,  # Add refresh tokens to blacklist after use
    "UPDATE_LAST_LOGIN": True,  # Update last login time
    # Token identifiers for better security
    "SLIDING_TOKEN_REFRESH_EXP_CLAIM": "refresh_exp",
    "SLIDING_TOKEN_LIFETIME": timedelta(minutes=15),
    "SLIDING_TOKEN_REFRESH_LIFETIME": timedelta(days=1),
    # Security enhancements
    "ALGORITHM": "HS256",
    "SIGNING_KEY": config(
        "SIGNING_KEY", default="your-very-secure-signing-key-change-in-production"
    ),
    "VERIFYING_KEY": "",
    "AUDIENCE": None,
    "ISSUER": None,
    "JWK_URL": None,
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "USER_AUTHENTICATION_RULE": "rest_framework_simplejwt.authentication.default_user_authentication_rule",
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
    "TOKEN_TYPE_CLAIM": "token_type",
    "TOKEN_USER_CLASS": "rest_framework_simplejwt.models.TokenUser",
    "JTI_CLAIM": "jti",  # JWT ID for token tracking
    # Custom claims
    "TOKEN_OBTAIN_SERIALIZER": "rest_framework_simplejwt.serializers.TokenObtainPairSerializer",
    "SLIDING_TOKEN_OBTAIN_SERIALIZER": "rest_framework_simplejwt.serializers.TokenObtainSlidingSerializer",
    "SLIDING_TOKEN_REFRESH_SERIALIZER": "rest_framework_simplejwt.serializers.TokenRefreshSlidingSerializer",
    # Cookie settings for httpOnly cookies
    "AUTH_COOKIE": "access_token",  # Name of the access token cookie
    "REFRESH_COOKIE": "refresh_token",  # Name of the refresh token cookie
    "AUTH_COOKIE_DOMAIN": None,  # Domain for the cookie (should be set in production)
    "AUTH_COOKIE_SECURE": config(
        "AUTH_COOKIE_SECURE", default=False, cast=bool
    ),  # Only send over HTTPS
    "AUTH_COOKIE_HTTP_ONLY": True,  # Prevent XSS attacks
    "AUTH_COOKIE_PATH": "/",  # Cookie path
    "AUTH_COOKIE_SAMESITE": "Lax",  # CSRF protection
}

# Email Configuration
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = config("EMAIL_HOST", default="localhost")
EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=True, cast=bool)
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="webmaster@localhost")

# Admin email for notifications
ADMIN_EMAIL = config("ADMIN_EMAIL", default=DEFAULT_FROM_EMAIL)

# Cache timeout from environment or default to 15 minutes
CACHE_TTL = config("CACHE_TTL", default=900, cast=int)

# Cache Configuration - Always use Redis with serverless-optimized settings
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": config("REDIS_URL", default="redis://127.0.0.1:6379/1"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "CONNECTION_POOL_KWARGS": {
                "max_connections": 20,  # Limit connections for serverless
                "retry_on_timeout": True,
                "health_check_interval": 30,
                "socket_keepalive": True,
                "socket_keepalive_options": {},
            },
        },
        "KEY_PREFIX": "homeser",  # Use a consistent key prefix
        "TIMEOUT": CACHE_TTL,
    },
}

# Channel layer configuration for WebSockets
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [config("REDIS_URL", default="redis://127.0.0.1:6379/1")],
            "capacity": 100,  # Number of messages to hold in the channel layer
            "expiry": 60,  # Number of seconds to hold messages
        },
    },
}

# Cachalot settings to automatically cache and invalidate ORM queries
CACHALOT_ENABLED = True
CACHALOT_CACHE = "default"
# Tables that should never be cached (useful for frequently updated tables)
CACHALOT_UNCACHABLE_TABLES = [
    # Add any tables that change frequently and shouldn't be cached
    # Example: 'django_session', 'auth_user' if frequently updated
]

# Additional cachalot settings for optimal performance
CACHALOT_ONLY_CACHABLE_TABLES = [
    # If we want to limit caching to only specific tables, we can add them here
    # This is commented out to cache all tables except those in CACHALOT_UNCACHABLE_TABLES
]

# Timeout for cached queries in seconds (optional, can be specified per query)
# CACHALOT_TIMEOUT = 300  # 5 minutes

# Redis configuration for direct connection
if not VERCEL_URL:
    REDIS_URL = config("REDIS_URL", default="redis://127.0.0.1:6379/1")

# CORS settings
CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS",
    default="http://localhost:3000,http://127.0.0.1:3000",
).split(",")

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_ALL_ORIGINS = False  # Disable for security - specific origins are configured in CORS_ALLOWED_ORIGINS

# Cloudinary configuration
CLOUDINARY_STORAGE = {
    "CLOUD_NAME": config("CLOUDINARY_CLOUD_NAME", default=""),
    "API_KEY": config("CLOUDINARY_API_KEY", default=""),
    "API_SECRET": config("CLOUDINARY_API_SECRET", default=""),
}

if CLOUDINARY_STORAGE["CLOUD_NAME"]:
    DEFAULT_FILE_STORAGE = "cloudinary_storage.storage.MediaCloudinaryStorage"

# Security Headers
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=False, cast=bool)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = config("SESSION_COOKIE_SECURE", default=False, cast=bool)
CSRF_COOKIE_SECURE = config("CSRF_COOKIE_SECURE", default=False, cast=bool)
X_FRAME_OPTIONS = "DENY"

# Additional Security Headers
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

# SSLCOMMERZ Configuration
SSLCOMMERZ_STORE_ID = config("SSLCOMMERZ_STORE_ID", default="testbox")
SSLCOMMERZ_STORE_PASS = config("SSLCOMMERZ_STORE_PASS", default="qwerty")
SSLCOMMERZ_IS_SANDBOX = config("SSLCOMMERZ_IS_SANDBOX", default=True, cast=bool)

# Frontend and Backend URLs
FRONTEND_URL = config("FRONTEND_URL", default="http://localhost:3000")
BACKEND_URL = config("BACKEND_URL", default="http://localhost:8000")

# DRF Spectacular settings for Swagger/OpenAPI documentation
SPECTACULAR_SETTINGS = {
    "TITLE": "HomeSer API",
    "DESCRIPTION": """
        # HomeSer API Documentation
    
        A comprehensive household service platform API that allows users to:
        - Browse various household services
        - Register and login to user accounts
        - Book services and manage orders
        - Leave reviews for completed services
        
        ## Authentication
        - Public endpoints (e.g., service browsing) don't require authentication
        - Private endpoints (e.g., booking, order management) require JWT tokens
        - Staff endpoints require admin privileges
        
        ## Getting Started
        1. Register a new account or login with existing credentials
        2. Use the JWT tokens in the authorization header for private endpoints
        3. Browse services and make bookings as needed
    """,
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    # OTHER SETTINGS
}

# Guardian settings
GUARDIAN_RAISE_403 = True

# Logging Configuration
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "api": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "api.services": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
        "api.lock_free_cart": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "utils": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

# Dramatiq Configuration - Not used in Vercel deployment, background tasks are synchronous
# DRAMATIQ_BROKER = {
#     "BROKER": "dramatiq.brokers.redis.RedisBroker",
#     "OPTIONS": {
#         "url": config.get("REDIS_URL", "redis://127.0.0.1:6379/2"),
#     },
#     "MIDDLEWARE": [
#         "dramatiq.middleware.AgeLimit",
#         "dramatiq.middleware.TimeLimit",
#         "dramatiq.middleware.Callbacks",
#         "dramatiq.middleware.Retries",
#         "django_dramatiq.middleware.DbConnectionsMiddleware",
#     ]
# }
#
# DRAMATIQ_WORKER = {
#     "MIDDLEWARE": [
#         "dramatiq.middleware.AgeLimit",
#         "dramatiq.middleware.TimeLimit",
#         "dramatiq.middleware.Callbacks",
#         "dramatiq.middleware.Retries",
#         "django_dramatiq.middleware.DbConnectionsMiddleware",
#     ]
# }

# Opentelemetry Configuration
if config("ENABLE_OPENTELEMETRY", default=False, cast=bool):
    INSTALLED_APPS += ["opentelemetry.instrumentation.django"]

# Sentry Configuration
if config("SENTRY_DSN", default=None):
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration

    sentry_sdk.init(
        dsn=config("SENTRY_DSN"),
        integrations=[DjangoIntegration()],
        # Set traces_sample_rate to 1.0 to capture 100%
        # of transactions for performance monitoring.
        # We recommend adjusting this value in production.
        traces_sample_rate=1.0,
        # If you wish to associate users to errors (assuming you are using
        # django.contrib.auth) you may enable sending PII data.
        send_default_pii=True,
    )

# MeiliSearch Configuration - Not used in Vercel deployment, using PostgreSQL full-text search instead
# MEILISEARCH_CONFIG = {
#     "host": config.get("MEILISEARCH_HOST", "http://127.0.0.1:7700"),
#     "api_key": config.get("MEILISEARCH_MASTER_KEY", "masterKey"),
# }

# RedisBloom Configuration
if not VERCEL_URL:
    REDISBLOOM_HOST = config("REDISBLOOM_HOST", default="redis://127.0.0.1:6379")

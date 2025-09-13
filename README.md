# HomeSer Backend

A comprehensive household service platform backend built with Django REST Framework.

## Features

- User authentication with JWT tokens
- User profile management
- Service catalog with categories and reviews
- Shopping cart functionality
- Order management
- SSLCOMMERZ payment gateway integration
- Admin user promotion system
- Review and rating system

## Quick Start

### Prerequisites

- Python 3.8+
- [uv](https://docs.astral.sh/uv/) (Python package manager and project manager)

### Installation

1. **Install dependencies:**
   ```bash
   uv sync
   ```

2. **Set up environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Run migrations:**
   ```bash
   uv run python manage.py migrate
   ```

4. **Create superuser:**
   ```bash
   uv run python manage.py createsuperuser
   ```

5. **Load sample data (optional):**
   ```bash
   uv run python manage.py load_sample_data
   ```

6. **Start development server:**
   ```bash
   uv run python manage.py runserver
   ```

## API Endpoints

### Authentication
- `POST /api/auth/register/` - User registration
- `POST /api/auth/login/` - User login

### Profile
- `GET /api/profile/` - Get user profile
- `PATCH /api/profile/` - Update user profile

### Services
- `GET /api/services/` - List services (supports `?ordering=-avg_rating`)
- `GET /api/services/{id}/` - Service detail
- `GET /api/services/{id}/reviews/` - Service reviews
- `POST /api/services/{id}/reviews/` - Create review (requires purchase)

### Cart & Orders
- `GET /api/cart/` - Get user's cart
- `POST /api/cart/add/` - Add service to cart
- `POST /api/cart/remove/` - Remove service from cart
- `POST /api/orders/checkout/` - Checkout and create payment session

### Payments
- `POST /api/payments/ipn/` - SSLCOMMERZ IPN handler

### Admin
- `POST /api/admin/promote/` - Promote user to admin (admin only)

## Environment Variables

Create a `.env` file with the following variables:

```env
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
# DATABASE_URL=postgresql://user:password@localhost:5432/homeser  # Optional, for PostgreSQL
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
# CLOUDINARY_CLOUD_NAME=your-cloud-name  # Optional
# CLOUDINARY_API_KEY=your-api-key  # Optional
# CLOUDINARY_API_SECRET=your-api-secret  # Optional
SSLCOMMERZ_STORE_ID=testbox
SSLCOMMERZ_STORE_PASS=qwerty
SSLCOMMERZ_IS_SANDBOX=True
FRONTEND_URL=http://localhost:3000
BACKEND_URL=http://localhost:8000
```

## Testing

Run the test suite:
```bash
uv run python manage.py test
```

## SSLCOMMERZ Integration

The platform integrates with SSLCOMMERZ payment gateway:

- **Sandbox Mode**: Uses test credentials by default
- **Test Cards**: 
  - VISA: `4111111111111111` CVV `111` Exp `12/25`
  - MasterCard: `5111111111111111` CVV `111` Exp `12/25`
  - OTP: `111111` or `123456`

## Admin Interface

Access the Django admin at `http://localhost:8000/admin/` with the created admin user.

## Sample Data

The application comes with sample data for testing:
- Service categories: Cleaning, Plumbing, Electrical, Gardening, Painting
- Services: House Deep Cleaning, Bathroom Cleaning, Pipe Repair, etc.
- Sample users: john_doe, jane_smith, mike_johnson
- Reviews for services

## 🐛 Troubleshooting

### Common Issues

**Database Not Populating / Empty API Responses (e.g., /api/services/ returns empty JSON)**

This often happens if your database is not correctly set up or populated, or if a system-wide environment variable is interfering.

1.  **Check for `DATABASE_URL` environment variable:**
    If you intend to use SQLite for local development, ensure the `DATABASE_URL` environment variable is NOT set in your system. A system-wide `DATABASE_URL` will override your `settings.py` and attempt to connect to a PostgreSQL database.

    *   **To unset it temporarily in your current terminal session:**
        *   **Windows (Command Prompt):** `set DATABASE_URL=`
        *   **Windows (PowerShell):** `Remove-Item Env:DATABASE_URL`
        *   **Linux/macOS:** `unset DATABASE_URL`

2.  **Clear and Repopulate the Database:**
    Ensure your Django server is **STOPPED** before performing these steps to avoid file locks.

    *   **Delete the SQLite database file:**
        ```bash
        rm db.sqlite3
        ```
        (This clears all data and migration history for SQLite)

    *   **Run database migrations:**
        ```bash
        uv run python manage.py migrate
        ```
        (This creates the `db.sqlite3` file and sets up the schema)

    *   **Create a superuser (interactive):**
        ```bash
        uv run python manage.py createsuperuser
        ```
        (Follow the prompts to create your admin user)

    *   **Load sample data:**
        ```bash
        uv run python manage.py load_sample_data
        ```
        (This runs the custom management command to populate categories, services, etc.)

    *   **Restart your Django server** and check the API endpoint again.

**CORS Errors:**
```python
# In settings.py, ensure frontend URL is in CORS_ALLOWED_ORIGINS
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "https://your-frontend-domain.vercel.app",
]
```

**API Connection Failed:**
```bash
# Check if backend is running
curl http://localhost:8000/api/services/
```

## Performance Optimizations

The HomeSer backend includes several performance optimizations:

### Caching
- Redis caching for frequently accessed data (services, service details)
- Configurable cache timeout (default: 15 minutes)
- Automatic cache invalidation

### Database Optimization
- Efficient database queries with `select_related` and `prefetch_related`
- Database indexing on frequently queried fields
- Annotation-based calculations to reduce Python-level processing

### Pagination
- Built-in pagination for large datasets
- Configurable page size (default: 20 items per page)

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
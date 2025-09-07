# HomeSer Backend - Django REST Framework

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
- pip
- Virtual environment (recommended)

### Installation

1. **Clone the repository and navigate to backend directory:**
   ```bash
   cd homeser-backend-drf
   ```

2. **Run the setup script:**
   ```bash
   chmod +x run_local.sh
   ./run_local.sh
   ```

   This script will:
   - Create a virtual environment
   - Install dependencies
   - Run database migrations
   - Create sample data
   - Create admin user (admin@example.com / adminpass)
   - Start the development server

### Manual Setup

If you prefer manual setup:

1. **Create and activate virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Run migrations:**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

5. **Create superuser:**
   ```bash
   python manage.py createsuperuser
   ```

6. **Start development server:**
   ```bash
   python manage.py runserver
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
DATABASE_URL=postgresql://user:password@localhost:5432/homeser  # Optional
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
CLOUDINARY_CLOUD_NAME=your-cloud-name  # Optional
CLOUDINARY_API_KEY=your-api-key  # Optional
CLOUDINARY_API_SECRET=your-api-secret  # Optional
SSLCOMMERZ_STORE_ID=testbox
SSLCOMMERZ_STORE_PASS=qwerty
SSLCOMMERZ_IS_SANDBOX=True
FRONTEND_URL=http://localhost:3000
BACKEND_URL=http://localhost:8000
```

## Testing

Run the test suite:
```bash
python manage.py test
```

## SSLCOMMERZ Integration

The platform integrates with SSLCOMMERZ payment gateway:

- **Sandbox Mode**: Uses test credentials by default
- **Test Cards**: 
  - VISA: `4111111111111111` CVV `111` Exp `12/25`
  - MasterCard: `5111111111111111` CVV `111` Exp `12/25`
  - OTP: `111111` or `123456`

## Deployment

### Vercel Deployment

1. Install Vercel CLI:
   ```bash
   npm i -g vercel
   ```

2. Create `vercel.json`:
   ```json
   {
     "builds": [
       {
         "src": "homeser/wsgi.py",
         "use": "@vercel/python"
       }
     ],
     "routes": [
       {
         "src": "/(.*)",
         "dest": "homeser/wsgi.py"
       }
     ]
   }
   ```

3. Deploy:
   ```bash
   vercel --prod
   ```

## Project Structure

```
homeser-backend-drf/
├── homeser/                 # Main project settings
├── accounts/                # User authentication and profiles
├── services/                # Service catalog and reviews
├── orders/                  # Cart and order management
├── payments/                # Payment processing
├── api/                     # API views and serializers
├── scripts/                 # Utility scripts
├── requirements.txt         # Python dependencies
├── run_local.sh            # Quick setup script
└── README.md               # This file
```

## Admin Interface

Access the Django admin at `http://localhost:8000/admin/` with the created admin user.

## Support

For issues and questions, please check the documentation or create an issue in the repository.
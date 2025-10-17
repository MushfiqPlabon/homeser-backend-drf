# HomeSer Backend - Business & Marketing Focused Development

## Business Overview

HomeSer is a comprehensive household service platform backend designed to connect service providers and customers, enabling seamless booking, payment processing, and quality management. Developed with a business-first mindset, this platform incorporates advanced marketing and customer relationship strategies alongside robust technical architecture.

This project demonstrates my ability to bridge technical development with business strategy, applying marketing principles to technology solutions. As a BBA Marketing graduate, I've integrated customer experience, value proposition, and market positioning considerations into the technical implementation.

## Key Business Features

- **Market Segmentation**: Multi-tenant support for individual, business, and government customer types
- **Customer Relationship Management**: Comprehensive review and rating system with sentiment analysis
- **Service Provider Management**: Dedicated dashboard and API endpoints for service providers to manage their own services
- **Revenue Generation**: Secure payment processing with SSLCOMMERZ integration
- **Customer Experience**: Advanced search functionality with multi-language support
- **Data-Driven Insights**: Search analytics, email analytics, and sentiment analysis
- **User Engagement**: Automated email notifications with customizable templates
- **Scalable Growth**: Designed for horizontal scaling to accommodate market expansion

## Technical Excellence

For technical recruiters: This platform implements advanced software engineering practices including:

- **Architecture**: Service-oriented architecture with clean separation of concerns
- **Real-time Communication**: WebSocket implementation for live order updates, notifications, and payment status
- **Performance**: Redis caching with django-cachalot for ORM query optimization, connection pooling, and N+1 query prevention
- **Optimization**: Automatic ORM caching, bulk operations, and efficient database querying
- **Security**: JWT authentication, RBAC, comprehensive vulnerability protection, and security headers
- **Role-Based Access Control (RBAC)**: Implementation of customer, service provider, and admin roles with appropriate permissions and access levels
- **Code Quality**: Zero redundancy, zero dead code, and industry-standard linting with Ruff
- **Development Tools**: Modern Python tooling with uv, Ruff linting, and automated testing

## Marketing & Business Intelligence Integration

### Customer Analytics
- Sentiment analysis of customer reviews using TextBlob
- Search analytics for understanding customer preferences
- Performance metrics and business intelligence dashboards

### Customer Value Enhancement
- Lock-free cart implementation for seamless user experience
- Advanced search capabilities to improve customer satisfaction
- Multi-channel communication via email integration
- Asynchronous email processing with queue system and delivery tracking

### Revenue Optimization
- Secure payment processing with SSLCOMMERZ
- Order and payment status management
- Refund and dispute handling systems

## Quick Start

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd homeser-backend-drf
   ```

2. **Install dependencies:**
   ```bash
   uv venv
   uv sync
   ```

3. **Set up environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Run migrations:**
   ```bash
   uv run manage.py migrate
   ```

5. **Create superuser:**
   ```bash
   uv run manage.py createsuperuser
   ```

6. **Start development server:**
   ```bash
   uv run manage.py runserver
   ```

## For Technical Recruiters

This project showcases advanced technical skills including:
- Modern Python framework implementation
- Database optimization and caching strategies
- API development with best practices
- Security implementation
- Deployment and DevOps practices

## For Business-Focused Recruiters

This project demonstrates:
- Understanding of market segmentation and customer needs
- Ability to implement business requirements in technical solutions
- Data-driven approach to business problems
- Focus on customer experience and value creation
- Revenue-generating features and payment processing
- Market-ready product development

## Real-time Features

The platform includes comprehensive real-time communication capabilities:

- **WebSocket Integration**: Full-featured WebSocket implementation using Django Channels
- **Order Updates**: Real-time order status updates through WebSocket connections
- **Notifications**: Live notification system with WebSocket delivery
- **Payment Updates**: Real-time payment status notifications
- **Connection Management**: Robust connection handling with authentication and error recovery

### WebSocket Endpoints

- **Order Updates**: `/ws/orders/` - Provides real-time order status updates for authenticated users
- **Notifications**: `/ws/notifications/` - Delivers live notifications to users
- **Payment Updates**: `/ws/payments/` - Real-time payment status notifications

## API Documentation

The platform includes comprehensive API documentation:

- **Swagger UI**: Available at `/api/schema/swagger-ui/`
- **ReDoc**: Available at `/api/schema/redoc/`
- **OpenAPI Schema**: Available at `/api/schema/`

### Service Provider Endpoints

- **Service Provider Services**: `/api/provider/services/` - Allows service providers to manage only their own services (CRUD operations)
  - `GET /api/provider/services/` - Retrieve all services owned by the service provider
  - `POST /api/provider/services/` - Create a new service (owned by the authenticated service provider)
  - `PUT /api/provider/services/{id}/` - Update an existing service owned by the service provider
  - `DELETE /api/provider/services/{id}/` - Delete a service owned by the service provider

### Analytics Endpoints

- **Email Analytics**: `/api/analytics/email/` - Provides email campaign performance metrics
- **Sentiment Analytics**: `/api/analytics/sentiment/` - Delivers customer sentiment analysis from reviews
- **Payment Analytics**: `/api/payments/analytics/` - Offers payment processing insights
- **Search Analytics**: `/api/search/analytics/` - Reveals customer search behavior patterns

## Environment Configuration

Create a `.env` file with the following variables:

```env
# Django settings
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database configuration (SQLite by default)
# Uncomment for PostgreSQL:
# DATABASE_URL=postgresql://user:password@localhost:5432/homeser

# CORS settings
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# Services (required for production, including Vercel deployments)
CLOUDINARY_URL=cloudinary://api_key:api_secret@cloud_name  # Required for media storage
REDIS_URL=rediss://username:password@host:port/database    # Required for caching with serverless-optimized settings

# Payment gateway (sandbox by default)
SSLCOMMERZ_STORE_ID=testbox
SSLCOMMERZ_STORE_PASS=qwerty
SSLCOMMERZ_IS_SANDBOX=True

# Frontend integration
FRONTEND_URL=http://localhost:3000
BACKEND_URL=http://localhost:8000
```

## Testing

Run the test suite:
```bash
uv run manage.py test
```

## Deployment

For production deployment, ensure:

1. **Set DEBUG=False** in environment variables
2. **Use PostgreSQL** instead of SQLite
3. **Configure proper SSL certificates**
4. **Set up Redis** with serverless-optimized settings for caching, WebSocket channel layers, and session storage (required for production)
5. **Configure Cloudinary** for media storage
6. **Set up email backend** for notifications
7. **Enable security headers** for production environment

## Value Proposition

This project demonstrates my unique skill set combining:
- Technical proficiency in backend development
- Understanding of business requirements and market needs
- Marketing perspective on customer experience and value creation
- Data-driven approach to business intelligence
- Cross-functional collaboration between technical and business teams

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

*Built with ❤️ using Django REST Framework*
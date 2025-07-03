# Employee Daily Activity Tracker

A modern Django-based web application for tracking employee daily activities, built with Tailwind CSS and featuring SSO authentication through Arnatech's identity provider.

## Features

### 🎯 Core Functionality
- **Morning Check-in**: Employees log their daily plans, goals, and any morning problems
- **Afternoon Check-out**: Employees record completed activities, goal achievements, and encountered problems
- **Daily Activity Tracking**: Comprehensive tracking of work hours and attendance
- **Goal Management**: Set and track daily goals with completion percentages

### 👥 Employee Management
- **Company Management**: Multi-company support with configurable work hours
- **Employee Profiles**: Complete employee information with position, department, and manager hierarchy
- **Work Hour Configuration**: Company-level defaults with employee-specific overrides
- **Employment Status Tracking**: Active, inactive, on leave, and terminated status management

### 📊 Admin Dashboard
- **Real-time Analytics**: Live attendance tracking and performance metrics
- **Attendance Reports**: Who's on time, late, or absent
- **Company Performance**: Aggregated statistics by company, team, or individual
- **Historical Data**: Comprehensive reporting and data export capabilities

### 🔐 Authentication & Security
- **SSO Integration**: Direct API integration with Arnatech's SSO service
- **JWT Authentication**: Secure token-based authentication with refresh capabilities
- **MFA Support**: Two-factor authentication support for enhanced security
- **Session Management**: Secure session handling with automatic token refresh

### 🎨 Modern UI/UX
- **Dark Theme**: Modern NFT-inspired dark mode design
- **Responsive Design**: Mobile-first approach with Tailwind CSS
- **Interactive Elements**: Smooth animations and transitions
- **Accessibility**: WCAG-compliant design patterns

## Technology Stack

- **Backend**: Django 5.2.4
- **Frontend**: Tailwind CSS 3.x
- **Database**: SQLite (development) / PostgreSQL (production)
- **Authentication**: JWT with RSA256 signatures
- **SSO Integration**: Arnatech SSO API
- **Icons**: Font Awesome 6.0
- **Fonts**: Inter (Google Fonts)

## Project Structure

```
employee_daily_activity/
├── employee_activity_tracker/    # Main Django project
│   ├── settings.py              # Django settings
│   ├── urls.py                  # URL configuration
│   └── wsgi.py                  # WSGI configuration
├── employees/                   # Employee management app
│   ├── models.py               # Company and Employee models
│   ├── admin.py                # Django admin configuration
│   └── views.py                # Employee management views
├── activities/                  # Daily activity tracking app
│   ├── models.py               # DailyActivity and ActivityGoal models
│   ├── views.py                # Check-in/out and activity views
│   └── urls.py                 # Activity URL patterns
├── authentication/             # SSO authentication app
│   ├── middleware.py           # JWT authentication middleware
│   ├── views.py                # Login/logout views
│   └── urls.py                 # Authentication URL patterns
├── dashboard/                  # Admin dashboard app
│   ├── views.py                # Dashboard and analytics views
│   └── urls.py                 # Dashboard URL patterns
├── templates/                  # HTML templates
│   ├── base.html              # Base template with navigation
│   ├── authentication/        # Authentication templates
│   ├── activities/            # Activity tracking templates
│   └── dashboard/             # Dashboard templates
├── static/                     # Static files (CSS, JS, images)
├── public.pem                 # SSO public key for JWT verification
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

## Installation

1. **Clone the repository** (if applicable):
   ```bash
   git clone <repository-url>
   cd employee_daily_activity
   ```

2. **Create and activate virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**:
   ```bash
   cp env.example .env
   # Edit .env with your configuration
   ```

5. **Setup SSO public key**:
   - Obtain the public key from your SSO administrator
   - Save it as `public.pem` in the project root
   - Or update `SSO_PUBLIC_KEY_PATH` in your `.env` file

6. **Run migrations**:
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

7. **Create superuser**:
   ```bash
   python manage.py createsuperuser
   ```

8. **Run the development server**:
   ```bash
   python manage.py runserver
   ```

## Configuration

### Environment Variables

Create a `.env` file in the project root with the following variables:

```env
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# SSO Configuration
SSO_BASE_URL=https://sso.arnatech.id
SSO_PUBLIC_KEY_PATH=public.pem

# JWT Configuration
JWT_ALGORITHM=RS256
JWT_AUDIENCE=employee-daily-activity
JWT_ISSUER=sso.arnatech.id
```

### SSO Setup

1. **Obtain SSO Public Key**: Get the RSA public key from your SSO administrator
2. **Configure JWT Settings**: Update JWT audience and issuer to match your SSO configuration
3. **Set SSO Base URL**: Configure the SSO service base URL

### SSO API Integration

The application integrates with the following SSO API endpoints:

- **Login**: `POST /api/auth/login/` - Email/password authentication
- **MFA Verification**: `POST /api/auth/mfa/verify/` - Two-factor authentication
- **Token Refresh**: `POST /api/auth/token/refresh/` - Refresh JWT access tokens
- **Logout**: `POST /api/auth/logout/` - Revoke refresh tokens

## Usage

### For Employees

1. **Login**: 
   - Navigate to the login page
   - Enter your Arnatech email and password
   - Complete MFA verification if required
   
2. **Morning Check-in**: 
   - Set daily goals and planned activities
   - Report any morning problems or blockers
   
3. **Afternoon Check-out**:
   - Record completed activities
   - Update goal completion percentage
   - Report any problems encountered

### For Administrators

1. **Access Admin Dashboard**: Navigate to `/dashboard/admin/`
2. **View Analytics**: Monitor real-time attendance and performance
3. **Manage Employees**: Add/edit employee profiles and company assignments
4. **Generate Reports**: Export attendance and performance data

## API Endpoints

### Authentication
- `GET /auth/login/` - Login page
- `POST /auth/api/login/` - API login with email/password
- `POST /auth/api/mfa/verify/` - MFA token verification
- `POST /auth/api/token/refresh/` - Refresh JWT tokens
- `POST /auth/logout/` - Logout and revoke tokens

### Activities
- `GET /activities/` - Daily activity summary
- `GET /activities/check-in/` - Morning check-in form
- `POST /activities/check-in/` - Submit morning check-in
- `GET /activities/check-out/` - Afternoon check-out form
- `POST /activities/check-out/` - Submit afternoon check-out

### Dashboard
- `GET /dashboard/` - Employee dashboard
- `GET /dashboard/admin/` - Admin dashboard with analytics

## Models

### Company
- Company information and work hour configuration
- Timezone settings for different client locations

### Employee
- Employee profiles linked to Django User model
- Company assignments and work hour overrides
- SSO integration fields

### DailyActivity
- Daily check-in/check-out records
- Goal tracking and completion metrics
- Problem reporting and notes

### ActivityGoal
- Individual goals within daily activities
- Priority levels and completion status

## Security Features

- **JWT Token Authentication**: Secure token-based authentication
- **Automatic Token Refresh**: Seamless token renewal
- **Session Management**: Secure session handling
- **MFA Support**: Two-factor authentication for enhanced security
- **CSRF Protection**: Cross-site request forgery protection
- **Input Validation**: Comprehensive input sanitization

## Development

### Running Tests
```bash
python manage.py test
```

### Code Style
```bash
# Format code with Black
black .

# Check linting with flake8
flake8 .
```

### Database Migrations
```bash
# Create migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate
```

## Deployment

### Production Checklist
- [ ] Set `DEBUG=False` in environment
- [ ] Configure production database (PostgreSQL)
- [ ] Set up proper SSL certificates
- [ ] Configure static file serving
- [ ] Set up monitoring and logging
- [ ] Configure backup strategies

### Environment Variables for Production
```env
DEBUG=False
SECRET_KEY=your-production-secret-key
ALLOWED_HOSTS=your-domain.com,www.your-domain.com
DATABASE_URL=postgresql://user:password@localhost/dbname
SSO_BASE_URL=https://sso.arnatech.id
SSO_PUBLIC_KEY_PATH=/path/to/production/public.pem
```

## Contributing

1. Follow Django coding standards
2. Use Black for code formatting
3. Write comprehensive tests
4. Update documentation for new features
5. Use semantic commit messages

## License

Copyright © 2025 Arnatech. All rights reserved.

## Support

For technical support, contact: support@arnatech.id

## Roadmap

- [ ] Mobile app development
- [ ] Advanced analytics and reporting
- [ ] Integration with project management tools
- [ ] Automated absence notifications
- [ ] Performance review integration
- [ ] Multi-language support 
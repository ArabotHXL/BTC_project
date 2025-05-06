# Architecture Documentation

## 1. Overview

The BTC Mining Calculator is a web application that provides Bitcoin mining profitability analysis tools. It allows users to calculate potential mining profits based on various factors including electricity costs, mining hardware specifications, and real-time Bitcoin network parameters.

The application serves two distinct user roles: mining site owners who host mining equipment and their clients who own the mining equipment. The system provides specialized calculations for each role with appropriate access controls.

## 2. System Architecture

The application follows a traditional web application architecture with the following components:

- **Frontend**: HTML templates with Bootstrap CSS framework and vanilla JavaScript
- **Backend**: Python Flask web framework
- **Database**: PostgreSQL database for user data and login records
- **Authentication**: Custom email-based authentication system

### Architectural Diagram

```
+------------------+        +------------------+        +------------------+
|                  |        |                  |        |                  |
|    Client        |  HTTP  |    Flask App     |  SQL   |   PostgreSQL     |
|    Browser       | <----> |    (Python)      | <----> |   Database       |
|                  |        |                  |        |                  |
+------------------+        +------------------+        +------------------+
                                     |
                                     | HTTP
                                     |
                                     v
                            +------------------+
                            |                  |
                            |  External APIs   |
                            |  (BTC Network)   |
                            |                  |
                            +------------------+
```

## 3. Key Components

### 3.1 Backend Components

#### 3.1.1 Flask Application (`app.py`, `main.py`)

The main application entry point and request handler. It initializes the Flask application, configures routes, and handles HTTP requests.

- `app.py`: Contains route definitions and request handling logic
- `main.py`: Application entry point that initializes database and starts the server

#### 3.1.2 Mining Calculator Engine (`mining_calculator.py`)

Core calculation logic for Bitcoin mining profitability. This module:
- Defines mining hardware specifications (hashrate, power consumption)
- Implements algorithms for mining profitability calculation
- Provides functions for real-time data retrieval (BTC price, network difficulty, etc.)
- Generates data for profit visualization charts

#### 3.1.3 Authentication System (`auth.py`)

Custom role-based authentication system that:
- Verifies user access based on authorized email addresses
- Implements login/logout functionality
- Handles role-based access control
- Tracks login attempts and geographic locations

#### 3.1.4 Database Interface (`db.py`, `models.py`)

- `db.py`: Database connection management and initialization
- `models.py`: SQLAlchemy ORM models defining database structure

### 3.2 Frontend Components

#### 3.2.1 Templates

HTML templates using Jinja2 templating engine:
- `templates/index.html`: Main calculator interface
- `templates/login.html`: Authentication page
- `templates/user_access.html`: User management interface
- `templates/login_records.html`: Login history tracking
- `templates/unauthorized.html`: Access denied page

#### 3.2.2 Static Assets

- `static/js/main.js`: Main application JavaScript
- `static/js/chart.js`: Chart generation functionality
- `static/css/styles.css`: Custom styling

#### 3.2.3 Localization

- `translations.py`: Bilingual support (Chinese/English) for UI elements

### 3.3 Data Models

#### 3.3.1 UserAccess Model

Manages user access permissions with the following attributes:
- Email, name, company information
- Access expiration dates
- Role assignments (owner, admin, manager, guest)

#### 3.3.2 LoginRecord Model

Tracks authentication activities:
- Login timestamp
- Success/failure status
- IP address information
- Geographic location data

## 4. Data Flow

### 4.1 Authentication Flow

1. User enters email address on login page
2. System checks email against authorized users list in database
3. If authorized, user is assigned a role based on database records
4. Login attempt is recorded with IP and location information
5. User session is created with appropriate access level

### 4.2 Calculator Flow

1. Real-time Bitcoin network data is fetched from external APIs
2. User inputs mining parameters (hardware model, electricity cost, etc.)
3. System calculates mining profitability using two different algorithms:
   - Network hashrate-based algorithm
   - Difficulty-based algorithm
4. Results are displayed with different views based on user role
5. Profit heatmaps are generated for sensitivity analysis

## 5. External Dependencies

### 5.1 External APIs

- Bitcoin price data API
- Bitcoin network statistics APIs (difficulty, hashrate, block reward)
- IP geolocation service for tracking login locations

### 5.2 Frontend Libraries

- Bootstrap CSS framework for UI components
- Chart.js for data visualization
- Bootstrap Icons for UI elements

### 5.3 Backend Dependencies

- Flask web framework
- SQLAlchemy ORM for database operations
- Requests library for API calls
- NumPy and Pandas for mathematical calculations

## 6. Deployment Strategy

The application supports two deployment methods:

### 6.1 Replit Deployment

- Uses Gunicorn WSGI server
- Configured via `.replit` file with autoscaling
- Runs on port 5000 internally, mapped to port 80 externally

### 6.2 Local Deployment

- Requires Python 3.9+ and PostgreSQL
- Environment variables for database connection and secrets
- Detailed setup instructions in `local_run_guide.md`

## 7. Security Considerations

### 7.1 Authentication

- Email-based authentication with no password (simplified approach)
- SHA-256 hashing for email addresses for increased security
- Role-based access control system
- Session management with Flask sessions

### 7.2 Database Security

- Uses environment variables for database credentials
- Connection pooling with timeout and reconnect capabilities
- Connection pool pre-ping to verify connections

### 7.3 Input Validation

- Server-side validation for calculator inputs
- Client-side validation for form data
- Reasonable defaults for missing parameters

## 8. Localization Strategy

The application supports both Chinese and English languages:
- Default language is Chinese (`zh`)
- Language can be changed via URL parameter or session settings
- Translations are managed through a dictionary in `translations.py`
- UI elements dynamically update based on language selection

## 9. Future Architectural Considerations

Potential areas for architectural improvement:

1. **Formal API Structure**: Refactor backend to provide a clear API structure
2. **Enhanced Authentication**: Implement more robust authentication methods
3. **Frontend Framework**: Consider migrating from vanilla JS to a modern framework
4. **Caching Layer**: Implement caching for API calls and calculations
5. **Containerization**: Add Docker support for easier deployment
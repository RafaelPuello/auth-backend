# CLAUDE.md - ID Backend

This file provides backend-specific guidance. For frontend details and full service overview, see `/id/CLAUDE.md`.

## Project Overview

Django 6.0 identity/authentication service using django-allauth for headless API-driven authentication. Provides user account management with multi-factor authentication (MFA), social OAuth providers, and WebAuthn/passkey support. Uses JWT-based authentication with RSA-256 asymmetric keys.

## Commands

### Setup & Development
```bash
cd backend
pip install -r requirements.txt -r requirements-dev.txt
python manage.py migrate          # Create database tables
python manage.py runserver 0.0.0.0:8000
```

### Testing
```bash
pytest                            # Run all tests
pytest identity/                  # Run identity app tests only
pytest -v                         # Verbose output
pytest -v --cov                   # With coverage report
pytest identity/tests.py::TestClass::test_method  # Single test
```

### Utilities
```bash
python manage.py createsuperuser  # Create admin user (note: admin disabled in HEADLESS_ONLY mode)
python manage.py shell            # Django shell for manual testing
```

## Architecture

### Authentication Model

**JWT-Based Authentication (Not Session-Based)**
- Tokens: Access tokens (5 min), Refresh tokens (24 hrs)
- Algorithm: RS256 (asymmetric) - frontend can validate tokens with public key only
- Tokens sent via `Authorization: Bearer <token>` header
- No CSRF protection needed (JWT inherently CSRF-safe)
- Sessions stored in signed cookies (not database), via `SESSION_ENGINE = 'django.contrib.sessions.backends.signed_cookies'`

**Key Configuration** (`config/settings.py`)
- `HEADLESS_ONLY = True` - No server-rendered auth pages, API-only
- Custom User model (`identity.User`) - email as identifier, not username
- MFA types: TOTP, recovery codes, WebAuthn
- Passkey login enabled, passkey signup disabled
- Signups disabled via `IdentityAdapter.is_open_for_signup()` (returns False)

### API Structure

**Ninja Router** (`config/api.py`)
- `/api/me` - Get current authenticated user (requires JWT)
- `/api/health` - Health check endpoint (no auth required)
- Built with `django-ninja` and `django-ninja-jwt`

**Django Allauth Headless URLs**
- `/accounts/` - Standard allauth URLs
- `/_allauth/app/v1/*` - Headless API endpoints for auth flows (app client only)
  - `/auth/login`, `/auth/signup`, `/auth/token`, `/auth/session`
  - `/auth/2fa/authenticate`, `/auth/webauthn/authenticate`
  - `/account/authenticators/totp`, `/account/authenticators/webauthn`
  - `/account/password/change`, `/account/email`
  - `/config` - Runtime configuration for frontend
- Note: Browser client endpoints (`/_allauth/browser/v1/*`) are disabled via `HEADLESS_CLIENTS = ["app"]`

### Database Models

**Custom User Model** (`identity/models.py`)
```python
class User(AbstractUser):
    # Replaces username with email as unique identifier
    email: EmailField (unique)
    uuid: UUIDField (for JWT claims, indexed)
```

**Account Adapter** (`identity/adapter.py`)
```python
class IdentityAdapter(DefaultAccountAdapter):
    # Controls signup behavior - currently disabled
    def is_open_for_signup(request) -> False
```

### JWT Key Management

**Key Locations**
- Private key: `config/keys/jwt_private_key.pem` (dev) or `JWT_PRIVATE_KEY_PATH` env var (prod)
- Public key: `config/keys/jwt_public_key.pem` (dev) or `JWT_PUBLIC_KEY_PATH` env var (prod)

**In Development**
- Keys are checked into git in `config/keys/` for local testing
- Used for signing tokens and validating test requests

**In Production**
- Keys must be provided via environment variables
- Private key must be secret and never exposed
- Public key can be shared with other services for token validation

**Token Expiration**
- Access token: 300 seconds (5 minutes)
- Refresh token: 86400 seconds (24 hours)
- Rotate refresh token: Enabled (new refresh token issued on each use)

## Testing

### Test Structure
- Test files: `identity/tests.py`, `identity/test_jwt_integration.py`
- Configuration: `pytest.ini` specifies `DJANGO_SETTINGS_MODULE = config.settings`
- Markers: `slow`, `integration` (use `-m` flag to run specific subsets)
- Database: SQLite in-memory for tests (configured in `config/settings_test.py`)

### Key Test Patterns
- Factory-boy for fixture creation (see `requirements-dev.txt`)
- Custom User model tested with email as identifier
- JWT token generation and validation tested
- Auth flow and MFA tested via headless API

## Environment Variables

### Required (must be set)
- `DJANGO_SECRET_KEY` - Secret key for Django
- `DATABASE_URL` - Database connection string (defaults to sqlite for dev)

### Optional (with defaults)
- `DJANGO_DEBUG` - Set to "True" for development (default: "False")
- `DJANGO_ALLOWED_HOSTS` - Comma-separated list (default: "localhost,testserver")
- `JWT_PRIVATE_KEY_PATH` - Path to JWT private key (default: `config/keys/jwt_private_key.pem`)
- `JWT_PUBLIC_KEY_PATH` - Path to JWT public key (default: `config/keys/jwt_public_key.pem`)

### Development
- `.env.dev` file in `backend/` directory sets development variables
- `.env.prod` file for production settings

## Key Files

| File | Purpose |
|------|---------|
| `config/settings.py` | Main Django settings (JWT, allauth, database config) |
| `config/urls.py` | URL routing (API, allauth, headless endpoints) |
| `config/api.py` | Ninja API router with `/me` and `/health` endpoints |
| `identity/models.py` | Custom User model (email-based, UUID field) |
| `identity/adapter.py` | Allauth account adapter (signup control) |
| `identity/tests.py` | Unit tests for authentication |
| `identity/test_jwt_integration.py` | Integration tests for JWT auth flow |
| `conftest.py` | Pytest configuration and fixtures |

## Important Gotchas

### No Sessions in Database
The service uses `SESSION_ENGINE = 'django.contrib.sessions.backends.signed_cookies'` instead of database-backed sessions. This avoids 409 Conflict errors from django-allauth when dealing with JWT tokens. Sessions are stored entirely in signed cookies.

### Admin Interface Disabled
`HEADLESS_ONLY = True` means the Django admin interface is disabled and not accessible. All admin tasks must be done via Django shell or scripts.

### CSRF Middleware Removed
CSRF middleware is removed from the middleware stack because JWT authentication in Authorization headers is inherently CSRF-safe (not vulnerable to cross-site request forgery). Tokens cannot be stolen via cookies.

### Custom User Model
Always use `get_user_model()` or `from django.contrib.auth import get_user_model` when referencing the User model. Do not import directly.

### JWT Keys Required at Startup
The service will fail to start if JWT key files are missing. In development, they must exist at `config/keys/jwt_private_key.pem` and `config/keys/jwt_public_key.pem`. In production, set the env vars.

## Deployment Notes

- Database: Uses PostgreSQL in production (via `dj-database-url`)
- Static files: WhitNoise middleware handles static file serving
- CORS: Configured for specific origins (digidex.bio, localhost for dev)
- Environment: Production requires `DJANGO_DEBUG=False` and all env vars set
- Secrets: JWT private key must never be exposed; use secrets management system

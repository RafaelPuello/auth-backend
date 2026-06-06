# CLAUDE.md - ID Backend

Django 6.0 identity/authentication service using django-allauth (headless API) for account management, MFA, OAuth, and WebAuthn support. Uses JWT-based authentication (RS256 asymmetric).

**For setup, testing, and commands, see README.md.**

## Architecture

### Authentication Model

**JWT (RS256 Asymmetric)**

See `.claude/rules/jwt-authentication-contract.md` for the complete token flow, structure, key management, frontend/backend patterns, and common mistakes.

Key points:
- Access tokens: 5 min, Refresh tokens: 14 days (configurable via `JWT_REFRESH_TOKEN_EXPIRES_IN`)
- Tokens sent via `Authorization: Bearer <token>` header
- Custom User model (`identity.User`): email-based identifier, no username
- MFA types: TOTP, recovery codes, WebAuthn/passkeys
- Signups disabled (via `IdentityAdapter.is_open_for_signup()`)

**Token Refresh**
- Database-backed sessions (`SESSION_ENGINE = 'django.contrib.sessions.backends.db'`) required: allauth's `validate_refresh_token()` validates refresh token JTI via `session_store().exists(session_key)` (interim pattern; long-term goal is pure stateless JWT)
- `LoginFlushMiddleware` flushes session on POST `/_allauth/app/v1/auth/login` to prevent 409 Conflict when a user logs in with existing session

### API Endpoints

**Ninja Router** (`config/api.py`)
- `GET /id/api/me` — Current authenticated user (requires JWT)
- `GET /id/api/health` — Health check (no auth)

**Django Allauth Headless** (`/_allauth/app/v1/*`, app client only; browser client disabled)
- `/auth/login`, `/auth/signup`, `/auth/token`, `/auth/session`
- `/auth/2fa/authenticate`, `/auth/webauthn/authenticate`
- `/account/authenticators/totp`, `/account/authenticators/webauthn`
- `/account/password/change`, `/account/email`
- `/config` — Runtime configuration for frontend

### Key Configuration

`config/settings.py`:
- `HEADLESS_ONLY = True` — API-only, no Django admin
- Custom User model (`identity.User`) — email as unique identifier
- `HEADLESS_CLIENTS = ["app"]` — Only app client; browser client disabled
- JWT expiration and refresh token rotation enabled

### JWT Key Management

**Development:** Keys in `config/keys/jwt_private_key.pem` and `config/keys/jwt_public_key.pem` (checked into git)

**Production:** Keys via env vars `JWT_PRIVATE_KEY_PATH` and `JWT_PUBLIC_KEY_PATH` (never expose private key)

## Conventions

- **Email-first User model:** Always use `get_user_model()` to reference User; never import directly
- **Headless API:** Frontend calls `/_allauth/app/v1/*` endpoints; no server-rendered pages
- **JWT token structure:** `sub` claim holds user UUID (not email); frontend validates tokens with public key
- **Refresh token handling:** Automatic rotation enabled (new token issued on each refresh); effectively infinite session while in use

## Gotchas

### Sessions Required for Token Refresh

Database-backed sessions are interim requirement: allauth's `validate_refresh_token()` uses `session_store().exists(session_key)`. Signed-cookies backend always returns False (no server-side store), breaking token refresh. **Long-term goal:** eliminate sessions; use custom `JWTTokenStrategy` subclass for session-free validation or disable refresh rotation.

### 409 Conflict on Login

Without `LoginFlushMiddleware`, allauth's login endpoint returns 409 Conflict if `request.user.is_authenticated` is True. Middleware flushes session on every POST to `/_allauth/app/v1/auth/login` *before* AuthenticationMiddleware runs. Middleware must appear *before* AuthenticationMiddleware in the stack.

### Admin Interface Disabled

`HEADLESS_ONLY = True` disables Django admin. All admin tasks via Django shell or scripts.

### JWT Keys Required at Startup

Service fails to start if JWT keys missing (dev: `config/keys/`, prod: env vars). Verify keys exist before running migrations.

### DJANGO_SETTINGS_MODULE Required for Tests

`pytest.ini` sets `DJANGO_SETTINGS_MODULE = config.settings`. Without it, tests fail. In-memory SQLite used for tests (configured in `config/settings_test.py`).

## Key Files

| File | Purpose |
|------|---------|
| `config/settings.py` | JWT, allauth, headless config; custom User model |
| `config/urls.py` | URL routing (allauth, Ninja API) |
| `config/api.py` | Ninja router: `/me`, `/health` |
| `config/middleware.py` | LoginFlushMiddleware (prevents 409 Conflict) |
| `identity/models.py` | Custom User model (email-based, UUID for JWT) |
| `identity/adapter.py` | Account adapter (signup control) |
| `identity/tests.py` | Unit tests for auth flows |

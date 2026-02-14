# JWT Implementation for ID Service (Backend)

## Overview

This document describes the JWT (JSON Web Token) implementation for the DigiDex ID Service backend. The implementation uses **RS256 (RSA)** asymmetric encryption, allowing other services (CMS, App) to validate tokens independently using the public key.

## Configuration

### Key Files Changed

1. **config/settings.py**
   - Enabled `HEADLESS_TOKEN_STRATEGY = "allauth.headless.contrib.ninja.token_strategy.JWTTokenStrategy"`
   - Configured JWT parameters (algorithm, expiration, key rotation)
   - Added JWT public/private key paths
   - Updated CORS and cookie settings for development

2. **config/api.py**
   - Updated `/api/me` endpoint to return JWT-compatible data (uuid, is_authenticated)
   - Added health check endpoint (no auth required)
   - Maintained dual auth support (JWT + session tokens) for backward compatibility

3. **identity/tests.py**
   - Added comprehensive JWT configuration tests
   - User model tests for UUID and group management
   - Configuration verification tests

4. **config/keys/** (generated)
   - `jwt_private_key.pem` - Private key for signing tokens
   - `jwt_public_key.pem` - Public key for validating tokens

## JWT Configuration Details

### Token Strategy
```python
HEADLESS_TOKEN_STRATEGY = "allauth.headless.contrib.ninja.token_strategy.JWTTokenStrategy"
```
Uses django-allauth's built-in JWT strategy with Ninja API integration.

### Algorithm
```python
HEADLESS_JWT_ALGORITHM = "RS256"  # RSA SHA-256 (asymmetric)
```

**Why RS256?**
- Asymmetric: Private key signs, public key verifies
- Other services can validate without access to private key
- Standard, widely supported algorithm
- Suitable for microservices architecture

### Key Management
```python
# Load from environment variables or file paths
HEADLESS_JWT_PRIVATE_KEY = Path(_jwt_private_key_path).read_text().strip()
HEADLESS_JWT_PUBLIC_KEY = Path(_jwt_public_key_path).read_text().strip()
```

**Development**: Uses local PEM files in `config/keys/`
**Production**: Load from environment variables or secrets manager

### Token Expiration
```python
HEADLESS_JWT_ACCESS_TOKEN_EXPIRES_IN = 300  # 5 minutes
HEADLESS_JWT_REFRESH_TOKEN_EXPIRES_IN = 86400  # 24 hours
HEADLESS_JWT_ROTATE_REFRESH_TOKEN = True
```

**Flow**:
1. User logs in → receives access token (5 min) + refresh token (24 hrs)
2. Access token used for API requests
3. When access token expires → use refresh token to get new one
4. Refresh token automatically rotated (old one invalidated)
5. Logout invalidates refresh token

## API Endpoints

### `GET /api/me` (Authenticated)

Returns current user information for token validation.

**Authentication**: Supports both JWT and session tokens (for compatibility)

**Response**:
```json
{
  "id": 1,
  "email": "user@example.com",
  "uuid": "550e8400-e29b-41d4-a716-446655440000",
  "is_authenticated": true,
  "first_name": "John",
  "last_name": "Doe"
}
```

**Key fields for JWT**:
- `uuid`: Unique identifier for JWT claims
- `is_authenticated`: Verification of authentication status

### `GET /api/health` (Public)

Health check endpoint for load balancers and monitoring.

**Authentication**: None required

**Response**:
```json
{
  "status": "healthy"
}
```

## CORS Configuration

Added local development origins:
```python
CORS_ALLOWED_ORIGINS = [
    "https://digidex.bio",
    "https://www.digidex.bio",
    "https://id.digidex.bio",
    "http://localhost:3000",  # App frontend
    "http://localhost:5173",  # ID frontend (Vite)
]
CORS_ALLOW_CREDENTIALS = True
```

## Session/Cookie Security

Even during JWT transition, session cookies are hardened:
```python
SESSION_COOKIE_SECURE = True  # HTTPS only
SESSION_COOKIE_HTTPONLY = True  # No JavaScript access
SESSION_COOKIE_DOMAIN = ".digidex.bio"
```

## User Model Integration

The custom User model supports JWT:
- **UUID field**: Used in JWT claims for unique identification
- **Email-based**: No username field (cleaner JWT payload)
- **Group management**: Each user gets auto-created group (UUID-based)

## Testing

Run tests to verify JWT configuration:

```bash
cd id/backend

# Run all tests
pytest identity/tests.py

# Run specific test
pytest identity/tests.py::JWTAuthenticationTests::test_jwt_public_key_available

# With verbose output
pytest identity/tests.py -v

# With coverage
pytest identity/tests.py --cov=identity
```

### Test Coverage

- JWT configuration (keys, algorithm, strategy)
- Token expiration settings
- CORS configuration
- User model and UUID generation
- MFA configuration
- Security settings

## Backward Compatibility

Current implementation maintains **dual authentication**:

```python
@api_router.get("/me", auth=[jwt_token_auth, x_session_token_auth])
```

This allows:
1. Old clients using session tokens to continue working
2. New clients to use JWT tokens
3. Smooth migration period

To switch to JWT-only (after frontend migration):
```python
@api_router.get("/me", auth=[jwt_token_auth])
```

## Security Considerations

### ✅ Implemented

- **RS256 algorithm**: Asymmetric, suitable for microservices
- **Short access token expiration**: 5 minutes reduces exposure window
- **Refresh token rotation**: Automatically rotates on use
- **HTTPOnly cookies**: Session cookies not accessible via JavaScript
- **HTTPS-only cookies**: Secure transmission
- **Public key sharing**: Other services can validate independently

### ⚠️ Next Phase (Frontend)

- **Token storage strategy**: Use httpOnly cookies (not localStorage)
- **Automatic token refresh**: Before expiration or on 401
- **Logout**: Invalidate refresh token server-side

### ⚠️ Later Phase

- **Token revocation**: Implement blacklist if needed (extra security)
- **Rate limiting**: Protect token endpoint from brute force
- **Audit logging**: Track token issuance and usage

## Generating New Keys (if needed)

```bash
cd config/keys

# Generate new private key
openssl genrsa -out jwt_private_key.pem 4096

# Extract public key
openssl rsa -in jwt_private_key.pem -pubout -out jwt_public_key.pem
```

Then update environment variables to point to new keys:
```bash
export JWT_PRIVATE_KEY_PATH=/path/to/new/jwt_private_key.pem
export JWT_PUBLIC_KEY_PATH=/path/to/new/jwt_public_key.pem
```

## Integration with Other Services

### CMS Backend

CMS can validate tokens independently:

```python
# cms/backend/settings.py
import jwt
from pathlib import Path

JWT_PUBLIC_KEY = Path(os.environ["JWT_PUBLIC_KEY_PATH"]).read_text()

def validate_token(token):
    payload = jwt.decode(token, JWT_PUBLIC_KEY, algorithms=["RS256"])
    return payload

# Use in authentication middleware
```

### App Backend

Same pattern as CMS.

## Troubleshooting

### Missing Keys

Error: `FileNotFoundError: [Errno 2] No such file or directory: 'config/keys/jwt_private_key.pem'`

**Solution**: Generate keys using openssl command above

### Invalid Key Format

Error: `ValueError: Could not deserialize key data`

**Solution**: Ensure keys are in PEM format (starts with `-----BEGIN`)

### Token Verification Failures

Check:
1. Public key matches private key
2. Algorithm is RS256 in both encoder and decoder
3. Token hasn't expired
4. Token wasn't tampered with

## Production Deployment

1. **Generate production keys** (different from dev keys)
2. **Store keys securely**:
   - Docker secrets: `/run/secrets/jwt_private_key`
   - Environment variables (base64 encoded)
   - Kubernetes secrets
3. **Update environment variables**:
   ```bash
   JWT_PRIVATE_KEY_PATH=/run/secrets/jwt_private_key
   JWT_PUBLIC_KEY_PATH=/run/secrets/jwt_public_key
   ```
4. **Share public key** with CMS and App services
5. **Test token validation** across all services

## Next Steps

1. ✅ Backend JWT configuration (this document)
2. ⏳ Frontend JWT implementation (separate document)
3. ⏳ CMS/App service integration
4. ⏳ Production deployment
5. ⏳ Session middleware removal (optional, after full migration)

## References

- [django-allauth JWT Docs](https://django-allauth.readthedocs.io/)
- [django-ninja Docs](https://django-ninja.rest-framework.com/)
- [RFC 7519 - JWT Specification](https://tools.ietf.org/html/rfc7519)
- [RS256 Asymmetric Algorithm](https://auth0.com/blog/critical-vulnerabilities-in-json-web-token-libraries/)

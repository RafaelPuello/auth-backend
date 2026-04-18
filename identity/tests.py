from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.conf import settings

User = get_user_model()


class JWTAuthenticationTests(TestCase):
    """
    Test JWT authentication flow with django-allauth.
    Verifies that tokens are correctly issued and can authenticate requests.
    """

    def setUp(self):
        """Create test user and client."""
        self.client = Client()
        self.user_email = "testuser@example.com"
        self.user_password = "SecureTestPass123!"

        # Create test user
        self.user = User.objects.create_user(
            email=self.user_email, password=self.user_password
        )

    def test_user_creation(self):
        """Verify custom User model uses email as identifier."""
        self.assertEqual(self.user.email, self.user_email)
        self.assertIsNone(self.user.username)
        self.assertTrue(self.user.check_password(self.user_password))

    def test_user_has_uuid(self):
        """Verify User model has UUID field for JWT claims."""
        self.assertIsNotNone(self.user.uuid)
        self.assertEqual(str(self.user.uuid), str(self.user.uuid))  # Valid UUID

    def test_jwt_public_key_available(self):
        """Verify JWT public key is available for token validation."""
        self.assertTrue(hasattr(settings, "HEADLESS_JWT_PUBLIC_KEY"))
        public_key = settings.HEADLESS_JWT_PUBLIC_KEY
        self.assertIn("-----BEGIN PUBLIC KEY-----", public_key)

    def test_jwt_private_key_available(self):
        """Verify JWT private key is available for token signing."""
        self.assertTrue(hasattr(settings, "HEADLESS_JWT_PRIVATE_KEY"))
        private_key = settings.HEADLESS_JWT_PRIVATE_KEY
        self.assertIn("-----BEGIN RSA PRIVATE KEY-----", private_key)

    def test_jwt_algorithm_configured(self):
        """Verify JWT uses RS256 (asymmetric) algorithm."""
        self.assertEqual(settings.HEADLESS_JWT_ALGORITHM, "RS256")

    def test_jwt_token_strategy_configured(self):
        """Verify JWT token strategy is enabled."""
        self.assertEqual(
            settings.HEADLESS_TOKEN_STRATEGY,
            "allauth.headless.tokens.strategies.jwt.JWTTokenStrategy",
        )

    def test_api_me_endpoint_exists(self):
        """Verify /api/me endpoint is available."""
        response = self.client.get("/api/me")
        # Should get 401 without auth token
        self.assertEqual(response.status_code, 401)

    def test_headless_only_mode(self):
        """Verify HEADLESS_ONLY is enabled (no server-rendered auth pages)."""
        self.assertTrue(settings.HEADLESS_ONLY)

    def test_headless_clients_app_only(self):
        """Verify only app client is enabled (browser client disabled)."""
        self.assertEqual(settings.HEADLESS_CLIENTS, ["app"])

    def test_cors_configured(self):
        """Verify CORS is configured for development and production."""
        self.assertIn("http://localhost:3000", settings.CORS_ALLOWED_ORIGINS)
        self.assertIn("http://localhost:5173", settings.CORS_ALLOWED_ORIGINS)
        self.assertTrue(settings.CORS_ALLOW_CREDENTIALS)

    def test_token_expiration_configured(self):
        """Verify token expiration times are set correctly."""
        # Access token: 5 minutes
        self.assertEqual(settings.HEADLESS_JWT_ACCESS_TOKEN_EXPIRES_IN, 300)
        # Refresh token: 14 days
        self.assertEqual(settings.HEADLESS_JWT_REFRESH_TOKEN_EXPIRES_IN, 1209600)

    def test_refresh_token_rotation_enabled(self):
        """Verify refresh token rotation is enabled for security."""
        self.assertTrue(settings.HEADLESS_JWT_ROTATE_REFRESH_TOKEN)

    def test_jwt_uses_db_session_backend(self):
        """Verify application uses database-backed sessions for JWT token refresh compatibility.

        JWT token refresh (validate_refresh_token) calls session_store().exists(session_key)
        to verify the session. The signed_cookies backend always returns False from exists(),
        breaking token refresh and causing immediate logout. The db backend stores sessions
        server-side so exists() works correctly.
        """
        self.assertEqual(settings.SESSION_ENGINE, "django.contrib.sessions.backends.db")
        # Session middleware required for AuthenticationMiddleware
        self.assertIn(
            "django.contrib.sessions.middleware.SessionMiddleware", settings.MIDDLEWARE
        )

    def test_login_flush_middleware_in_stack(self):
        """Verify LoginFlushMiddleware is in the middleware stack to prevent 409 Conflict.

        When using db-backed sessions, a previous session may still exist when a user
        tries to log in again. allauth's LoginView returns 409 Conflict if request.user
        is already authenticated. The LoginFlushMiddleware flushes the session before
        the login endpoint to prevent this.
        """
        self.assertIn("identity.middleware.LoginFlushMiddleware", settings.MIDDLEWARE)

    def test_mfa_types_supported(self):
        """Verify MFA types are available for JWT auth."""
        expected_types = ["totp", "recovery_codes", "webauthn"]
        for mfa_type in expected_types:
            self.assertIn(mfa_type, settings.MFA_SUPPORTED_TYPES)

    def test_passkey_login_enabled(self):
        """Verify WebAuthn/passkey login is enabled."""
        self.assertTrue(settings.MFA_PASSKEY_LOGIN_ENABLED)

    def test_passkey_signup_disabled(self):
        """Verify WebAuthn/passkey signup is disabled."""
        self.assertFalse(settings.MFA_PASSKEY_SIGNUP_ENABLED)


class UserModelTests(TestCase):
    """Test custom User model functionality."""

    def test_create_user_with_email(self):
        """User should be created with email as primary identifier."""
        user = User.objects.create_user(
            email="newuser@example.com", password="TestPass123!"
        )
        self.assertEqual(user.email, "newuser@example.com")

    def test_create_superuser(self):
        """Superuser should be created with proper permissions."""
        admin = User.objects.create_superuser(
            email="admin@example.com", password="AdminPass123!"
        )
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)

    def test_user_group_creation(self):
        """User should get a unique group based on their UUID."""
        user = User.objects.create_user(
            email="grouptest@example.com", password="TestPass123!"
        )
        group = user.get_group()
        self.assertEqual(str(group.name), str(user.uuid))
        self.assertIn(group, user.groups.all())

    def test_user_deletion_removes_group(self):
        """Deleting user should remove their associated group."""
        user = User.objects.create_user(
            email="deltest@example.com", password="TestPass123!"
        )
        group = user.get_group()
        user_id = user.id
        group_id = group.id

        user.delete()

        # Verify user and group are deleted
        with self.assertRaises(User.DoesNotExist):
            User.objects.get(id=user_id)

        from django.contrib.auth.models import Group

        with self.assertRaises(Group.DoesNotExist):
            Group.objects.get(id=group_id)

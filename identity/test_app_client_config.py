"""
Tests for App Client JWT Configuration

Verifies that:
1. JWT token strategy uses correct import path
2. Only app client is enabled (browser client disabled)
3. App client endpoints work with JWT tokens
4. Browser client endpoints return 404
"""

import json
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.conf import settings

User = get_user_model()


class AppClientConfigurationTests(TestCase):
    """Test app client configuration settings"""

    def test_jwt_token_strategy_import_path_is_correct(self):
        """JWT token strategy should use correct import path"""
        # The correct path is allauth.headless.tokens.strategies.jwt.JWTTokenStrategy
        # NOT allauth.headless.contrib.ninja.token_strategy.JWTTokenStrategy
        self.assertEqual(
            settings.HEADLESS_TOKEN_STRATEGY,
            'allauth.headless.tokens.strategies.jwt.JWTTokenStrategy'
        )

    def test_headless_clients_configured_for_app_only(self):
        """HEADLESS_CLIENTS should be set to ['app'] to disable browser client"""
        self.assertTrue(hasattr(settings, 'HEADLESS_CLIENTS'))
        self.assertEqual(settings.HEADLESS_CLIENTS, ['app'])

    def test_session_engine_uses_signed_cookies(self):
        """SESSION_ENGINE should use signed_cookies for JWT-only auth"""
        self.assertEqual(
            settings.SESSION_ENGINE,
            'django.contrib.sessions.backends.signed_cookies'
        )

    def test_csrf_middleware_not_in_middleware_list(self):
        """CSRF middleware should be removed for JWT auth"""
        self.assertNotIn(
            'django.middleware.csrf.CsrfViewMiddleware',
            settings.MIDDLEWARE
        )


class AppClientEndpointTests(TestCase):
    """Test app client endpoints work correctly with JWT"""

    def setUp(self):
        """Create test user and client"""
        self.client = Client()
        self.user_email = 'testuser@example.com'
        self.user_password = 'TestPass123!'
        self.user = User.objects.create_user(
            email=self.user_email,
            password=self.user_password
        )

    def test_app_login_endpoint_returns_jwt_tokens(self):
        """POST /_allauth/app/v1/auth/login should return JWT tokens in meta"""
        response = self.client.post(
            '/_allauth/app/v1/auth/login',
            data=json.dumps({
                'email': self.user_email,
                'password': self.user_password
            }),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Verify JWT tokens are in meta
        self.assertIn('meta', data)
        self.assertIn('access_token', data['meta'])
        self.assertIn('refresh_token', data['meta'])

        # Verify tokens are non-empty strings
        self.assertTrue(data['meta']['access_token'])
        self.assertTrue(data['meta']['refresh_token'])

    def test_app_login_endpoint_accepts_valid_credentials(self):
        """POST /_allauth/app/v1/auth/login with valid credentials should succeed"""
        response = self.client.post(
            '/_allauth/app/v1/auth/login',
            data=json.dumps({
                'email': self.user_email,
                'password': self.user_password
            }),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)

    def test_app_login_endpoint_rejects_invalid_credentials(self):
        """POST /_allauth/app/v1/auth/login with invalid credentials should fail"""
        response = self.client.post(
            '/_allauth/app/v1/auth/login',
            data=json.dumps({
                'email': self.user_email,
                'password': 'WrongPassword123!'
            }),
            content_type='application/json'
        )

        self.assertNotEqual(response.status_code, 200)

    def test_app_login_returns_refresh_token(self):
        """Login should return refresh token for token rotation"""
        # Login to get tokens
        login_response = self.client.post(
            '/_allauth/app/v1/auth/login',
            data=json.dumps({
                'email': self.user_email,
                'password': self.user_password
            }),
            content_type='application/json'
        )

        self.assertEqual(login_response.status_code, 200)
        login_data = login_response.json()

        # Verify refresh token is provided for token rotation
        self.assertIn('meta', login_data)
        self.assertIn('refresh_token', login_data['meta'])
        self.assertTrue(login_data['meta']['refresh_token'])

        # Verify access token is also provided
        self.assertIn('access_token', login_data['meta'])
        self.assertTrue(login_data['meta']['access_token'])

    def test_app_authenticated_request_with_bearer_token(self):
        """Authenticated request with Bearer token should work"""
        # Login first to get access token
        login_response = self.client.post(
            '/_allauth/app/v1/auth/login',
            data=json.dumps({
                'email': self.user_email,
                'password': self.user_password
            }),
            content_type='application/json'
        )

        self.assertEqual(login_response.status_code, 200)
        login_data = login_response.json()
        access_token = login_data['meta']['access_token']

        # Use access token to access protected endpoint (using /api/me from ninja)
        me_response = self.client.get(
            '/api/me',
            HTTP_AUTHORIZATION=f'Bearer {access_token}'
        )

        self.assertEqual(me_response.status_code, 200)
        me_data = me_response.json()

        # Verify authenticated user is returned
        self.assertEqual(me_data['email'], self.user_email)

    def test_subsequent_logins_do_not_cause_409_conflict(self):
        """Multiple login attempts should not cause 409 Conflict errors"""
        # Login first time
        first_login = self.client.post(
            '/_allauth/app/v1/auth/login',
            data=json.dumps({
                'email': self.user_email,
                'password': self.user_password
            }),
            content_type='application/json'
        )

        self.assertEqual(first_login.status_code, 200)

        # Create new client (simulating new session)
        new_client = Client()

        # Login second time
        second_login = new_client.post(
            '/_allauth/app/v1/auth/login',
            data=json.dumps({
                'email': self.user_email,
                'password': self.user_password
            }),
            content_type='application/json'
        )

        # Should not get 409 Conflict
        self.assertEqual(second_login.status_code, 200)
        self.assertNotEqual(second_login.status_code, 409)


class BrowserClientDisabledTests(TestCase):
    """Test browser client endpoints are not available"""

    def setUp(self):
        """Create test user and client"""
        self.client = Client()
        self.user_email = 'testuser@example.com'
        self.user_password = 'TestPass123!'
        self.user = User.objects.create_user(
            email=self.user_email,
            password=self.user_password
        )

    def test_browser_login_endpoint_returns_404(self):
        """POST /_allauth/browser/v1/auth/login should return 404"""
        response = self.client.post(
            '/_allauth/browser/v1/auth/login',
            data=json.dumps({
                'email': self.user_email,
                'password': self.user_password
            }),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 404)

    def test_browser_session_endpoint_returns_404(self):
        """GET /_allauth/browser/v1/auth/session should return 404"""
        response = self.client.get('/_allauth/browser/v1/auth/session')

        self.assertEqual(response.status_code, 404)

    def test_browser_config_endpoint_returns_404(self):
        """GET /_allauth/browser/v1/config should return 404"""
        response = self.client.get('/_allauth/browser/v1/config')

        self.assertEqual(response.status_code, 404)

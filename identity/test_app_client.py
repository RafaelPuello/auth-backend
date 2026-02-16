"""
Integration tests for app client (JWT-based) authentication endpoints.
Verifies that:
- App client endpoints work with JWT tokens
- Browser client endpoints are disabled (404)
- Authentication flow works correctly
"""

import json
from django.test import TestCase, Client
from django.contrib.auth import get_user_model

User = get_user_model()


class AppClientEndpointTests(TestCase):
    """Test app client endpoints are available and working."""

    def setUp(self):
        """Create test user and client."""
        self.client = Client()
        self.user_email = 'apptest@example.com'
        self.user_password = 'SecureTestPass123!'

        # Create test user
        self.user = User.objects.create_user(
            email=self.user_email,
            password=self.user_password
        )

    def test_app_login_endpoint_exists(self):
        """Verify app client login endpoint is available."""
        response = self.client.post(
            '/_allauth/app/v1/auth/login',
            data=json.dumps({
                'email': self.user_email,
                'password': self.user_password
            }),
            content_type='application/json'
        )
        # Should not be 404 (endpoint exists)
        self.assertNotEqual(response.status_code, 404)

    def test_app_login_returns_jwt_tokens(self):
        """Verify app client login returns JWT tokens in response meta."""
        response = self.client.post(
            '/_allauth/app/v1/auth/login',
            data=json.dumps({
                'email': self.user_email,
                'password': self.user_password
            }),
            content_type='application/json'
        )

        # Login should succeed
        self.assertEqual(response.status_code, 200)

        data = response.json()

        # Response should have meta with tokens
        self.assertIn('meta', data)
        self.assertIn('access_token', data['meta'])
        self.assertIn('refresh_token', data['meta'])

        # Tokens should be non-empty strings
        self.assertTrue(data['meta']['access_token'])
        self.assertTrue(data['meta']['refresh_token'])

    def test_app_session_endpoint_with_bearer_token(self):
        """Verify app client session endpoint works with Bearer token."""
        # First, log in to get tokens
        login_response = self.client.post(
            '/_allauth/app/v1/auth/login',
            data=json.dumps({
                'email': self.user_email,
                'password': self.user_password
            }),
            content_type='application/json'
        )

        self.assertEqual(login_response.status_code, 200)
        tokens = login_response.json()['meta']
        access_token = tokens['access_token']

        # Now use the access token to get session info
        session_response = self.client.get(
            '/_allauth/app/v1/auth/session',
            HTTP_AUTHORIZATION=f'Bearer {access_token}'
        )

        # Should return authenticated user info
        self.assertEqual(session_response.status_code, 200)

        data = session_response.json()
        self.assertIn('data', data)
        self.assertIn('user', data['data'])
        self.assertEqual(data['data']['user']['email'], self.user_email)

    def test_app_refresh_token_endpoint(self):
        """Verify app client refresh token endpoint works."""
        # First, log in to get tokens
        login_response = self.client.post(
            '/_allauth/app/v1/auth/login',
            data=json.dumps({
                'email': self.user_email,
                'password': self.user_password
            }),
            content_type='application/json'
        )

        self.assertEqual(login_response.status_code, 200)
        tokens = login_response.json()['meta']
        refresh_token = tokens['refresh_token']

        # Use refresh token to get new tokens
        refresh_response = self.client.post(
            '/_allauth/app/v1/auth/token',
            data=json.dumps({
                'refresh_token': refresh_token
            }),
            content_type='application/json'
        )

        # Should return new tokens
        self.assertEqual(refresh_response.status_code, 200)

        data = refresh_response.json()
        self.assertIn('meta', data)
        self.assertIn('access_token', data['meta'])
        self.assertIn('refresh_token', data['meta'])


class BrowserClientDisabledTests(TestCase):
    """Test browser client endpoints are disabled (return 404)."""

    def setUp(self):
        """Create test client."""
        self.client = Client()

    def test_browser_login_endpoint_disabled(self):
        """Verify browser client login endpoint returns 404."""
        response = self.client.post(
            '/_allauth/browser/v1/auth/login',
            data=json.dumps({
                'email': 'test@example.com',
                'password': 'password'
            }),
            content_type='application/json'
        )

        # Browser client should be disabled
        self.assertEqual(response.status_code, 404)

    def test_browser_session_endpoint_disabled(self):
        """Verify browser client session endpoint returns 404."""
        response = self.client.get('/_allauth/browser/v1/auth/session')

        # Browser client should be disabled
        self.assertEqual(response.status_code, 404)

    def test_browser_config_endpoint_disabled(self):
        """Verify browser client config endpoint returns 404."""
        response = self.client.get('/_allauth/browser/v1/config')

        # Browser client should be disabled
        self.assertEqual(response.status_code, 404)


class JWTAuthenticationFlowTests(TestCase):
    """Test complete JWT authentication flow with app client."""

    def setUp(self):
        """Create test user and client."""
        self.client = Client()
        self.user_email = 'flowtest@example.com'
        self.user_password = 'SecureTestPass123!'

        self.user = User.objects.create_user(
            email=self.user_email,
            password=self.user_password
        )

    def test_login_invalid_credentials_returns_401(self):
        """Verify login with invalid credentials returns 401."""
        response = self.client.post(
            '/_allauth/app/v1/auth/login',
            data=json.dumps({
                'email': self.user_email,
                'password': 'wrongpassword'
            }),
            content_type='application/json'
        )

        # Should return 401 for invalid credentials
        self.assertEqual(response.status_code, 401)

    def test_session_without_token_returns_401(self):
        """Verify session endpoint without token returns 401."""
        response = self.client.get('/_allauth/app/v1/auth/session')

        # Should return 401 for missing authentication
        self.assertEqual(response.status_code, 401)

    def test_session_with_invalid_token_returns_401(self):
        """Verify session endpoint with invalid token returns 401."""
        response = self.client.get(
            '/_allauth/app/v1/auth/session',
            HTTP_AUTHORIZATION='Bearer invalid_token_here'
        )

        # Should return 401 for invalid token
        self.assertEqual(response.status_code, 401)

    def test_multiple_logins_no_409_conflict(self):
        """Verify multiple login attempts don't cause 409 Conflict errors."""
        # First login
        response1 = self.client.post(
            '/_allauth/app/v1/auth/login',
            data=json.dumps({
                'email': self.user_email,
                'password': self.user_password
            }),
            content_type='application/json'
        )
        self.assertEqual(response1.status_code, 200)

        # Second login (should not cause 409 Conflict)
        response2 = self.client.post(
            '/_allauth/app/v1/auth/login',
            data=json.dumps({
                'email': self.user_email,
                'password': self.user_password
            }),
            content_type='application/json'
        )

        # Should succeed without conflict
        self.assertEqual(response2.status_code, 200)
        self.assertNotEqual(response2.status_code, 409)

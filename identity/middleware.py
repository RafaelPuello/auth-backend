"""
Custom middleware for the identity service.
"""

from django.http import HttpRequest


LOGIN_PATH = "/_allauth/app/v1/auth/login"


class LoginFlushMiddleware:
    """Flush the session before the allauth login endpoint is processed.

    When using a database-backed session engine, a returning user may still
    have an active session from a previous login.  allauth's LoginView checks
    ``request.user.is_authenticated`` at the very beginning of its ``post()``
    handler and returns HTTP 409 Conflict if the user is already authenticated.

    This middleware intercepts POST requests to the login endpoint and flushes
    the existing session before Django's AuthenticationMiddleware populates
    ``request.user``.  Because the session is flushed the user appears
    unauthenticated to the view and the new login proceeds normally.
    """

    def __init__(self, get_response) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest):
        """Flush session on POST to the login endpoint."""
        if request.method == "POST" and request.path == LOGIN_PATH:
            request.session.flush()
        return self.get_response(request)

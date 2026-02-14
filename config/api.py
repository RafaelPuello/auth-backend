from ninja_extra import NinjaExtraAPI
from allauth.headless.contrib.ninja.security import jwt_token_auth, x_session_token_auth

api_router = NinjaExtraAPI(
    title="DigiDex Auth API",
    description="API for authentication using Django Allauth and JWT",
    urls_namespace="auth_api",
)


@api_router.get("/me", auth=[jwt_token_auth, x_session_token_auth])
def get_current_user(request):
    """
    Get current authenticated user information.
    Supports both JWT and session token authentication for compatibility.

    Returns:
        - id: User primary key
        - email: User email address
        - uuid: User UUID (for JWT claims)
        - is_authenticated: Boolean authentication status
    """
    return {
        "id": request.user.pk,
        "email": request.user.email,
        "uuid": str(request.user.uuid),
        "is_authenticated": request.user.is_authenticated,
        "first_name": request.user.first_name,
        "last_name": request.user.last_name,
    }


@api_router.get("/health", auth=None)
def health_check(request):
    """
    Health check endpoint (no authentication required).
    Used for load balancers and monitoring.
    """
    return {"status": "healthy"}

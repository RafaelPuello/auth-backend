from ninja_extra import NinjaExtraAPI
from allauth.headless.contrib.ninja.security import jwt_token_auth, x_session_token_auth

api_router = NinjaExtraAPI(
    title="DigiDex Auth API",
    description="API for authentication using Django Allauth and Ninja JWT",
    urls_namespace="auth_api",
)

@api_router.get("/me", auth=[jwt_token_auth, x_session_token_auth])
def get_current_user(request):
    return {
        "id": request.user.pk,
        "email": request.user.email,
        "username": request.user.username,
    }

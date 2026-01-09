from ninja_jwt.controller import NinjaJWTDefaultController
from ninja_extra import NinjaExtraAPI

api_router = NinjaExtraAPI()
api_router.register_controllers(NinjaJWTDefaultController)
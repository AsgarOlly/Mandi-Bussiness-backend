from rest_framework_simplejwt.authentication import JWTAuthentication

class SafeJWTAuthentication(JWTAuthentication):
    """
    Standard JWT Authentication ensuring invalid or expired tokens
    raise 401 Unauthorized rather than silently degrading to anonymous user.
    """
    pass

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, AuthenticationFailed

class SafeJWTAuthentication(JWTAuthentication):
    """
    Safely authenticates JWT tokens without halting requests on expired or invalid tokens
    when endpoints allow unauthenticated access (AllowAny).
    """
    def authenticate(self, request):
        header = self.get_header(request)
        if header is None:
            return None

        raw_token = self.get_raw_token(header)
        if raw_token is None:
            return None

        try:
            validated_token = self.get_validated_token(raw_token)
            return self.get_user(validated_token), validated_token
        except (InvalidToken, AuthenticationFailed):
            # Expired or corrupted token; degrade to anonymous user rather than breaking all AllowAny views
            return None

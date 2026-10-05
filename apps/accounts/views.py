from rest_framework import viewsets, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from .models import Role, UserProfile
from .serializers import RoleSerializer, UserSerializer
from .permissions import IsAdmin

class RoleViewSet(viewsets.ModelViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [IsAdmin]

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().select_related('profile')
    serializer_class = UserSerializer
    permission_classes = [IsAdmin]

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def login_view(request):
    username = (request.data.get('username') or '').strip()
    password = request.data.get('password') or ''

    if not username or not password:
        return Response(
            {'error': 'Username and password are required.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    user = authenticate(username=username, password=password)

    if not user:
        # Check if user exists but inactive
        existing = User.objects.filter(username=username).first()
        if existing and not existing.is_active:
            return Response(
                {'error': 'Account is inactive. Please contact your administrator.'},
                status=status.HTTP_403_FORBIDDEN
            )
        return Response(
            {'error': 'Invalid username or password.'},
            status=status.HTTP_401_UNAUTHORIZED
        )

    if not user.is_active:
        return Response(
            {'error': 'Account is inactive. Please contact your administrator.'},
            status=status.HTTP_403_FORBIDDEN
        )

    # Attach profile if none exists
    if not hasattr(user, 'profile'):
        admin_role, _ = Role.objects.get_or_create(
            name='Super Admin',
            defaults={'code': 'SUPER_ADMIN', 'description': 'Full System Access'}
        )
        UserProfile.objects.get_or_create(
            user=user,
            defaults={'role': admin_role, 'employee_code': f'EMP-{user.id:03d}'}
        )

    refresh = RefreshToken.for_user(user)
    return Response({
        'refresh': str(refresh),
        'access': str(refresh.access_token),
        'user': UserSerializer(user).data
    })

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def me_view(request):
    return Response(UserSerializer(request.user).data)

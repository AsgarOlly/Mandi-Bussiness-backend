from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from apps.accounts.models import Role, UserProfile

class AuthTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.super_role, _ = Role.objects.get_or_create(code='SUPER_ADMIN', defaults={'name': 'Super Admin'})
        self.user = User.objects.create_user(username='testadmin', password='SecurePassword123!', email='admin@test.com')
        UserProfile.objects.create(user=self.user, role=self.super_role)

    def test_valid_login(self):
        response = self.client.post('/api/v1/auth/login/', {'username': 'testadmin', 'password': 'SecurePassword123!'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_invalid_login(self):
        response = self.client.post('/api/v1/auth/login/', {'username': 'testadmin', 'password': 'WrongPassword'})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('error', response.data)

    def test_inactive_user_cannot_login(self):
        self.user.is_active = False
        self.user.save()
        response = self.client.post('/api/v1/auth/login/', {'username': 'testadmin', 'password': 'SecurePassword123!'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_protected_endpoint_without_token(self):
        response = self.client.get('/api/v1/auth/me/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_protected_endpoint_with_token(self):
        login_resp = self.client.post('/api/v1/auth/login/', {'username': 'testadmin', 'password': 'SecurePassword123!'})
        token = login_resp.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = self.client.get('/api/v1/auth/me/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'testadmin')

    def test_no_auto_create_user_on_login_attempt(self):
        initial_count = User.objects.count()
        response = self.client.post('/api/v1/auth/login/', {'username': 'nonexistentuser', 'password': 'somepassword'})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(User.objects.count(), initial_count)

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.throttling import ScopedRateThrottle
from django.db.models import Q
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.conf import settings
from .serializers import (
    RegisterSerializer, UserSerializer, VenueProfileSerializer, CreatorProfileSerializer,
    AudienceProfileSerializer,
)
from .models import (
    VenueProfile, CreatorProfile, AudienceProfile,
    EmailVerificationToken, PasswordResetToken,
)
from .emails import send_verification_email, send_password_reset_email

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'register'
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Create verification token and send email
        token = EmailVerificationToken.objects.create(user=user)
        try:
            send_verification_email(user, token)
        except Exception:
            pass  # Don't block registration if email fails

        return Response({
            'message': 'Account created. Please check your email to verify your account.',
            'email': user.email,
        }, status=status.HTTP_201_CREATED)


class VerifyEmailView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        token_str = request.data.get('token')
        try:
            token = EmailVerificationToken.objects.select_related('user').get(token=token_str)
        except (EmailVerificationToken.DoesNotExist, ValueError):
            return Response({'error': 'Invalid verification link.'}, status=400)

        if token.is_expired:
            return Response({'error': 'This link has expired. Please request a new one.'}, status=400)

        user = token.user
        user.is_verified = True
        user.save()
        token.delete()

        # Issue JWT tokens
        refresh = RefreshToken.for_user(user)
        return Response({
            'message': 'Email verified successfully!',
            'user': UserSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        })


class ResendVerificationView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get('email')
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({'message': 'If an account exists, a verification email has been sent.'})

        if user.is_verified:
            return Response({'message': 'Email is already verified.'})

        # Delete old tokens and create new one
        user.verification_tokens.all().delete()
        token = EmailVerificationToken.objects.create(user=user)
        try:
            send_verification_email(user, token)
        except Exception:
            pass

        return Response({'message': 'If an account exists, a verification email has been sent.'})


class PasswordResetRequestView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'password_reset'

    def post(self, request):
        email = request.data.get('email')
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({'message': 'If an account exists, a password reset email has been sent.'})

        # Delete old tokens and create new one
        user.reset_tokens.filter(used=False).delete()
        token = PasswordResetToken.objects.create(user=user)
        try:
            send_password_reset_email(user, token)
        except Exception:
            pass

        return Response({'message': 'If an account exists, a password reset email has been sent.'})


class PasswordResetConfirmView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'password_reset'

    def post(self, request):
        token_str = request.data.get('token')
        new_password = request.data.get('password')

        if not new_password or len(new_password) < 8:
            return Response({'error': 'Password must be at least 8 characters.'}, status=400)

        try:
            token = PasswordResetToken.objects.select_related('user').get(token=token_str, used=False)
        except (PasswordResetToken.DoesNotExist, ValueError):
            return Response({'error': 'Invalid or expired reset link.'}, status=400)

        if token.is_expired:
            return Response({'error': 'This reset link has expired. Please request a new one.'}, status=400)

        user = token.user
        user.set_password(new_password)
        user.save()
        token.used = True
        token.save()

        return Response({'message': 'Password reset successfully. You can now sign in.'})


class GoogleAuthView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'login'

    def post(self, request):
        from google.oauth2 import id_token
        from google.auth.transport import requests as google_requests

        credential = request.data.get('credential')
        if not credential:
            return Response({'error': 'No credential provided.'}, status=400)

        try:
            idinfo = id_token.verify_oauth2_token(
                credential, google_requests.Request(), settings.GOOGLE_CLIENT_ID
            )
        except Exception:
            return Response({'error': 'Invalid Google token.'}, status=400)

        email = idinfo.get('email')
        if not email:
            return Response({'error': 'Email not provided by Google.'}, status=400)

        # Find or create user
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # Create new user from Google data
            user = User.objects.create_user(
                username=email.split('@')[0],
                email=email,
                password=None,
                first_name=idinfo.get('given_name', ''),
                last_name=idinfo.get('family_name', ''),
                role=request.data.get('role', 'creator'),
                avatar=idinfo.get('picture', ''),
                is_verified=True,
            )
            # Create profile based on role
            name = f"{user.first_name} {user.last_name}".strip() or user.username
            if user.role == 'venue':
                VenueProfile.objects.create(
                    user=user,
                    organization_name=f"{user.first_name}'s Venue" or name,
                )
            elif user.role == 'audience':
                AudienceProfile.objects.create(user=user, display_name=name)
            else:
                CreatorProfile.objects.create(user=user, display_name=name)

        if not user.is_verified:
            user.is_verified = True
            user.save()

        refresh = RefreshToken.for_user(user)
        return Response({
            'user': UserSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        })


class LoginView(APIView):
    """Custom login that checks email verification."""
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'login'

    def post(self, request):
        from django.contrib.auth import authenticate
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(username=username, password=password)

        if not user:
            return Response({'error': 'Invalid credentials.'}, status=401)

        if not user.is_verified:
            return Response({
                'error': 'Please verify your email before signing in.',
                'email': user.email,
                'needs_verification': True,
            }, status=403)

        refresh = RefreshToken.for_user(user)
        return Response({
            'user': UserSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        })


class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)

    def patch(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class VenueProfileUpdateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request):
        try:
            profile = request.user.venue_profile
        except VenueProfile.DoesNotExist:
            return Response({'detail': 'No venue profile.'}, status=404)
        serializer = VenueProfileSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class CreatorProfileUpdateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request):
        try:
            profile = request.user.creator_profile
        except CreatorProfile.DoesNotExist:
            return Response({'detail': 'No creator profile.'}, status=404)
        serializer = CreatorProfileSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class AudienceProfileUpdateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request):
        try:
            profile = request.user.audience_profile
        except AudienceProfile.DoesNotExist:
            return Response({'detail': 'No audience profile.'}, status=404)
        serializer = AudienceProfileSerializer(profile, data=request.data, partial=True, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class AudienceListView(generics.ListAPIView):
    serializer_class = AudienceProfileSerializer
    permission_classes = [permissions.AllowAny]
    filterset_fields = ['city', 'country']
    search_fields = ['display_name', 'bio', 'city']

    def get_queryset(self):
        # Hide private profiles from anonymous / other users
        qs = AudienceProfile.objects.select_related('user').filter(is_public=True)
        return qs


class AudienceDetailView(generics.RetrieveAPIView):
    serializer_class = AudienceProfileSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'user_id'

    def get_queryset(self):
        user = self.request.user
        qs = AudienceProfile.objects.select_related('user')
        # Private profiles visible only to their owner
        if user.is_authenticated:
            return qs.filter(Q(is_public=True) | Q(user=user))
        return qs.filter(is_public=True)


class VenueListView(generics.ListAPIView):
    queryset = VenueProfile.objects.select_related('user').all()
    serializer_class = VenueProfileSerializer
    permission_classes = [permissions.AllowAny]


class VenueDetailView(generics.RetrieveAPIView):
    queryset = VenueProfile.objects.select_related('user').all()
    serializer_class = VenueProfileSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'user_id'


class CreatorListView(generics.ListAPIView):
    queryset = CreatorProfile.objects.select_related('user').all()
    serializer_class = CreatorProfileSerializer
    permission_classes = [permissions.AllowAny]


class CreatorDetailView(generics.RetrieveAPIView):
    queryset = CreatorProfile.objects.select_related('user').all()
    serializer_class = CreatorProfileSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'user_id'

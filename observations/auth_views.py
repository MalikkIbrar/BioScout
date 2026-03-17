"""
JWT Authentication views for BioScout.

Provides user registration, login, token refresh, and profile endpoints.
"""

import logging

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

logger = logging.getLogger("bioscout")


def _get_tokens_for_user(user: User) -> dict:
    """
    Generate JWT access and refresh tokens for a user.

    Args:
        user: Django User instance.

    Returns:
        Dict with 'access' and 'refresh' token strings.
    """
    refresh = RefreshToken.for_user(user)
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }


@extend_schema(
    summary="Register a new user",
    request=None,
    responses={201: None},
)
@api_view(["POST"])
@permission_classes([AllowAny])
def register_view(request):
    """
    Register a new user account.

    Request JSON:
        username: str (required)
        email: str (required)
        password: str (required, min 8 chars)

    Returns:
        201 with message and user_id on success.
        400 with error details on failure.
    """
    username = request.data.get("username", "").strip()
    email = request.data.get("email", "").strip()
    password = request.data.get("password", "")

    if not username or not email or not password:
        return Response(
            {"error": "username, email, and password are all required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if len(password) < 8:
        return Response(
            {"error": "Password must be at least 8 characters."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if User.objects.filter(username=username).exists():
        return Response(
            {"error": f"Username '{username}' is already taken."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if User.objects.filter(email=email).exists():
        return Response(
            {"error": "An account with this email already exists."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = User.objects.create_user(
        username=username, email=email, password=password
    )
    logger.info("New user registered: %s", username)

    return Response(
        {"message": "User created successfully.", "user_id": user.id},
        status=status.HTTP_201_CREATED,
    )


@extend_schema(
    summary="Login and receive JWT tokens",
    request=None,
    responses={200: None},
)
@api_view(["POST"])
@permission_classes([AllowAny])
def login_view(request):
    """
    Authenticate a user and return JWT tokens.

    Request JSON:
        username: str
        password: str

    Returns:
        200 with access token, refresh token, and user info.
        401 on invalid credentials.
    """
    username = request.data.get("username", "").strip()
    password = request.data.get("password", "")

    if not username or not password:
        return Response(
            {"error": "username and password are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = authenticate(username=username, password=password)
    if user is None:
        return Response(
            {"error": "Invalid credentials."},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    tokens = _get_tokens_for_user(user)
    logger.info("User logged in: %s", username)

    return Response(
        {
            "access": tokens["access"],
            "refresh": tokens["refresh"],
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
            },
        },
        status=status.HTTP_200_OK,
    )


@extend_schema(
    summary="Refresh access token",
    request=None,
    responses={200: None},
)
@api_view(["POST"])
@permission_classes([AllowAny])
def refresh_view(request):
    """
    Obtain a new access token using a valid refresh token.

    Request JSON:
        refresh: str

    Returns:
        200 with new access token.
        401 on invalid/expired refresh token.
    """
    refresh_token = request.data.get("refresh", "")
    if not refresh_token:
        return Response(
            {"error": "'refresh' token is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        token = RefreshToken(refresh_token)
        return Response(
            {"access": str(token.access_token)},
            status=status.HTTP_200_OK,
        )
    except Exception as exc:
        logger.warning("Token refresh failed: %s", exc)
        return Response(
            {"error": "Invalid or expired refresh token."},
            status=status.HTTP_401_UNAUTHORIZED,
        )


@extend_schema(
    summary="Get current authenticated user profile",
    responses={200: None},
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me_view(request):
    """
    Return the profile of the currently authenticated user.

    Requires: Authorization: Bearer <access_token>

    Returns:
        200 with user id, username, email.
    """
    user = request.user
    return Response(
        {
            "id": user.id,
            "username": user.username,
            "email": user.email,
        },
        status=status.HTTP_200_OK,
    )

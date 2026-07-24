from rest_framework_simplejwt.tokens import RefreshToken


def blacklist_token(refresh_token):
    """Add a refresh token to the blacklist so it becomes invalid."""
    token = RefreshToken(refresh_token)
    token.blacklist()

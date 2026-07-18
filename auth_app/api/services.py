from rest_framework_simplejwt.tokens import RefreshToken


def blacklist_token(refresh_token):
    """Setzt einen Refresh-Token auf die Blacklist, sodass er ungültig wird."""
    token = RefreshToken(refresh_token)
    token.blacklist()

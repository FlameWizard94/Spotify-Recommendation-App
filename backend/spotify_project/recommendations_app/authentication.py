# authentication.py
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.tokens import AccessToken
from .models import Profile

class ProfileAuthentication(BaseAuthentication):
    """
    Custom authentication that uses Profile model and JWT tokens
    """
    
    def authenticate(self, request):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header:
            return None
        
        try:
            # Extract token
            parts = auth_header.split()
            if len(parts) != 2 or parts[0].lower() != 'bearer':
                return None
            
            token = parts[1]
            
            # Validate token
            access_token = AccessToken(token)
            user_id = access_token.payload.get('user_id')
            
            if not user_id:
                raise AuthenticationFailed('Invalid token payload')
            
            # Get profile
            profile = Profile.objects.get(spotify_id=user_id)
            
            # Return (profile, token) - Django expects (user, auth)
            return (profile, token)
            
        except Exception as e:
            raise AuthenticationFailed(str(e))
    
    def authenticate_header(self, request):
        return 'Bearer'
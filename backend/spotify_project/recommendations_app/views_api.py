# views_api.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect
from .models import Profile
from .serializers import *
import secrets
import urllib.parse
from django.conf import settings
from django.shortcuts import redirect
import requests
from .helper_functions import *
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.tokens import AccessToken
import json
from django.http import JsonResponse
from django.db.models import Q
from rest_framework_simplejwt.authentication import JWTAuthentication


# views_api.py
@api_view(['GET'])
@permission_classes([AllowAny])
def spotify_login_api(request):
    """
    Returns the Spotify auth URL instead of redirecting
    """
    print("=" * 50)
    print("SPOTIFY LOGIN API CALLED")
    print("=" * 50)
    
    next_url = request.GET.get('next', '/')
    print(f"Next URL: {next_url}")
    
    # FORCE clear ALL existing session data
    # Instead of pop, flush the entire session
    request.session.flush()  # This completely clears the session and creates a new one
    print("Session flushed completely")
    
    # Generate PKCE codes
    code_verifier = Code_verifier()
    code_challenge = Code_challenge(code_verifier)
    
    # Generate new state
    state = secrets.token_urlsafe(16)
    
    # Store in session
    request.session['spotify_code_verifier'] = code_verifier
    request.session['spotify_state'] = state
    request.session['next_url'] = next_url

    OAuthState.objects.create(
        state=state,
        code_verifier=code_verifier,
        next_url=next_url
    )
    
    # Clean up old states
    OAuthState.cleanup_old_states()
    
    # Force session save
    request.session.save()
    
    print(f"NEW session created - ID: {request.session.session_key}")
    print(f"NEW state: {state}")
    print(f"Session keys: {list(request.session.keys())}")
    
    scope = 'user-read-private user-read-email playlist-modify-public'
    redirect_uri = request.build_absolute_uri('/api/spotify-auth-complete/')
    
    params = {
        'client_id': settings.SPOTIFY_CLIENT_ID,
        'response_type': 'code',
        'redirect_uri': redirect_uri,
        'scope': scope,
        'code_challenge_method': 'S256',
        'code_challenge': code_challenge,
        'state': state,
    }
    
    auth_url = "https://accounts.spotify.com/authorize?" + urllib.parse.urlencode(params)
    
    # Create response
    response = Response({'auth_url': auth_url})
    
    # Delete any existing state cookie first
    response.delete_cookie('spotify_state')
    
    # Set new cookie
    response.set_cookie(
        'spotify_state',
        state,
        max_age=600,
        httponly=True,
        samesite='Lax',
        secure=False,
        path='/',
    )
    
    print(f"Cookie set with state: {state}")
    
    return response


# views_api.py 
@api_view(['GET'])
@permission_classes([AllowAny])
def spotify_auth_complete_api(request):
    """
    Handles Spotify callback and returns JWT tokens
    """
    print("=" * 50)
    print("SPOTIFY CALLBACK RECEIVED")
    print("=" * 50)
    
    code = request.GET.get('code')
    state = request.GET.get('state')
    error = request.GET.get('error')
    
    # Log everything for debugging
    print(f"Full URL: {request.build_absolute_uri()}")
    print(f"Code: {code[:50] if code else 'None'}...")
    print(f"State from URL: {state}")
    print(f"Error from Spotify: {error}")
    
    # If Spotify returned an error
    if error:
        print(f"Spotify error: {error}")
        error_url = f"http://127.0.0.1:3000/auth/callback?error={urllib.parse.quote(f'Spotify error: {error}')}"
        return HttpResponseRedirect(error_url)
    
    if not code:
        print("ERROR: No code provided")
        error_url = f"http://127.0.0.1:3000/auth/callback?error={urllib.parse.quote('No code provided')}"
        return HttpResponseRedirect(error_url)
    
    try:
        # Get OAuth state from database
        oauth_state = OAuthState.objects.get(state=state)
        code_verifier = oauth_state.code_verifier
        next_url = oauth_state.next_url
        print(f"Found OAuth state in DB. Next URL: {next_url}")
        
        # Delete used state immediately to prevent reuse
        oauth_state.delete()
        
    except OAuthState.DoesNotExist:
        print(f"ERROR: No OAuth state found for state: {state}")
        error_url = f"http://127.0.0.1:3000/auth/callback?error={urllib.parse.quote('Invalid or expired state')}"
        return HttpResponseRedirect(error_url)
    
    try:
        # Exchange code for token
        redirect_uri = 'http://127.0.0.1:8000/api/spotify-auth-complete/'
        print(f"Exchanging code for token...")
        
        token_data = exchange_code_for_token(code, code_verifier, redirect_uri)
        print(f"Token exchange successful!")
        
        # Get user profile
        user_profile = get_user_profile(token_data['access_token'])
        print(f"Got user profile: {user_profile.get('display_name')}")
        
        # Create/update profile
        image_url = None
        if user_profile.get('images') and len(user_profile['images']) > 0:
            image_url = user_profile['images'][0].get('url')
        
        profile, created = Profile.objects.update_or_create(
            spotify_id=user_profile['id'],
            defaults={
                'name': user_profile.get('display_name', user_profile['id']),
                'email': user_profile.get('email'),
                'image': image_url,
                'data': user_profile,
                'access_token': token_data.get('access_token'),
                'refresh_token': token_data.get('refresh_token'),
            }
        )
        print(f"Profile {'created' if created else 'updated'}")
        
        # Generate JWT tokens
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken()
        refresh.payload['user_id'] = profile.spotify_id
        refresh.payload['name'] = profile.name
        
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)
        
        # Prepare user data for React
        user_data = {
            'spotify_id': profile.spotify_id,
            'name': profile.name,
            'email': profile.email,
            'image': profile.image,
        }
        
        import json
        user_json = json.dumps(user_data)
        
        # Build redirect URL
        react_url = f"http://127.0.0.1:3000/auth/callback?access={access_token}&refresh={refresh_token}&next={next_url}&user={urllib.parse.quote(user_json)}"
        
        print(f"Redirecting to React: {react_url[:150]}...")
        
        return HttpResponseRedirect(react_url)
        
    except Exception as e:
        print(f"ERROR in token exchange: {str(e)}")
        import traceback
        traceback.print_exc()
        
        error_url = f"http://127.0.0.1:3000/auth/callback?error={urllib.parse.quote(str(e))}"
        return HttpResponseRedirect(error_url)


def get_user_profile(access_token):
    """Get user profile from Spotify"""
    headers = {'Authorization': f'Bearer {access_token}'}
    response = requests.get('https://api.spotify.com/v1/me', headers=headers)
    response.raise_for_status()
    return response.json()


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_api(request):
    """Logout by blacklisting refresh token"""
    try:
        refresh_token = request.data.get('refresh')
        token = RefreshToken(refresh_token)
        token.blacklist()
        return Response({'message': 'Successfully logged out'})
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def current_user_api(request):
    """Get current user info from JWT token"""
    try:
        # Get token from header
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return Response({'error': 'No authorization header'}, status=401)
        
        token = auth_header.split()[1]
        access_token = AccessToken(token)
        current_spotify_id = access_token.payload.get('user_id')
        
        # Get profile
        profile = Profile.objects.get(spotify_id=current_spotify_id)
        
        return Response({
            'spotify_id': profile.spotify_id,
            'name': profile.name,
            'email': profile.email,
            'image': profile.image,
            'following': profile.following,
            'visibility': profile.visibility,
        })
        
    except Profile.DoesNotExist:
        return Response({'error': 'User not found'}, status=404)
    except Exception as e:
        print(f"Error in current_user_api: {e}")
        return Response({'error': str(e)}, status=400)
    

@api_view(['GET'])
@permission_classes([AllowAny]) 
def api_search_profiles(request):
    '''Used to get profiles for search page'''
    user = get_profile(request)
    term = request.POST.get('term', None)
    if term:
        profile_objects = Profile.objects.filter(~Q(spotify_id=user.spotify_id) &
                                            (Q(spotify_id__icontains=term) | 
                                            Q(name__icontains=term)) &
                                            (~Q(visibility='private'))
                )
    else:
        profile_objects = Profile.objects.filter(~Q(spotify_id=user.spotify_id) 
                                                  & ~Q(visibility='private')
                )

    
        
    print(term)
    print(f'profiles\n{profile_objects}')
    #profiles_list = list(profiles_objects)
    serializer = ProfileSerializer(profile_objects, many=True)
        
    return Response({'profiles': serializer.data})


@api_view(['GET'])
@permission_classes([AllowAny])
def view_profile_api(request, spotify_id):
    """Returns individual profile"""
    print("Viewing id", spotify_id)
    profile = Profile.objects.get(spotify_id=spotify_id)
    serializer = ProfileSerializer(profile, many=False)
    print(serializer.data)

    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def follow_api(request, spotify_id):
    """
    Follow or unfollow a user
    Only need the target user's ID in the URL
    Current user is determined from the JWT token
    """
    try:
        # Get current user from JWT token
        # The request.user should be your Profile object if you set up custom auth
        current_user = request.user
        
        # Alternative: If request.user is not set up, extract from token
        # auth_header = request.headers.get('Authorization')
        # if auth_header:
        #     token = auth_header.split()[1]
        #     access_token = AccessToken(token)
        #     current_spotify_id = access_token.payload.get('user_id')
        #     current_user = Profile.objects.get(spotify_id=current_spotify_id)
        
        target_user = Profile.objects.get(spotify_id=spotify_id)
        
        if spotify_id in current_user.following:
            current_user.following.remove(spotify_id)
            current_user.save()

            print(f'Successfully unfollowed {target_user.name}')

            return Response({
                'status': 'unfollowed',
                'message': f'Successfully unfollowed {target_user.name}',
                'is_following': False
            })

        else:
            current_user.following.append(spotify_id)
            current_user.save()

            print(f'Successfully followed {target_user.name}')

            return Response({
                    'status': 'followed',
                    'message': f'Successfully followed {target_user.name}',
                    'is_following': True
                })
            
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# views_api.py
@api_view(['GET'])
@permission_classes([AllowAny])
def test_session(request):
    """Test endpoint to check session"""
    print("Session test called")
    print(f"Session keys: {list(request.session.keys())}")
    
    # Set a test value
    request.session['test_value'] = 'test123'
    request.session.save()
    
    return Response({
        'session_keys': list(request.session.keys()),
        'session_id': request.session.session_key,
        'test_value': request.session.get('test_value')
    })
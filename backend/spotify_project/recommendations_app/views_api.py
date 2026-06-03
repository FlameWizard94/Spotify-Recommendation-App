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
from .recommendation_functions import make_recommendations
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.tokens import AccessToken
import json
from django.http import JsonResponse
from django.db.models import Q
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from datetime import timedelta
import traceback

class CustomTokenRefreshView(APIView):
    """Custom token refresh that works with Profile model"""
    permission_classes = []
    
    def post(self, request):
        refresh_token = request.data.get('refresh')
        
        if not refresh_token:
            print('Refresh: Refresh token required')
            return Response(
                {'error': 'Refresh token required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Use the existing refresh token to get a new access token
            refresh = RefreshToken(refresh_token)
            
            # Get user_id from the token payload
            user_id = refresh.payload.get('user_id')
            
            if not user_id:
                print('Resresh: missing user id')
                return Response(
                    {'error': 'Invalid token: missing user_id'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            # Verify user exists
            try:
                profile = Profile.objects.get(spotify_id=user_id)
            except Profile.DoesNotExist:
                print('Refresh: User not found')
                return Response(
                    {'error': 'User not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            print('Refresh: Token refreshed')
            return Response({
                'access': str(refresh.access_token),
            })
            
        except TokenError as e:
            return Response(
                {'error': 'Invalid or expired token'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        

def require_profile_api(view_func):
    """
    Decorator that calls get_profile_header() and passes the result to the view.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        try:
            # Try to get user profile from token
            user_profile = get_profile_header(request)
            return view_func(request, user_profile, *args, **kwargs)
        except Profile.DoesNotExist:
            return Response({'error': 'User not found'}, status=404)
        except Exception as e:
            print(f"Error in function within require_profile_api wrapper: {e}")
            print(f"Full traceback:")
            traceback.print_exc()
            return Response(
                {'error': str(e)},
                status=getattr(e, 'status_code', 500)
            )
    return wrapper
    
def get_profile_header(request):
    """Returns the current user's profile using JWT Token in auth header"""
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return Response({'error': 'No authorization header'}, status=401)
    
    token = auth_header.split()[1]
    access_token = AccessToken(token)
    current_spotify_id = access_token.payload.get('user_id')
    profile = Profile.objects.get(spotify_id=current_spotify_id)

    return profile


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
        
        expires_in = token_data.get('expires_in', 3600) 
        token_expiry = timezone.now() + timedelta(seconds=expires_in)

        profile, created = Profile.objects.update_or_create(
            spotify_id=user_profile['id'],
            defaults={
                'name': user_profile.get('display_name', user_profile['id']),
                'email': user_profile.get('email'),
                'image': image_url,
                'data': user_profile,
                'access_token': token_data.get('access_token'),
                'refresh_token': token_data.get('refresh_token'),
                'token_expiry': token_expiry,
            }
        )
        print(f"Profile {'created' if created else 'updated'}")
        print(f"{profile.name}'s Token expires in {expires_in} seconds at {token_expiry}")
        
        # Generate JWT tokens
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken()
        refresh.payload['user_id'] = profile.spotify_id
        refresh.payload['name'] = profile.name
        
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)

        serializer = ProfileSerializer(profile, many=False)
        
        user_json = json.dumps(serializer.data)
        
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
@require_profile_api
def logout_api(request, user):
    """Logout by blacklisting refresh token"""
    try:
        refresh_token = request.data.get('refresh')
        #refresh_token = user.refresh_token
        token = RefreshToken(refresh_token)
        token.blacklist()
        return Response({'message': 'Successfully logged out'})
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@require_profile_api
def current_user_api(request, user):
    """Get current user info from JWT token"""
    serializer = ProfileSerializer(user, many=False)
    print(serializer.data)
    
    '''return Response({
        'spotify_id': profile.spotify_id,
        'name': profile.name,
        'email': profile.email,
        'image': profile.image,
        'following': profile.following,
        'visibility': profile.visibility,
        'data' : profile.data,
    })'''

    return Response(serializer.data)

    

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@require_profile_api
def get_following_api(request, user):
    '''Get the current user's followers'''
    followers = Profile.objects.filter(Q(spotify_id__in=user.following))
    serializer = ProfileSerializer(followers, many=True)
    print(serializer.data)

    return Response(serializer.data)

    
@api_view(['GET'])
@permission_classes([IsAuthenticated])
@require_profile_api
def change_visibility_api(request, user):
    '''Change a user's visibility'''
    visibility = request.GET.get('visibility', 'public')
    user.visibility = visibility
    user.save()

    data = {
        'Message' : f'visibility changed to {visibility}'
    }
    
    print(data)
    return Response(data)


@api_view(['GET'])
@permission_classes([AllowAny]) 
def api_search_profiles(request):
    '''Used to get profiles for search page'''
    user = get_profile(request)
    term = request.GET.get('term', None)
    if term:
        print("Term: ", term)
        profile_objects = Profile.objects.filter((~Q(spotify_id=user.spotify_id) &
                                                  (Q(spotify_id__icontains=term) | 
                                                   Q(name__icontains=term)) ) &
                                                    ~Q(visibility='private')
                )
    else:
        profile_objects = Profile.objects.filter(~Q(spotify_id=user.spotify_id) 
                                                  & ~Q(visibility='private')
                )

    
        
    print("Term: ", term)
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
@require_profile_api
def follow_api(request, user, spotify_id):
    """
    Follow or unfollow a user
    Only need the target user's ID in the URL
    Current user is determined from the JWT token
    """
    target_user = Profile.objects.get(spotify_id=spotify_id)
    
    if spotify_id in user.following:
        user.following.remove(spotify_id)
        user.save()

        print(f'Successfully unfollowed {target_user.name}')

        return Response({
            'status': 'unfollowed',
            'message': f'Successfully unfollowed {target_user.name}',
            'is_following': False
        })

    else:
        user.following.append(spotify_id)
        user.save()

        print(f'Successfully followed {target_user.name}')

        return Response({
            'status': 'followed',
            'message': f'Successfully followed {target_user.name}',
            'is_following': True
        })
            


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


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@require_profile_api
def set_preferences_api(request, user):
    """Updates a user's preferences"""
    artists = comma_seperation(request.data.get('fav_artists', ''))
    genres = comma_seperation(request.data.get('fav_genres', ''))
    num_tracks = request.data.get('num_tracks', 10)
    ranking = request.data.get('fav_ranking', 'most popular')
    
    if not user.preferences:
        user.preferences = {}
    
    user.preferences['fav_artists'] = artists
    user.preferences['fav_genres'] = genres
    user.preferences['num_tracks'] = num_tracks
    user.preferences['fav_ranking'] = ranking
    
    user.save()
    
    return Response({
        'message': 'Preferences updated successfully',
        'preferences': user.preferences
    })

    
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@require_profile_api
def add_preset_api(request, user):
    """Creates a preset for the user"""
    name = request.data.get('name', '')
    new_preset_data = {}
    new_preset_data['artists'] = comma_seperation(request.data.get('artists', ''))
    new_preset_data['genres'] = comma_seperation(request.data.get('genres', ''))
    new_preset_data['num_tracks'] = request.data.get('num_tracks', '')
    new_preset_data['ranking'] = request.data.get('ranking', '')
    
    if not user.presets:
        user.presets = {}

    
    if name in user.presets.keys():
        message = f'Preset {name} has been updated.'
    else:
        message = f'Preset {name} has been created.'

    user.presets[name] = new_preset_data
    user.save()
    
    user.save()

    return Response({
        'message': message,
        'preferences': user.presets
    })

    

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
@require_profile_api
def delete_preset_api(request, user):
    """Delete a user's preset"""
    name = request.GET.get('name')
    if name in user.presets.keys():
        user.presets.pop(name)
        message = f'Preset {name} deleted'
        user.save()

    else:
        message = f"Preset {name} didn't exist"

    print(message)

    return Response({'message' : message})

@api_view(['GET'])
@permission_classes([AllowAny])
def get_genres_api(request):
    return Response({'genres' : GENRES})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@require_profile_api
def get_recommendations_api(request, user):
    print("=" * 50)
    print("GET_RECOMMENDATIONS_API CALLED")
    print(f"Request method: {request.method}")
    print(f"Request data: {request.data}")
    print(f"Headers: {dict(request.headers)}")
    print(f"User from decorator: {user}")
    preset = request.data.get('preset', None)
    print('preset:', preset)
    print('User presets: ', user)
    if preset:
        artists = user.presets[preset]['artists']
        artists = comma_seperation(artists)
        print('artisits;', artists)
        genres = user.presets[preset]['genres']
        genres = comma_seperation(genres)
        num_tracks = int(user.presets[preset]['num_tracks'])
        ranking_type = user.presets[preset]['ranking']

    else:   
        artists = request.data.get('artists', None)
        artists = comma_seperation(artists)
        genres = request.data.get('genres', None).strip()
        genres = comma_seperation(genres)
        num_tracks = int(request.data.get('num_tracks'))
        ranking_type = request.data.get('ranking', 'most popular')
    
    print(50 * '=')

    if not user.access_token:
        return Response({'error': 'No Spotify token found'}, status=401)

    spotify_token = user.access_token

    if user and user.access_token:
        spotify_token = user.access_token
        print(f"Using Spotify token for user: {user.name}")
        print(f"Token expiry: {user.token_expiry}")
        
        # Check if token is expired and refresh if needed
        if user.token_expiry and user.token_expiry < timezone.now():
            print("Spotify token expired, need to refresh")
            refreshed_token = refresh_spotify_token(user)
            if refreshed_token:
                spotify_token = refreshed_token
                print("Spotify token refreshed successfully")
            else:
                print('Spotify session expired. Please re-authenticate.')
                return Response(
                    {'error': 'Spotify session expired. Please re-authenticate.'}, 
                    status=401
                )
        else:
            print('Valid Spotify token')
    
    else:
        print('User not authenticated or no Spotify token')
        return Response({'error': 'User not authenticated or no Spotify token'}, status=401)
    

    print(f'''\nRequest\n
            Artists:{artists}
            Wanted Genre: {genres}
            Num tracks: {num_tracks}
            Ranking Type: {ranking_type}''')
    
    recommendations = make_recommendations(access_token=spotify_token,
                                                artists=artists,
                                                requested_genres=genres,
                                                num_tracks=num_tracks,
                                                ranking=ranking_type)
    
    return Response({
        'recommendations' : recommendations,
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@require_profile_api
def get_presets_api(request, user):
    """Gets presets from user and accounts they follow (if availible)"""
    availible_presets = {}
    availible_presets[user.name] = {user.spotify_id : user.presets}
    for id in sorted(user.following):
        profile = Profile.objects.get(spotify_id=id)
        #Verify if user wants to make their preferences known
        if (profile.visibility == 'following' and user.name in profile.following) or profile.visibility == 'public':
            availible_presets[profile.name] = {profile.spotify_id : profile.presets}
            
    
    print(availible_presets)
    return Response({
        'presets' : availible_presets,
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@require_profile_api
def get_group_recommendations_api(request, user):
    """Get group recommendations"""

    # Use sets to automatically remove duplicates
    total_artists = set()
    total_genres = set()
    num_tracks = request.data.get('num_tracks', 0)
    ranking_type = request.data.get('ranking', '')

    selected_presets = request.data.get('presets', [])
    preferences = request.data.get('preferences', [])

    num_tracks_tally = 0
    ranking_tally = {
        'most popular': 0,
        'least popular': 0,
        'random': 0,
        'newest': 0,
        'oldest': 0
    }

    total_preferences = []
    total_presets = {}

    # Process user preferences
    if preferences:
        preference_ids = [p['user_id'] for p in preferences]
        preference_profiles = Profile.objects.filter(spotify_id__in=preference_ids)
        for profile in preference_profiles:
            total_artists.update(comma_seperation(profile.preferences.get('fav_artists', '')))
            total_genres.update(comma_seperation(profile.preferences.get('fav_genres', '')))
            num_tracks_tally += int(profile.preferences.get('num_tracks', 10))
            ranking_tally[profile.preferences.get('fav_ranking', 'most popular')] += 1
            total_preferences.append(profile)

    # Process presets
    if selected_presets:
        print('=' * 50)
        # Get unique user IDs from selected presets
        preset_user_ids = {p['user_id'] for p in selected_presets}
        preset_profiles = Profile.objects.filter(spotify_id__in=preset_user_ids)
        
        for profile in preset_profiles:
            # Get presets that were selected for this user
            user_presets = [p['preset_name'] for p in selected_presets if p['user_id'] == profile.spotify_id]
            
            for preset_name in user_presets:
                preset_data = profile.presets.get(preset_name, {})
                print(preset_data)
                
                # Update sets with preset data
                artists = preset_data.get('artists', '')
                genres = preset_data.get('genres', '')
                
                if isinstance(artists, list):
                    total_artists.update(artists)
                else:
                    total_artists.update(comma_seperation(artists))
                    
                if isinstance(genres, list):
                    total_genres.update(genres)
                else:
                    total_genres.update(comma_seperation(genres))
                
                num_tracks_tally += int(preset_data.get('num_tracks', 10))
                ranking_tally[preset_data.get('ranking', 'most popular')] += 1
                
                # Store preset info
                if profile.spotify_id not in total_presets:
                    total_presets[profile.spotify_id] = []
                total_presets[profile.spotify_id].append({
                    'name': preset_name,
                    'data': preset_data
                })

    # Calculate average number of tracks if not specified
    total_contributors = len(total_preferences) + len(total_presets)
    if num_tracks == 0 and total_contributors > 0:
        num_tracks = num_tracks_tally // total_contributors
    if num_tracks == 0:
        num_tracks = 10

    # Determine ranking type if not specified
    if not ranking_type and ranking_tally:
        ranking_type = max(ranking_tally, key=ranking_tally.get)
    if not ranking_type:
        ranking_type = 'most popular'

    # Convert sets back to lists for the recommendation function
    artists_list = list(total_artists)
    genres_list = list(total_genres)

    print(f"Total unique artists: {len(artists_list)}")
    print(f"Total unique genres: {len(genres_list)}")
    print(f"Calculated num_tracks: {num_tracks}")
    print(f"Selected ranking: {ranking_type}")

    if not user.access_token:
        return Response({'error': 'No Spotify token found. Please re-authenticate.'}, status=401)
    
    spotify_token = user.access_token
    
    # Check if token is expired and refresh if needed
    if user.token_expiry and user.token_expiry < timezone.now():
        print("Spotify token expired, need to refresh")
        refreshed_token = refresh_spotify_token(user)
        if refreshed_token:
            spotify_token = refreshed_token
            print("Spotify token refreshed successfully")
        else:
            print('Spotify session expired. Please re-authenticate.')
            return Response(
                {'error': 'Spotify session expired. Please re-authenticate.'}, 
                status=401
            )
    else:
        print('Valid Spotify token')

    try:
        recommendations = make_recommendations(
            access_token=spotify_token,
            artists=artists_list,
            requested_genres=genres_list,
            num_tracks=int(num_tracks),
            ranking=ranking_type
        )
        
        return Response({
            'recommendations': recommendations,
            'summary': {
                'unique_artists': len(artists_list),
                'unique_genres': len(genres_list),
                'num_tracks': num_tracks,
                'ranking_used': ranking_type,
                'contributors': total_contributors
            }
        })
    except Exception as e:
        print(f"Error making recommendations: {e}")
        return Response({'error': str(e)}, status=500)
    

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@require_profile_api
def make_spotify_playlist_api(request, user):
    """Makes spotify playlist with recommendations"""
    print("=" * 50)
    print("MAKE PLAYLIST API CALLED")
    print(f"Request data: {request.data}")
    print(f"Request data keys: {request.data.keys() if hasattr(request.data, 'keys') else 'Not a dict'}")

    raw_codes = request.data.get('track_ids')
    playlist_name = request.data.get('playlist_name')

    print(f"Raw codes: {raw_codes}")
    print(f"Raw codes type: {type(raw_codes)}")
    print(f"Playlist name: {playlist_name}")

    song_codes_list = [f"spotify:track:{code.strip()}" for code in raw_codes if code]

    if not song_codes_list:
        return Response({'error' : 'No song codes'}, status=500)
    
    if not user.access_token:
        return Response({'error': 'No Spotify token found'}, status=401)
    
    if user.token_expiry and user.token_expiry < timezone.now():
        print("Spotify token expired, need to refresh")
        refreshed_token = refresh_spotify_token(user)
        if refreshed_token:
            spotify_token = refreshed_token
            print("Spotify token refreshed successfully")
        else:
            print('Spotify session expired. Please re-authenticate.')
            return Response(
                {'error': 'Spotify session expired. Please re-authenticate.'}, 
                status=401
            )
    else:
        print('Valid Spotify token')
    
    spotify_token = user.access_token
    
    headers = {
        "Authorization": f"Bearer {spotify_token}",
        "Content-Type": "application/json"
    }

    try:
        create_url = f"https://api.spotify.com/v1/users/{user.spotify_id}/playlists"
        playlist_data = {
            "name": playlist_name if playlist_name else "Music Discovery Hub Mix",
            "description": "Custom mix from spotify recommendation website",
            "public": True 
        }

        create_res = requests.post(create_url, headers=headers, json=playlist_data)
        create_res.raise_for_status()

        playlist_id = create_res.json()['id']

        add_url = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks"
            
        track_data = {
            "uris": song_codes_list
        }

        add_res = requests.post(add_url, headers=headers, json=track_data)
        add_res.raise_for_status()

        return Response({
            'message': f'Playlist created',
            'playlist_url' : add_url
        })
    
    except Exception as e:
        print(f"Error making recommendations: {e}")
        return Response({'error': str(e)}, status=500)
    
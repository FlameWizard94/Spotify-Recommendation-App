from django.shortcuts import render, redirect
import requests
from django.conf import settings
from django.http import JsonResponse
from django.urls import reverse
import urllib.parse
from rest_framework import viewsets
from .helper_functions import *
from .models import *
from .serializers import *
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.db.models import F
from django.contrib import messages


ME = 'https://api.spotify.com/v1/me/albums'
HOME_URI = 'http://127.0.0.1:8000'

VISIBILITIES = ['public', 'following', 'private']

callback = "http://127.0.0.1:8000/spotify/callback/"

def require_profile(view_func):
    """
    Decorator that calls get_profile() and passes the result to the view.
    Redirects to login if get_profile() raises ProfileNotFound.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        try:
            user_profile = get_profile(request)
            return view_func(request, user_profile, *args, **kwargs)
        except ProfileNotFound:
            return redirect(f'{reverse("spotify_login")}?next={request.path}')
    return wrapper


class ProfileViewSet(viewsets.ModelViewSet):
	serializer_class = ProfileSerializer
	queryset = Profile.objects.all()

class RoomViewSet(viewsets.ModelViewSet):
	serializer_class = RoomSerializer
	queryset = Room.objects.all()


def spotify_login(request):
    """Uses PKCE authourization to log into Spotify"""
    next_url = request.GET.get('next', '')
    print("Next:    ", next_url)
    
    if next_url:
        request.session['next_url'] = next_url

    #Generate PKCE codes
    code_verifier = Code_verifier()
    code_challenge = Code_challenge(code_verifier)

    scope = 'user-read-private user-read-email playlist-modify-public'
    
    # Store code_verifier in session for later use
    request.session['spotify_code_verifier'] = code_verifier
    request.session['spotify_state'] = secrets.token_urlsafe(16) #used to prevent CSRF attacks, users logging in with an attackers account
    request.session.modified = True

    redirect_uri = request.build_absolute_uri(reverse('spotify_auth_complete'))
    print(f"DEBUG - Redirect URI: {redirect_uri}")
    
    #Spotify authorization parameters
    params = {
        'client_id': settings.SPOTIFY_CLIENT_ID,
        'response_type': 'code',
        'redirect_uri': redirect_uri,
        'scope': scope,
        'code_challenge_method': 'S256',
        'code_challenge': code_challenge,
        'state': request.session['spotify_state']
    }

    auth_url = "https://accounts.spotify.com/authorize?" + urllib.parse.urlencode(params)
    print(f"DEBUG - Full Auth URL: {auth_url}")
    
    return redirect(auth_url)

def spotify_auth_complete(request):
    """
    Handles Spotify callback from view above.
    Loads profile page and createss/updates profile models
    """
    # Check if we have a code parameter
    code = request.GET.get('code')
    
    if code:
        print(f"DEBUG - Received code in URL: {code}")
        
        #Get the code_verifier from session
        code_verifier = request.session.get('spotify_code_verifier')
        
        if not code_verifier:
            return render(request, 'error.html', {'error': 'Missing code verifier. Please start over.'})
        
        try:
            #Exchange code for token
            redirect_uri = request.build_absolute_uri(reverse('spotify_auth_complete'))
            token_data = exchange_code_for_token(code, code_verifier, redirect_uri)
            
            #Get user profile
            user_profile = get_user_profile(token_data['access_token'])
            print(user_profile)
            
            #Clear session data
            request.session.pop('spotify_code_verifier', None)
            request.session.pop('spotify_state', None)

            image_url = None
            if user_profile.get('images') and len(user_profile['images']) > 0:
                image_url = user_profile['images'][0].get('url')
            
            #Make/update profile model
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
            
            next_url = request.session.pop('next_url', None)
            
            #If we have a next URL, redirect there instead of profile page
            if next_url:
                request.session['user'] = profile.spotify_id
                
                response = redirect(next_url)
                response.set_cookie(
                    'spotify_id',           #Cookie name
                    profile.spotify_id,          #Cookie value
                    max_age=30*24*60*60,         # 30 days in seconds
                    httponly=True,               # More secure (not accessible via JavaScript)
                    samesite='Lax',              # CSRF protection
                    secure=False                 # Set to True in production with HTTPS
                )

                request.session.pop('next_url', None)

                return response

            context = {
                'user': profile,
                'created': created,
                'token_data': token_data,
                'rankings' : RANKING_TYPES,
                'visibilities' : VISIBILITIES,
            }

            response = render(request, 'profile.html', context)
            

            request.session['user'] = profile.spotify_id
            response.set_cookie(
                'spotify_id',           #Cookie name
                profile.spotify_id,          #Cookie value
                max_age=30*24*60*60,         # 30 days in seconds
                httponly=True,               # More secure (not accessible via JavaScript)
                samesite='Lax',              # CSRF protection
                secure=False                 # Set to True in production with HTTPS
            )
            
            return response
            
        except requests.exceptions.RequestException as e:
            return render(request, 'error.html', {'error': str(e)})
    
    else:
        print("DEBUG - No code parameter, redirecting to login")
        return redirect('spotify_login')
    

def spotify_profile(request):
    """
    Used to load profile page using data saved in Profile models
    """
    
    if 'user' in request.session.keys():
        try:
            user_id = request.session['user']
            user = Profile.objects.get(spotify_id=user_id)

            context = {
                    'user': user,
                    'rankings' : RANKING_TYPES,
                    'visibilities' : VISIBILITIES,
                }

            return render(request, 'profile.html', context)
        
        except ObjectDoesNotExist:
            request.session.pop('user')
            return redirect('spotify_login')
        
    else:
        return redirect('spotify_login')
    

def logout(request):
    cookie = request.COOKIES.get('spotify_id', '')
    session = request.session.get('user', '')
    print('Cookie:', cookie)
    print('Session:', session)

    response = redirect('home')
    response.delete_cookie('spotify_id') 

    if 'user' in request.session:
        del request.session['user']
        request.session.modified = True

    return response

def change_visibility(request):
    """Used when a user wants to change their visibility"""
    try:
        user = get_profile(request)
        user.visibility = request.POST.get('visibility', 'public')

        user.save()

        messages.success(request, f'Visibility changed to {user.visibility}')

        return redirect('spotify_profile')


    except ProfileNotFound:
        return redirect('spotify_login')

def set_preferences(request):
    """Used when a user is setting their recommendation preferences"""
    try:
        user = get_profile(request)
        user.preferences['fav_artists'] = request.POST.get('artists', '')
        user.preferences['fav_genres'] = request.POST.get('genres', '')
        user.preferences['fav_num_tracks'] = request.POST.get('num_tracks', '')
        user.preferences['fav_ranking'] = request.POST.get('ranking', '')

        user.save()

        messages.success(request, 'Preferences Updated')

        return redirect('spotify_profile')


    except ProfileNotFound:
        return redirect('spotify_login')
    

def manage_following(request):
    """Used when a user wants to see all the people they follow"""
    try:
        user = get_profile(request)
        following = []
        for id in user.following:
            following.append(Profile.objects.get(spotify_id=id))

        context = {
            'user' : user,
            'following' : following,
        }

        return render(request, 'following.html', context)

    except ProfileNotFound:
        return redirect('spotify_login')
    

def Home(request):
    return render(request, 'home.html')

@require_profile
def recommendation_page(request, user):
    """Display the recommendation form"""
    
    genres = GENRES

    following = {}

    for id in user.following:
        profile = Profile.objects.get(spotify_id=id)
        following[profile.name] = id

    context = {
        'user' : user,
        'genres': sorted(genres), 
        'rankings' : RANKING_TYPES,
        'following' : following
    }
    
    return render(request, 'recommendation_page.html', context)

@require_profile
def get_recommendation(request, user):
    """Handle form submission and get recommendations from Spotify"""
    try:
        if request.method == 'POST':
            preset = request.POST.get('preset', None)
            if preset:
                artists = user.presets[preset]['artists']
                print(artists)
                artists = comma_seperation(artists)
                print(artists)
                genre = ''
                multiple_genres = user.presets[preset]['genres']
                multiple_genres = comma_seperation(multiple_genres)
                num_tracks = int(user.presets[preset]['num_tracks'])
                ranking_type = user.presets[preset]['ranking']

            else:   
                artists = request.POST.get('artists', None)
                artists = comma_seperation(artists)
                genre = request.POST.get('genre', None).strip()
                multiple_genres = request.POST.getlist('multiple_genres')
                num_tracks = int(request.POST.get('num_tracks'))
                ranking_type = request.POST.get('ranking', 'most popular')


            token_data = get_client_credentials_token()
            access_token = token_data['access_token']
            
            requested_genres = []
            if genre:
                requested_genres.append(genre)
            if multiple_genres:
                requested_genres.extend(multiple_genres)

            print(f'''\nRequest\n
                    Artists:{artists}
                    Wanted Genre: {requested_genres}
                    Num tracks: {num_tracks}
                    Ranking Type: {ranking_type}''')

            #recommendations = get_all_artist_tracks(access_token, artist_id)
            
            recommendations = make_recommendations(access_token=access_token,
                                                artists=artists,
                                                requested_genres=requested_genres,
                                                num_tracks=num_tracks,
                                                ranking=ranking_type)
            
            #messages.success(request, f'Artists: {artists}\nGenres: {requested_genres}')
            
            #print(f'Recommendations:\n{recommendations}')

            following = {}
            for id in user.following:
                profile = Profile.objects.get(spotify_id=id)
                following[profile.name] = id

            '''context = {
                'user' : user,
                'limit': num_tracks,
                'got_recommended': True,
                'wanted_genres' : requested_genres,
                'genres': GENRES,
                'rankings' : RANKING_TYPES,
                'recommendations' : recommendations,
                'following' : following
            }'''

            context = {
                'user' : user,
                'recommendations' : recommendations,
                'artists' : artists
            }
            
            return render(request, 'show_recommendations.html', context)
        
        return redirect('recommendation_page')
    except requests.exceptions.RequestException as e:
            return render(request, 'error.html', {'error': str(e)})

@require_profile
def group_recommendation_page(request, user):
    """Load group recommendation page"""
    following = {}
    availible_presets = {}
    name_id_pairs = {}
    for id in sorted(user.following):
        profile = Profile.objects.get(spotify_id=id)
        #Verify if user wants to make their preferences known
        if (profile.visibility == 'following' and user.name in profile.following) or profile.visibility == 'public':
            following[profile.name] = profile.spotify_id
            availible_presets[profile.name] = {profile.spotify_id : profile.presets}
            

    context = {'following' : following,
               'availible_presets' : availible_presets,
               'user' : user,
               'rankings' : RANKING_TYPES,
               'genres' : GENRES}
    
    return render(request, 'group_recommendations.html', context)

@require_profile
def get_group_recommendation(request, user):
    """Returns group recommendations"""
    #Future idea: Weighting with number of artists / tracks?
    try:
        if request.method == 'POST':
            artists = []
            requested_genres = []
            num_tracks = request.POST.get('num_tracks', '')
            ranking_type = request.POST.get('ranking', '')
            num_track_total = 0
            num_track_accumulator = 0
            ranking_tally = {'most popular' : 0,
                                'least popular' : 0,
                                'random' : 0,
                                'newest' : 0,
                                'oldest' : 0}
            total_presets = []
            total_preferences = []

            #Extract preferences and presets
            presets = request.POST.getlist('presets', [])
            preferences = request.POST.getlist('preferences', [])
            if presets:
                for preset in presets:
                    pair = preset.split('|') #[profile_id, preeset_name]
                    profile = Profile.objects.get(spotify_id=pair[0])
                    total_presets.append(profile.presets[pair[1]])

            if preferences:
                for id in preferences:
                    profile = Profile.objects.get(spotify_id=id)
                    if profile.preferences:
                        total_preferences.append(profile.preferences)

            print("total", total_presets)
            #print(f'Presets\n\n{total_presets}')
            #print(f'Preferences\n\n{total_preferences}')

            #Extract genres and artists from presets
            #Gets a ranking type, num tracks to recommend
            for preset in total_presets:
                preset_artists = comma_seperation(preset['artists'])
                artists.extend([artist for artist in preset_artists if artist not in artists])
                preset_genres = comma_seperation(preset['genres'])
                requested_genres.extend([genre for genre in preset_genres if genre not in requested_genres])
                
                if not num_tracks:
                    num_track_total += int(preset['num_tracks'])
                    num_track_accumulator += 1

                if not ranking_type:
                    ranking_tally[preset['ranking']] += 1

    
            for preference in total_preferences:
                preference_artists = comma_seperation(preference['fav_artists'])
                artists.extend([artist for artist in preference_artists if artist not in artists])
                preference_genres = comma_seperation(preference['fav_genres'])
                requested_genres.extend([genre for genre in preference_genres if genre not in requested_genres])

                if not num_tracks:
                    num_track_total += int(preset['num_tracks'])
                    num_track_accumulator += 1

                if not ranking_type:
                    ranking_tally[preset['ranking']] += 1

            #print(f'artists: {artists}')
            #print(f'genres: {genres}')

            if not num_tracks:
                num_tracks = num_track_total / num_track_accumulator

            if not ranking_type:
                ranking_type = max(ranking_tally, key=ranking_tally.get)


            token_data = get_client_credentials_token()
            access_token = token_data['access_token']

            recommendations = make_recommendations(access_token=access_token,
                                                artists=artists,
                                                requested_genres=requested_genres,
                                                num_tracks=int(num_tracks),
                                                ranking=ranking_type)
            
            
            following = {}
            availible_presets = {}
            name_id_pairs = {}
            for id in sorted(user.following):
                profile = Profile.objects.get(spotify_id=id)
                #Verify if user wants to make their preferences known
                if (profile.visibility == 'following' and user.name in profile.following) or profile.visibility == 'public':
                    following[profile.name] = profile.spotify_id
                    availible_presets[profile.name] = {profile.spotify_id : profile.presets}

            '''context = {
                'user' : user,
                'limit': num_tracks,
                'availible_presets' : availible_presets,
                'got_recommended': True,
                'wanted_genres' : requested_genres,
                'genres': GENRES,
                'rankings' : RANKING_TYPES,
                'recommendations' : recommendations,
                'following' : following
            }'''

            context = {
                'user' : user,
                'recommendations' : recommendations,
                'artists' : artists
            }
            
            return render(request, 'show_recommendations.html', context)

        return redirect('group_recommendation_page')

    except requests.exceptions.RequestException as e:
            return render(request, 'error.html', {'error': str(e)})


def search_page(request):
    '''Loads search page
        Handles users searching for profiles'''
    try:
        user = get_profile(request)
        if request.method == 'POST':
            term = request.POST.get('term')
            profiles = Profile.objects.filter(~Q(spotify_id=user.spotify_id) &
                                              (Q(spotify_id__icontains=term) | 
                                              Q(name__icontains=term))
                                            )
            
            print(term)
            print(f'profiles\n{profiles}')
            context = {'user' : user,
                       'profiles' : profiles}
            
            return render(request, 'search.html', context)
    

        profiles = Profile.objects.filter(~Q(spotify_id=user.spotify_id))
        context = {'user' : user,
                   'profiles' : profiles}

        return render(request, 'search.html', context)
    
    except ProfileNotFound:
        return redirect('spotify_login')
    

def view_profile(request, id):
    """Used when a user wants to look at another user's profile"""
    try:
        user = get_profile(request)
        profile = Profile.objects.get(spotify_id=id)

        context = {'user' : user,
                   'profile' : profile}
        
        return render(request, 'view_profile.html', context)

    except ProfileNotFound:
        return redirect('spotify_login')

def follow(request, id):
    """Used when someone wants to follow or unfollow a user"""
    try:
        user = get_profile(request)
        profile = Profile.objects.get(spotify_id=id)

        if profile.spotify_id in user.following:
            user.following.remove(profile.spotify_id)
            messages.success(request, f'Unfollowed {profile.name}')
        else:
            user.following.append(profile.spotify_id)
            messages.success(request, f'Followed {profile.name}')

        user.save()

        next_url = request.GET.get('next', 'view_profile')
        if next_url == 'view_profile':
            return redirect('view_profile', id=profile.spotify_id)
        return redirect(next_url)

    except ProfileNotFound:
        return redirect('spotify_login')
    

@require_profile
def presets(request, user):
    """Used when a user wants to see their presets"""
    if request.method == 'POST':
        name = request.POST.get('name')
        new_preset_data = {}
        new_preset_data['artists'] = request.POST.get('artists', '')
        new_preset_data['genres'] = request.POST.get('genres', '')
        new_preset_data['num_tracks'] = request.POST.get('num_tracks', '')
        new_preset_data['ranking'] = request.POST.get('ranking', '')

        if name in user.presets.keys():
            messages.success(request, f'Preset {name} has been updated.')
        else:
            messages.success(request, f'Preset {name} has been saved.')

        user.presets[name] = new_preset_data
        user.save()


    context = {'user': user,
               'rankings' : RANKING_TYPES}
    return render(request, 'presets.html', context)

@require_profile
def delete_preset(request, user, name):
    user.presets.pop(name)
    user.save()
    messages.success(request, f'Preset {name} removed')
    return redirect('presets')

@require_profile
def spotify_group_recommendations(request, user):
    #this is where we handle the Create or Join buttons
    if request.method == 'POST':
        action = request.POST.get('action')
        
        #user clicked "Create Room"
        if action == 'create_room':
            #generate a random 4 letter code
            room_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))

            new_room = Room(
                room_code=room_code,
                host=user,
                participants=[]
            )
            new_room.save()
            
            #print for debugging
            print(f"User {user.name} made room: {room_code}")
            
            messages.success(request, f"Room {room_code} created successfully!")
            return redirect('room_view', room_code=room_code) #takes user to screen 2
            
        #user clicked "Join Room"
        elif action == 'join_room':
            #get the code they typed in the box
            typed_code = request.POST.get('room_code', '').upper()
            
            try:
                #try to find the room in the database
                room_to_join = Room.objects.get(room_code=typed_code)
                
                #make sure they aren't already in the list so we don't get duplicates
                if user.spotify_id not in room_to_join.participants:
                    room_to_join.participants.append(user.spotify_id)
                    room_to_join.save() #save the updated list to the database
                
                messages.success(request, f"Successfully joined room {typed_code}!")
                
                return redirect('room_view', room_code=typed_code) # brings user to screen 2, into room with participants
                
            except Room.DoesNotExist:
                #if the database can't find the code, it crashes and comes here
                messages.error(request, f"Room {typed_code} does not exist. Try again.")
                return redirect('spotify_group_rec')

    #if they didn't click a button, just load the page normally
    context = {
        'user': user
    }
    return render(request, 'spotify_group_recommendations.html', context)

def room_view(request, room_code):
    #try to find the room in the database
    try:
        room = Room.objects.get(room_code=room_code)
    except Room.DoesNotExist:
        #ff they type a fake URL, kick them back to the start
        messages.error(request, "That room does not exist.")
        return redirect('spotify_group_rec')
    
    #grab the actual Profile objects for everyone in the participants list
    #the __in command is a shortcut to find multiple items in a list at once
    friends = Profile.objects.filter(spotify_id__in=room.participants)
    
    context = {
        'room': room,
        'friends': friends
    }
    
    return render(request, 'room.html', context)

@require_profile
def generate_room_mix(request, user, room_code):
    try:
        room = Room.objects.get(room_code=room_code)
    except Room.DoesNotExist:
        messages.error(request, "Room not found.")
        return redirect('spotify_group_rec')

    #grab everyone in the room
    users = [room.host]
    room_friends = Profile.objects.filter(spotify_id__in=room.participants)
    users.extend([f for f in room_friends if f not in users])

    artist_list = []
    genre_list = []

    #extract preferences for each person
    for person in users:
        if person.preferences:
            fav_arts = person.preferences.get('fav_artists', '')
            fav_gens = person.preferences.get('fav_genres', '')

            if fav_arts:
                arts = [a.strip().lower() for a in fav_arts.split(',')]
                artist_list.append(set(arts))
                
            if fav_gens:
                gens = [g.strip().lower() for g in fav_gens.split(',')]
                genre_list.append(set(gens))

    #find overlaps using set intersection
    match_artists = set()
    if artist_list:
        match_artists = artist_list[0] 
        for subset in artist_list[1:]:
            match_artists = match_artists.intersection(subset)

    match_genres = set()
    if genre_list:
        match_genres = genre_list[0] 
        for subset in genre_list[1:]:
            match_genres = match_genres.intersection(subset)

    #fallback to combining everything if tastes completely clash, using union
    if not match_artists and not match_genres:
        for a_set in artist_list:
            match_artists = match_artists.union(a_set)
        for g_set in genre_list:
            match_genres = match_genres.union(g_set)
            
        #absolute worst case scenario fallback
        if not match_genres:
            match_genres = {'pop', 'hip-hop'}

    #format the final sets for the api request
    final_arts_str = ", ".join(match_artists)
    final_gens_str = ", ".join(match_genres)

    final_artists = comma_seperation(final_arts_str) if final_arts_str else []
    final_genres = comma_seperation(final_gens_str) if final_gens_str else []

    token_data = get_client_credentials_token()
    access_token = token_data['access_token']

    #aask spotify for 20 songs
    recommendations = make_recommendations(
        access_token=access_token,
        artists=final_artists,
        requested_genres=final_genres,
        num_tracks=20, 
        ranking='most popular'
    )

    context = {
        'user': user,
        'recommendations': recommendations,
        'room_code': room.room_code,
        'artists' : final_artists
    }
    return render(request, 'show_recommendations.html', context)


@require_profile
def make_spotify_playlist(request, user):
    if request.method == 'POST':
        raw_codes = request.POST.getlist('song_codes')

        #build the Spotify URI strings
        song_codes_list = [f"spotify:track:{code.strip()}" for code in raw_codes if code]

        if not song_codes_list:
            messages.error(request, "No tracks found to save.")
            return redirect('home')

        headers = {
            "Authorization": f"Bearer {user.access_token}",
            "Content-Type": "application/json"
        }

        try:
            #create the empty playlist first
            create_url = f"https://api.spotify.com/v1/users/{user.spotify_id}/playlists"
            playlist_data = {
                "name": "Music Discovery Hub Mix",
                "description": "Custom mix from my Django project",
                "public": True 
            }

            create_res = requests.post(create_url, headers=headers, json=playlist_data)
            create_res.raise_for_status()
            
            playlist_id = create_res.json()['id']

            #populate the playlist with the tracks
            add_url = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks"
            
            track_data = {
                "uris": song_codes_list
            }

            add_res = requests.post(add_url, headers=headers, json=track_data)
            add_res.raise_for_status()

            messages.success(request, "Success! Check your Spotify for the new playlist.")

        except Exception as e:
            error_message = str(e)
            print("Error saving playlist:", error_message)
            
            #catch the 1-hour timeout
            if "401" in error_message:
                messages.error(request, "Your Spotify session expired! Please log out and log back in to save playlists.")
            else:
                messages.error(request, "Failed to save playlist. Please try again.")

    return redirect('spotify_profile')

def require_profile_api(view_func):
    """
    Decorator for API views that returns JSON instead of redirecting.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        try:
            user_profile = get_profile(request)
            return view_func(request, user_profile, *args, **kwargs)
        except ProfileNotFound:
            return JsonResponse({
                'success': False,
                'error': 'authentication_required',
                'message': 'Please login to access this resource',
                'login_url': reverse('spotify_login'),
                'redirect_url': request.path
            }, status=401)
    return wrapper


@require_profile_api
def api_search_page(request):
    '''Loads search page
        Handles users searching for profiles'''
    user = get_profile(request)
    if request.method == 'POST':
        term = request.POST.get('term')
        profiles = Profile.objects.filter(~Q(spotify_id=user.spotify_id) &
                                            (Q(spotify_id__icontains=term) | 
                                            Q(name__icontains=term))
                                        )
        
        print(term)
        print(f'profiles\n{profiles}')
        context = {'user' : user,
                    'profiles' : profiles}
        
        return render(request, 'search.html', context)


    profiles = Profile.objects.filter(~Q(spotify_id=user.spotify_id))
    context = {'success' : True,
                'user' : user,
                'profiles' : profiles}

    return JsonResponse(context)
    

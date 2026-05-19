import requests
from django.conf import settings
from django.core.cache import cache
from .models import *
import secrets
import string
import random
import hashlib
import base64
import random
from datetime import datetime
from functools import wraps
import concurrent.futures
import queue
import threading
import time

#For commands
ARTISTS = sorted([
            'Kendrick Lamar', 'Tyler the Creator', 'Lady Gaga',
            'Rina Sawayama', 'Childish Gambino', 'Doechii',
            'Taylor Swift'
])

GENRES = sorted([
            'black-metal', 'blues',
            'brazil',
            'children', 'chill', 'classical', 'club',
            'country', 'dance', 'death-metal',
            'electro', 'electronic', 'emo',
            'folk', 'french', 'funk',
            'german', 'gospel', 'goth', 'guitar', 'hardcore',
            'hip-hop',
            'indian', 'indie', 'indie-pop',
            'industrial', 'j-dance', 'j-pop',
            'j-rock', 'jazz', 'k-pop', 'latin',
            'metal',
            'opera',
            'piano', 'pop',
            'progressive', 'punk', 'punk-rock', 'reggae', 'rock',
            'sad',
            'samba', 'ska',
            'sleep', 'soul', 'spanish',
            'swedish',
            'world-music', 'drill'
        ])


RANKING_TYPES = ['most popular',
                 'least popular',
                 'random',
                 'newest',
                 'oldest']


all_tracks = [] #for recommendations
tracks_lock = threading.Lock() #for recommendations
genre_artist_lock = threading.Lock() #for recs

def comma_seperation(phrase):
    """Turns comma seperated phrases into a list"""
    phrase = phrase.strip()
    if not phrase:
        return []
    words = []
    start = 0
    end = 0
    word = ''
    for x in range(len(phrase)):
        if phrase[x] == ',':
            end = x
            word = phrase[start:end]
            start = end + 1
            words.append(word.strip())

    word = phrase[start:len(phrase)]
    words.append(word.strip()) #For last word

    return words


def api_call_limiter(func):
    """Decorator to add exponential backoff to any API call
    Delays API calls if a 429 error occurs"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        max_retries = 5
        base_delay = 1
        
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if '429' in str(e) and hasattr(e, 'response') and attempt < max_retries - 1:
                    # Try to get the Retry-After header
                    retry_after = e.response.headers.get('Retry-After', None)
                    if retry_after:
                        delay = int(retry_after)
                    else:
                        delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                    print(f"Rate limited. Waiting {delay:.2f} seconds...")
                    time.sleep(delay)
                else:
                    raise
        return None
    
    return wrapper


class ProfileNotFound(Exception):
    '''Error for when a user hasn't signed in'''
    pass

def get_profile(request):
    '''used to get the user's account details from cookies'''
    spotify_id = request.COOKIES.get('spotify_id', '')
    print('Got id:', spotify_id)
    try:
        profile = Profile.objects.get(spotify_id=spotify_id)
    except Profile.DoesNotExist:
        raise ProfileNotFound("Profile does not exist")
    
    return profile

#Authorization Code with PKCE Flow
def Code_verifier():
    '''Step 1: Code Verifier
     Create a high-entropy cryptographic random string with a length between 43 and 128 char'''
    
    length = 64
    possible = string.ascii_letters + string.digits  # A-Za-z0-9
    code =  ''.join(secrets.choice(possible) for _ in range(length))

    return code

def Code_challenge(code):
    '''Step2: Code Challenge
    Put generated code verifier in a hash table with a SHA256 algorithm
    This is the value sent in the user authorization request'''

    # SHA-256 hash
    sha256_hash = hashlib.sha256(code.encode('utf-8')).digest()
    
    # Base64 URL-safe encoding (without padding)
    code_challenge = base64.urlsafe_b64encode(sha256_hash).decode('utf-8')
    code_challenge = code_challenge.replace('=', '')  # Remove padding

    print(f"DEBUG Code Challenge - Input: {code}")
    print(f"DEBUG Code Challenge - Output: {code_challenge}")
    print(f"DEBUG Code Challenge - Output length: {len(code_challenge)}")

    return code_challenge

def exchange_code_for_token(auth_code, code_verifier, redirect_uri):
    """Exchange authorization code for access token"""
    url = "https://accounts.spotify.com/api/token"
    
    data = {
        'client_id': settings.SPOTIFY_CLIENT_ID,
        'grant_type': 'authorization_code',
        'code': auth_code,
        'redirect_uri': redirect_uri,
        'code_verifier': code_verifier,
    }
    
    response = requests.post(url, data=data)
    response.raise_for_status()
    
    return response.json()

def get_client_credentials_token():
    """Get access token using client credentials flow"""
    url = "https://accounts.spotify.com/api/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "grant_type": "client_credentials",
        "client_id": settings.SPOTIFY_CLIENT_ID,
        "client_secret": settings.SPOTIFY_CLIENT_SECRET
    }
    
    response = requests.post(url, headers=headers, data=data)
    response.raise_for_status()
    return response.json()


def get_user_profile(access_token):
    """Get current user's profile information"""
    url = "https://api.spotify.com/v1/me"
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    
    return response.json()

#Batch function to get multiple track details in one API call
@api_call_limiter
def batch_get_track_details(access_token, track_ids, batch_size=50):
    """Get details for multiple tracks in batches (50 tracks per API call)"""
    if not track_ids:
        return {}
    
    track_details_dict = {}
    
    for i in range(0, len(track_ids), batch_size):
        batch = track_ids[i:i+batch_size]
        url = f"https://api.spotify.com/v1/tracks/?ids={','.join(batch)}"
        headers = {'Authorization': f'Bearer {access_token}'}
        
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                tracks_data = response.json().get('tracks', [])
                for track in tracks_data:
                    if track:
                        track_details_dict[track['id']] = track
            else:
                print(f"Failed to fetch batch of tracks: {response.status_code}")
        except Exception as e:
            print(f"Error fetching batch of tracks: {e}")
    
    return track_details_dict

#Cached version of artist ID search
def search_artist_id_cached(access_token, artist_name, cache_ttl=86400):
    """Cached version of search_artist_id - caches for 24 hours by default"""
    cache_key = f"artist_id_{artist_name.lower().replace(' ', '_')}"
    cached_id = cache.get(cache_key)
    
    if cached_id:
        print(f"Cache hit for artist ID: {artist_name}")
        return cached_id
    
    artist_id = search_artist_id(access_token, artist_name)
    if artist_id:
        cache.set(cache_key, artist_id, cache_ttl)
    
    return artist_id

# NEW: Cached version of artist albums
def get_artist_albums_cached(access_token, artist_id, limit=50, cache_ttl=86400):
    """Cached version of get_artist_albums"""
    cache_key = f"artist_albums_{artist_id}_{limit}"
    cached_albums = cache.get(cache_key)
    
    if cached_albums:
        print(f"Cache hit for artist albums: {artist_id}")
        return cached_albums
    
    albums_data = get_artist_albums(access_token, artist_id, limit)
    cache.set(cache_key, albums_data, cache_ttl)
    
    return albums_data

#Cached version of album tracks
def get_album_tracks_cached(access_token, album_id, limit=50, cache_ttl=86400):
    """Cached version of get_album_tracks"""
    cache_key = f"album_tracks_{album_id}_{limit}"
    cached_tracks = cache.get(cache_key)
    
    if cached_tracks:
        print(f"Cache hit for album tracks: {album_id}")
        return cached_tracks
    
    tracks_data = get_album_tracks(access_token, album_id, limit)
    cache.set(cache_key, tracks_data, cache_ttl)
    
    return tracks_data

#Cached version of track details
def get_track_details_cached(access_token, track_id, cache_ttl=86400):
    """Cached version of get_track_details"""
    cache_key = f"track_details_{track_id}"
    cached_track = cache.get(cache_key)
    
    if cached_track:
        return cached_track
    
    track_details = get_track_details(access_token, track_id)
    if track_details:
        cache.set(cache_key, track_details, cache_ttl)
    
    return track_details

#Recommendations stuff
def artist_recs(artist_name, requested_genres, access_token, cohesive):
    artist_tracks = []
    artist_id = search_artist_id_cached(access_token, artist_name)  
    if not artist_id:
        print(f"Artist '{artist_name}' not found")
        return []
    
    print(f"Thread {threading.current_thread().name}: Fetching tracks for {artist_name}...")
    
    #Get artist details to check genres
    artist_genres = []
    if requested_genres:
        artist_url = f"https://api.spotify.com/v1/artists/{artist_id}"
        headers = {'Authorization': f'Bearer {access_token}'}
        artist_response = requests.get(artist_url, headers=headers)
        if artist_response.status_code == 200:
            artist_data = artist_response.json()
            artist_genres = artist_data.get('genres', [])
            print(f"{artist_name} genres: {artist_genres}")
    
    #Check if artist matches requested genres (if any)
    include_artist = True
    #commented out due to artist genres not always being availibe from API
    #Also currently doesn't handle minor spelling differences (Hip-hop vs hip hop), hyphon differenciates them
    '''if requested_genres:
        genre_match = False
        for req_genre in requested_genres:
            for artist_genre in artist_genres:
                if req_genre.lower() in artist_genre.lower():
                    genre_match = True
                    break
            if genre_match:
                break
        
        include_artist = genre_match'''
    
    #If artist matches criteria (or no genres specified), get their tracks
    if include_artist:
        if cohesive:
            artist_tracks = get_all_artist_tracks_optimized(access_token, artist_id)  #Use optimized version
        else:
            artist_tracks = get_artist_top_tracks_optimized(access_token, artist_id)  #Use optimized version
        
        #Remove duplicate check (the optimized versions already handle this better)
        #for track in artist_tracks:
        #    track_id = track.get('id')
        #    if track_id and not any(t.get('id') == track_id for t in artist_tracks):
        #        artist_tracks.append(track)

    return artist_tracks


def make_recommendations(access_token, 
                        artists=[], 
                        requested_genres=[], 
                        num_tracks=10, 
                        limit=10,
                        ranking='most popular',
                        cohesive=True):
    """Get recommendations based on criteria
        Cohesive parameter is for if you wanna collect all an artist's tracks or just their top ones"""
    
    recommendation_start = time.time()
    if not artists and not requested_genres:
        return [], "Please specify at least one artist or genre"
    
    # Convert inputs to lists if needed
    if artists and not isinstance(artists, list):
        artists = [artists]
    if requested_genres and not isinstance(requested_genres, list):
        requested_genres = [requested_genres]
    
    global all_tracks
    all_tracks = []
    recommendations = []
    
    if artists:
        #artist_start = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(artists)) as executor:
            future_to_artist = {}
            for artist in artists:
                future = executor.submit(
                    artist_recs, 
                    artist, 
                    requested_genres, 
                    access_token, 
                    cohesive
                )
                future_to_artist[future] = artist 

            for future in concurrent.futures.as_completed(future_to_artist):
                artist = future_to_artist[future]
                artist_tracks = future.result()
                print(f"Got {len(artist_tracks)} tracks from {artist}")
                
                with tracks_lock:
                    existing_ids = {t.get('id') for t in all_tracks if t.get('id')}
                    for track in artist_tracks:
                        if track.get('id') and track['id'] not in existing_ids:
                            all_tracks.append(track)
                            existing_ids.add(track['id'])

        #gathering_artist_tracks = time.time() - artist_start
        #print(f'Getting artist tracks time: {gathering_artist_tracks:.2f}\n')

    if requested_genres:   
        print('Just by genre')
        genre_artists = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(requested_genres)) as executor:
            future_to_genre_artists = {}
            for genre in requested_genres:
                future = executor.submit(
                    search_artists_by_genre_cached,
                    access_token=access_token,
                    genre=genre
                )
                future_to_genre_artists[future] = genre

            for future in concurrent.futures.as_completed(future_to_genre_artists):
                genre = future_to_genre_artists[future]
                artists_found = future.result()
                print(f"Found {len(artists_found)} artists for genre '{genre}'")
                with genre_artist_lock:
                    genre_artists.extend(artists_found)

        genre_artists = [x for x in genre_artists if x not in artists]
        if genre_artists:
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(genre_artists)) as executor:
                future_to_genre_tracks = {}
                for artist in genre_artists:
                    future = executor.submit(
                        get_all_artist_tracks_optimized,  #Use optimized version
                        access_token=access_token,
                        artist_id=artist['id'],
                        max_albums=5
                    )
                    future_to_genre_tracks[future] = artist

                for future in concurrent.futures.as_completed(future_to_genre_tracks):
                    genre_artist_tracks = future.result()

                    with tracks_lock:
                        existing_ids = {t.get('id') for t in all_tracks if t.get('id')}
                        for track in genre_artist_tracks:
                            if track.get('id') and track['id'] not in existing_ids:
                                all_tracks.append(track)
                                existing_ids.add(track['id'])

    for track in all_tracks:
        if 'popularity' not in track:
            track['popularity'] = 0

    #Apply ranking
    recommendations = apply_ranking(all_tracks, ranking, num_tracks)
    recommendation_time = time.time() - recommendation_start
    print(f'Total Recommendation Time: {recommendation_time:.2f}')

    return recommendations


def search_artist_id(access_token, artist_name):
    """Search for an artist and return their Spotify ID"""
    url = "https://api.spotify.com/v1/search"
    headers = {'Authorization': f'Bearer {access_token}'}
    params = {
        'q': artist_name,
        'type': 'artist',
        'limit': 1
    }
    
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    
    artists = response.json().get('artists', {}).get('items', [])
    if artists:
        return artists[0]['id']
    return None

#get_artist_top_tracks with batching
@api_call_limiter
def get_artist_top_tracks_optimized(access_token, artist_id, limit=20):
    """Gets an artist's top tracks with batched album info"""
    url = f"https://api.spotify.com/v1/artists/{artist_id}/top-tracks"
    
    headers = {'Authorization': f'Bearer {access_token}'}
    params = {
        'market': 'US',
        'limit': limit,
    }

    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    
    data = response.json()
    tracks = data.get('tracks', [])

    # Collect unique album IDs for batching
    album_ids = list(set([track.get('album', {}).get('id') for track in tracks if track.get('album', {}).get('id')]))
    
    # Batch fetch album details
    album_details = {}
    for album_id in album_ids:
        album_url = f"https://api.spotify.com/v1/albums/{album_id}"
        album_response = requests.get(album_url, headers=headers)
        if album_response.status_code == 200:
            album_details[album_id] = album_response.json()
    
    # Enhance tracks using cached album details
    enhanced_tracks = []
    for track in tracks:
        enhanced_track = enhance_top_track_with_album_cache(track, album_details)
        if enhanced_track:
            enhanced_tracks.append(enhanced_track)

    for i, track in enumerate(enhanced_tracks, 1):
        print(f"{i}. {track['name']}")
        
    return enhanced_tracks

#Helper function for enhance_top_track with cached album data
def enhance_top_track_with_album_cache(track, album_details_cache):
    """Enhance a track using pre-fetched album details"""
    try:
        album_id = track.get('album', {}).get('id')
        if album_id and album_id in album_details_cache:
            album_data = album_details_cache[album_id]
            
            release_date = album_data.get('release_date', '')
            release_year = None
            if release_date:
                release_year = int(release_date.split('-')[0])
            
            # Create enhanced track
            enhanced_track = {
                'id': track['id'],
                'name': track['name'],
                'artists': track.get('artists', []),
                'album': {
                    'id': album_data['id'],
                    'name': album_data['name'],
                    'images': album_data.get('images', []),
                    'release_date': release_date,
                    'release_year': release_year,
                    'album_type': album_data.get('album_type', 'album')
                },
                'duration_ms': track.get('duration_ms', 0),
                'explicit': track.get('explicit', False),
                'popularity': track.get('popularity', 0),
                'external_urls': track.get('external_urls', {}),
                'preview_url': track.get('preview_url'),
                'track_number': track.get('track_number', 1),
                'disc_number': track.get('disc_number', 1),
            }
            
            return enhanced_track
        
        return {
            'id': track['id'],
            'name': track['name'],
            'artists': track.get('artists', []),
            'album': track.get('album', {}),
            'duration_ms': track.get('duration_ms', 0),
            'explicit': track.get('explicit', False),
            'popularity': track.get('popularity', 0),
            'external_urls': track.get('external_urls', {}),
            'preview_url': track.get('preview_url'),
        }
        
    except Exception as e:
        print(f"Error enhancing track {track.get('name', 'Unknown')}: {e}")
        return track

@api_call_limiter
def get_artist_top_tracks(access_token, artist_id, limit=20):
    """Original get_artist_top_tracks - kept for compatibility"""
    url = f"https://api.spotify.com/v1/artists/{artist_id}/top-tracks"
    
    headers = {'Authorization': f'Bearer {access_token}'}
    params = {
        'market': 'US',
        'limit': limit,
    }

    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    
    data = response.json()
    tracks = data.get('tracks', [])

    enhanced_tracks = []
    for track in tracks:
        enhanced_track = enhance_top_track(access_token, track)
        if enhanced_track:
            enhanced_tracks.append(enhanced_track)

    for i, track in enumerate(enhanced_tracks, 1):
        print(f"{i}. {track['name']}")
        
    return enhanced_tracks


def enhance_track_info(access_token, track, album):
    """Add details to a track - now uses caching"""
    try:
        # Get track details for popularity using cached version
        track_details = get_track_details_cached(access_token, track['id'])
        if not track_details:
            return None
        
        # Extract release year from album
        release_date = album.get('release_date', '')
        release_year = None
        if release_date:
            # Handle different date formats: "2024", "2024-11", "2024-11-21"
            release_year = int(release_date.split('-')[0])
        
        # Combine track info
        enhanced_track = {
            'id': track['id'],
            'name': track['name'],
            'artists': track.get('artists', []),
            'album': {
                'id': album['id'],
                'name': album['name'],
                'images': album.get('images', []),
                'release_date': release_date,
                'release_year': release_year,
                'album_type': album.get('album_type', 'album')
            },
            'duration_ms': track.get('duration_ms', 0),
            'explicit': track.get('explicit', False),
            'popularity': track_details.get('popularity', 0),
            'external_urls': track_details.get('external_urls', {}),
            'preview_url': track_details.get('preview_url'),
            'track_number': track.get('track_number', 1),
            'disc_number': track.get('disc_number', 1),
        }
        
        return enhanced_track
        
    except Exception as e:
        print(f"Error enhancing track {track.get('name', 'Unknown')}: {e}")
        return None
    
@api_call_limiter
def enhance_top_track(access_token, track):
    """Enhance a track from top-tracks endpoint with album info - now uses caching"""
    try:
        album_id = track.get('album', {}).get('id')
        if album_id:
            # Use cached album info if available
            cache_key = f"album_{album_id}"
            album_data = cache.get(cache_key)
            
            if not album_data:
                album_url = f"https://api.spotify.com/v1/albums/{album_id}"
                headers = {'Authorization': f'Bearer {access_token}'}
                album_response = requests.get(album_url, headers=headers)
                
                if album_response.status_code == 200:
                    album_data = album_response.json()
                    cache.set(cache_key, album_data, 86400)  # Cache for 24 hours
            
            if album_data:
                release_date = album_data.get('release_date', '')
                release_year = None
                if release_date:
                    release_year = int(release_date.split('-')[0])
                
                #Create enhanced track
                enhanced_track = {
                    'id': track['id'],
                    'name': track['name'],
                    'artists': track.get('artists', []),
                    'album': {
                        'id': album_data['id'],
                        'name': album_data['name'],
                        'images': album_data.get('images', []),
                        'release_date': release_date,
                        'release_year': release_year,
                        'album_type': album_data.get('album_type', 'album')
                    },
                    'duration_ms': track.get('duration_ms', 0),
                    'explicit': track.get('explicit', False),
                    'popularity': track.get('popularity', 0),
                    'external_urls': track.get('external_urls', {}),
                    'preview_url': track.get('preview_url'),
                    'track_number': track.get('track_number', 1),
                    'disc_number': track.get('disc_number', 1),
                }
                
                return enhanced_track
        
        return {
            'id': track['id'],
            'name': track['name'],
            'artists': track.get('artists', []),
            'album': track.get('album', {}),
            'duration_ms': track.get('duration_ms', 0),
            'explicit': track.get('explicit', False),
            'popularity': track.get('popularity', 0),
            'external_urls': track.get('external_urls', {}),
            'preview_url': track.get('preview_url'),
        }
        
    except Exception as e:
        print(f"Error enhancing track {track.get('name', 'Unknown')}: {e}")
        return track

@api_call_limiter
def get_artist_albums(access_token, artist_id, limit=50):
    """Gets an artist's albums"""
    url = f"https://api.spotify.com/v1/artists/{artist_id}/albums"
    
    headers = {'Authorization': f'Bearer {access_token}'}
    params = {
        'limit': limit,
        'include_groups': 'album,single,compilation',
    }

    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    
    data = response.json()
    albums = data.get('items', [])
    for i, album in enumerate(albums, 1):
        print(f"{i}. {album['name']} ({album['album_type']}) - {album['release_date']}")
        
    return data

@api_call_limiter
def get_album_tracks(access_token, album_id, limit=50):
    """Gets tracks from an album"""
    url = f"https://api.spotify.com/v1/albums/{album_id}/tracks"
    headers = {'Authorization': f'Bearer {access_token}'}
    params = {
        'limit': limit,
    }

    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()

    data = response.json()
    tracks = data.get('items', [])
    
    # Print album and track names
    '''for i, track in enumerate(tracks, 1):
        print(f"{i}. {track['name']} - Duration: {track['duration_ms']//1000}s")'''
        
    return data

#get_all_artist_tracks with batching and caching
def get_all_artist_tracks_optimized(access_token, artist_id, max_albums=50):
    """Get all tracks from an artist's discography with batched API calls and caching"""
    album_tracks_lock = threading.Lock()
    enhanced_tracks = []
    
    #Get artist's albums (cached)
    albums_data = get_artist_albums_cached(access_token, artist_id, limit=max_albums)
    albums = albums_data.get('items', [])
    
    print(f"Found {len(albums)} albums for artist ID {artist_id}")

    if not albums:
        print(f"No albums found for artist ID {artist_id}")
        return [] 
    
    #First, collect all tracks from all albums (in parallel)
    all_tracks_list = []
    track_to_album_map = {}
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(albums), 10)) as executor:
        futures_for_albums = {}
        for album in albums:
            future = executor.submit(
                get_album_tracks_cached,  #Use cached version
                access_token=access_token,
                album_id=album['id']
            )
            futures_for_albums[future] = album

        for future in concurrent.futures.as_completed(futures_for_albums):
            track_data = future.result()
            tracks = track_data.get('items', [])
            album = futures_for_albums[future]
            
            with album_tracks_lock:
                for track in tracks:
                    all_tracks_list.append(track)
                    track_to_album_map[track['id']] = album
    
    #Now batch fetch all track details in as few API calls as possible
    track_ids = [track['id'] for track in all_tracks_list if track.get('id')]
    batch_track_details = batch_get_track_details(access_token, track_ids)
    
    #Enhance all tracks using the batch-fetched details
    for track in all_tracks_list:
        album = track_to_album_map.get(track['id'])
        if album and track['id'] in batch_track_details:
            track_details = batch_track_details[track['id']]
            
            #Extract release year from album
            release_date = album.get('release_date', '')
            release_year = None
            if release_date:
                release_year = int(release_date.split('-')[0])
            
            #Create enhanced track
            enhanced_track = {
                'id': track['id'],
                'name': track['name'],
                'artists': track.get('artists', []),
                'album': {
                    'id': album['id'],
                    'name': album['name'],
                    'images': album.get('images', []),
                    'release_date': release_date,
                    'release_year': release_year,
                    'album_type': album.get('album_type', 'album')
                },
                'duration_ms': track.get('duration_ms', 0),
                'explicit': track.get('explicit', False),
                'popularity': track_details.get('popularity', 0),
                'external_urls': track_details.get('external_urls', {}),
                'preview_url': track_details.get('preview_url'),
                'track_number': track.get('track_number', 1),
                'disc_number': track.get('disc_number', 1),
            }
            enhanced_tracks.append(enhanced_track)
    
    return enhanced_tracks

#Original function kept for backward compatibility
def get_all_artist_tracks(access_token, artist_id, max_albums=50):
    """Original get_all_artist_tracks - kept for compatibility, but you can replace with optimized version"""
    return get_all_artist_tracks_optimized(access_token, artist_id, max_albums)


def get_tracks_by_genre(access_token, genres, limit=40, max_return=100, cohesive=False):
    """Get tracks by genre using genre's top artists"""
    all_tracks = []

    if genres and not isinstance(genres, list):
        genres = [genres]
    
    #For each genre, get top artists and their tracks
    for genre in genres[:5]:  #Limit to 5 genres
        try:
            # Search for artists in this genre
            genre_artists = search_artists_by_genre_cached(access_token, genre)
            
            for artist in genre_artists:
                #Get some tracks from this artist
                if cohesive:
                    artist_tracks = get_all_artist_tracks_optimized(  # Use optimized version
                        access_token, artist['id'], max_albums=5
                    )
                else:
                    artist_tracks = get_artist_top_tracks_optimized(  # Use optimized version
                        access_token, artist['id'], limit
                    )
                all_tracks.extend(artist_tracks)
                
        except Exception as e:
            print(f"Error getting tracks for genre {genre}: {e}")
    
    return all_tracks[:max_return]

@api_call_limiter
def search_artists_by_genre(access_token, genre, limit=3):
    """Search for artists by genre"""
    url = "https://api.spotify.com/v1/search"
    headers = {'Authorization': f'Bearer {access_token}'}
    params = {
        'q': f'genre:"{genre}"',
        'type': 'artist',
        'limit': limit
    }
    
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    
    data = response.json()
    return data.get('artists', {}).get('items', [])


def search_artists_by_genre_cached(access_token, genre, limit=3, cache_ttl=86400):
    """Search for artists by genre with caching"""
    cache_key = f"genre_artists_{genre}"
    cached_artists = cache.get(cache_key)
    
    if cached_artists:
        return cached_artists
    
    artists = search_artists_by_genre(access_token=access_token, genre=genre, limit=limit)
    if artists:
        cache.set(cache_key, artists, cache_ttl)
    
    return artists


@api_call_limiter
def get_track_details(access_token, track_id):
    """Get track details"""
    url = f"https://api.spotify.com/v1/tracks/{track_id}"
    headers = {'Authorization': f'Bearer {access_token}'}
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    return None


def apply_ranking(tracks, ranking, limit):
    """Sort tracks based on ranking criteria"""
    if not tracks:
        return []
    
    #Make sure all tracks have popularity
    for track in tracks:
        if 'popularity' not in track:
            track['popularity'] = 0
    
    if ranking == 'most popular':
        sorted_tracks = sorted(tracks, key=lambda x: x['popularity'], reverse=True)
    elif ranking == 'least popular':
        sorted_tracks = sorted(tracks, key=lambda x: x['popularity'], reverse=False)
    elif ranking == 'random':
        random.shuffle(tracks)
        sorted_tracks = tracks
    elif ranking == 'newest':
        sorted_tracks = sorted(tracks, 
            key=lambda x: x.get('album', {}).get('release_date', ''), 
            reverse=True
        )
    elif ranking == 'oldest':
        sorted_tracks = sorted(tracks, 
            key=lambda x: x.get('album', {}).get('release_date', '9999'), 
            reverse=False
        )
    else:
        #Default: most popular
        sorted_tracks = sorted(tracks, key=lambda x: x['popularity'], reverse=True)
    
    return sorted_tracks[:limit]
import requests
from django.conf import settings
from django.core.cache import cache
from .models import *
import secrets
import string
import hashlib
import base64
import random
from datetime import datetime
from functools import wraps
import concurrent.futures
import threading
import time
from django.utils import timezone
from datetime import timedelta

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


def comma_seperation(phrase):
    """Turns comma seperated phrases into a list"""
    if isinstance(phrase, list):
        return phrase
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

def refresh_spotify_token(user):
    """Refresh an expired Spotify access token"""
    if not user.refresh_token:
        print("No refresh token available")
        return None
    
    url = "https://accounts.spotify.com/api/token"
    data = {
        'grant_type': 'refresh_token',
        'refresh_token': user.refresh_token,
        'client_id': settings.SPOTIFY_CLIENT_ID,
        'client_secret': settings.SPOTIFY_CLIENT_SECRET,
    }
    
    try:
        response = requests.post(url, data=data)
        response.raise_for_status()
        token_data = response.json()
        
        expires_in = token_data.get('expires_in', 3600)
        new_expiry = timezone.now() + timedelta(seconds=expires_in)
        

        user.access_token = token_data['access_token']
        user.token_expiry = new_expiry
        
        # Only update refresh token if a new one is provided
        if 'refresh_token' in token_data:
            user.refresh_token = token_data['refresh_token']
        
        user.save()
        
        print(f"Token refreshed for user {user.name}. New expiry: {user.token_expiry}")
        return user.access_token
        
    except Exception as e:
        print(f"Error refreshing Spotify token: {e}")
        return None




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



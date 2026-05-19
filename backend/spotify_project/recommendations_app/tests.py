from django.test import TestCase
from .helper_functions import *

# Create your tests here.
def genre_availible(genre):
    token_data = get_client_credentials_token()
    access_token = token_data['access_token']
    tracks = get_tracks_by_genre(access_token=access_token,
                        genres=genre)
    
    artists = search_artists_by_genre(access_token, genre, limit=5)
    print(f'Tracks\n\n{tracks}')
    print(f'Artists\n\n{artists}')


#genre_availible('Anime')

class GroupAlgorithmTests(TestCase):
    
    def test_intersection(self):
        #checking if the overlap extraction works correctly
        artist_list = [{'drake', 'kendrick'}, {'kendrick', 'j cole'}]
        
        match_artists = artist_list[0]
        for i in range(1, len(artist_list)):
            match_artists = match_artists.intersection(artist_list[i])
            
        self.assertEqual(match_artists, {'kendrick'})
        
    def test_union(self):
        #testing what happens if users have totally opposite tastes
        genre_list = [{'heavy metal'}, {'k-pop'}]
        
        match_genres = genre_list[0]
        for i in range(1, len(genre_list)):
            match_genres = match_genres.intersection(genre_list[i])
            
        #if the intersection is empty we combine them instead
        if len(match_genres) == 0:
            for g_set in genre_list:
                match_genres = match_genres.union(g_set)
                
        self.assertEqual(match_genres, {'heavy metal', 'k-pop'})

    def test_failsafe(self):
        #final fallback for brand new accounts with no listening data
        artist_list = []
        genre_list = []
        
        match_artists = set()
        match_genres = set()
        
        if len(match_artists) == 0 and len(match_genres) == 0:
            if len(match_genres) == 0:
                match_genres = {'pop', 'hip-hop'}
                
        self.assertEqual(match_genres, {'pop', 'hip-hop'})

class HelperFunctionTests(TestCase):
    
    def test_comma(self):
        #testing if our app function formats messy user input
        raw_input = " Drake , Taylor Swift,  The Weeknd "
        
        #run the raw string through the helper
        cleaned_list = comma_seperation(raw_input)
        
        #making sure it strips spaces but keeps the original capitalization
        self.assertEqual(cleaned_list, ['Drake', 'Taylor Swift', 'The Weeknd'])
        
    def test_empty(self):
        #making sure a blank text box doesnt crash the function
        raw_input = "   "
        
        cleaned_list = comma_seperation(raw_input)
        
        self.assertEqual(cleaned_list, [])

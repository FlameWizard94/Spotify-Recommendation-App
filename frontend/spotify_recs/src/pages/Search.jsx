// pages/Search.jsx
import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../contexts/AuthContext';

const Search = () => {
  const { user, isAuthenticated, accessToken, spotifyLogin } = useAuth();
  const [searchTerm, setSearchTerm] = useState('');
  const [profiles, setProfiles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Set current user when authenticated
  useEffect(() => {
    if (user) {
      console.log('User data from auth:', user);
    }
  }, [user]);

  // Fetch profiles when authenticated
  useEffect(() => {
    if (isAuthenticated && accessToken) {
      getProfiles();
    }
  }, [isAuthenticated, accessToken]);

  // Search when search term changes (optional - or use button only)
  useEffect(() => {
    if (isAuthenticated && accessToken && searchTerm) {
      const debounceTimer = setTimeout(() => {
        getProfiles();
      }, 500); // Wait 500ms after user stops typing
      
      return () => clearTimeout(debounceTimer);
    }
  }, [searchTerm]);

  const getProfiles = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const url = searchTerm 
        ? `/api/search-profiles/?term=${encodeURIComponent(searchTerm)}`
        : '/api/search-profiles/';
      
      console.log('Fetching from URL:', url);
      
      const response = await fetch(url, {
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${accessToken}`
        },
      });
      
      if (response.status === 401) {
        console.log('Unauthorized, redirecting to login');
        spotifyLogin('/search');
        return;
      }
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      console.log('API Response:', data);
      
      // Backend already filters visibility, so just set the profiles
      const profilesData = Array.isArray(data.profiles) ? data.profiles : [];
      setProfiles(profilesData);
      
    } catch (error) {
      console.error('Search error:', error);
      setError('Failed to load profiles. Please try again.');
      setProfiles([]);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = async (e) => {
    e.preventDefault();
    
    if (!isAuthenticated) {
      spotifyLogin('/search');
      return;
    }
    
    await getProfiles();
  };

  const handleFollowToggle = async (profileId) => {
    try {
      const isFollowing = user?.following?.includes(profileId);
      const endpoint = isFollowing ? 'unfollow' : 'follow';
      
      const response = await fetch(`/api/${endpoint}/${profileId}/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${accessToken}`
        },
      });
      
      if (response.ok) {
        // Refresh profiles to update follow status
        await getProfiles();
      }
    } catch (error) {
      console.error('Follow/unfollow error:', error);
    }
  };

  if (!isAuthenticated) {
    return (
      <div className="container" style={{ textAlign: 'center', marginTop: '50px' }}>
        <h2>Please Login to Search</h2>
        <button onClick={() => spotifyLogin('/search')} className="btn-submit">
          Login with Spotify
        </button>
      </div>
    );
  }

  return (
    <div className="container">
      <h2>Profile Search Page</h2>
      
      <div className="search-bar">
        <form onSubmit={handleSearch}>
          <input
            className="form-input"
            type="text"
            placeholder="Search a user's name or id"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
          <button className="btn-submit" type="submit" disabled={loading}>
            {loading ? 'Searching...' : 'Search'}
          </button>
        </form>
      </div>

      {loading && <p>Loading...</p>}
      
      {error && <p style={{ color: 'red' }}>{error}</p>}

      {!loading && profiles.length === 0 && searchTerm && (
        <p>No profiles found for "{searchTerm}"</p>
      )}

      {!loading && profiles.length === 0 && !searchTerm && (
        <p>Enter a search term to find users</p>
      )}

      {!loading && profiles.map((profile) => (
        <div key={profile.spotify_id} className="profile_card">
          <img
            src={profile.image || '/static/images/default_icon.png'}
            alt={profile.name}
            className="search-image"
            style={{ borderRadius: '50%', width: '100px', height: '100px' }}
            onError={(e) => {
              e.target.src = '/static/images/default_icon.png';
            }}
          />
          
          <h2>{profile.name}</h2>

          {profile.preferences ? (
            <>
              <h4 style={{ marginBottom: 0 }}>
                <strong>Preferences:</strong>
              </h4>
              <ul style={{ marginTop: 0, marginBottom: '20px' }}>
                <li>
                  <strong>Fav artists:</strong> {profile.preferences.fav_artists}
                </li>
                <li>
                  <strong>Fav genres:</strong> {profile.preferences.fav_genres}
                </li>
                <li>
                  <strong>Preferred ranking:</strong> {profile.preferences.fav_ranking}
                </li>
              </ul>
            </>
          ) : (
            <p style={{ fontSize: '21px' }}>
              <strong>Preferences:</strong> <br /> None
            </p>
          )}

          <p>
            <a 
              className="link" 
              href={`/view-profile/${profile.spotify_id}`}
            >
              View Profile
            </a>
          </p>

          <p>
            <a 
              className="link"
              onClick={() => handleFollowToggle(profile.spotify_id)}
              style={{ background: 'none', border: 'none', cursor: 'pointer' }}
            >
              {user?.following?.includes(profile.spotify_id) 
                ? 'Click to unfollow' 
                : 'Click to follow'}
            </a>
          </p>
        </div>
      ))}
    </div>
  );
};

export default Search;
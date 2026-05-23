import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';

const ManageFollowing = () => {
  const { user:currentUser, isAuthenticated, accessToken, spotifyLogin, refreshUser, printUser } = useAuth();
  const [searchTerm, setSearchTerm] = useState('');
  const [following, setFollowing] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (currentUser) {
      printUser(currentUser);
    }
  }, [currentUser, following]);

  useEffect(() => {
    if (isAuthenticated && accessToken) {
      getFollowing();
    }
  }, [isAuthenticated, accessToken]);

  const getFollowing = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const url =  '/api/get-following/';
      
      console.log('Fetching from URL:', url);
      
      const response = await fetch(url, {
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${accessToken}`
        },
      });
      
      if (response.status === 401) {
        console.log('Unauthorized, redirecting to login');
        spotifyLogin('/manage-following');
        return;
      }
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      console.log('API Response:', data);
      
      const followingData = Array.isArray(data) ? data : [];
      setFollowing(followingData);

      console.log("Got following");
      
    } catch (error) {
      console.error('Search error:', error);
      setError('Failed to load following. Please try again.');
      setFollowing([]);
    } finally {
      setLoading(false);
    }
  };

  const handleFollowToggle = async (profileId) => {
    try {
      const isFollowing = currentUser?.following?.includes(profileId);
      
      const response = await fetch(`/api/follow/${profileId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${accessToken}`
        },
      });
      
      if (response.ok) {
        await refreshUser();
        const data = await response.json();
        console.log(data.message)
      }
    } catch (error) {
      console.error('Follow/unfollow error:', error);
    }
  };

  return (
    <div className="container">
      <h1>Following Page</h1>

      {loading && <p>Loading...</p>}
      
      {error && <p style={{ color: 'red' }}>{error}</p>}

      {!loading && following.length === 0 && (
        <p>You're not following anyone</p>
      )}
      {!loading && following.map((profile) => (
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
              {currentUser?.following?.includes(profile.spotify_id) 
                ? 'Click to unfollow' 
                : 'Click to follow'}
            </a>
          </p>
        </div>
      ))}
    </div>
  );

};

export default ManageFollowing;
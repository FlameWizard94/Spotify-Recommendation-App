// pages/ViewProfile.jsx
import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth, printUser } from '../contexts/AuthContext';
import defaultIcon from '../assets/images/default_icon.png';

const View_Profile = () => {
  const { spotifyId } = useParams(); // Get the ID from the URL
  const navigate = useNavigate();
  const { user: currentUser, accessToken, refreshUser, refreshAccessToken, spotifyLogin } = useAuth();
  
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isFollowing, setIsFollowing] = useState(false);


  useEffect(() => {
    if (profile && currentUser) {
      setIsFollowing(currentUser.following?.includes(profile.spotify_id));
    }
  }, [profile, currentUser]);


  const fetchProfile = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      const url = `/api/view-profile/${spotifyId}`;
      console.log('Fetching from URL:', url);

      const response = await fetch(url, {
        headers: {
          'Authorization': `Bearer ${accessToken}`,
          'Content-Type': 'application/json',
        },
      });
      
      if (response.status === 404) {
        setError('Profile not found');
        return;
      }
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      setProfile(data);
      console.log('Profile data:', data);
      
    } catch (error) {
      console.error('Error fetching profile:', error);
      setError('Failed to load profile');
    } finally {
      setLoading(false);
    }
  }, [spotifyId, accessToken]); 

  useEffect(() => {
    if (spotifyId && accessToken) {
      fetchProfile();
    }
  }, [spotifyId, accessToken, fetchProfile]);


  const handleFollowToggle = async () => {
    if (!profile) return;
    
    try {
      const isFollowing = currentUser?.following?.includes(profile.spotify_id);
      const endpoint = isFollowing ? 'unfollow' : 'follow';
      
      const response = await fetch(`/api/follow/${profile.spotify_id}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${accessToken}`,
          'Content-Type': 'application/json',
        },
      });
      
      if (response.status === 401) {
        console.log('Token expired or invalid, attempting to refresh...');
        
        // Try to refresh the token
        const refreshed = await refreshAccessToken();
        
        if (refreshed) {
          // Retry the follow request with new token
          console.log('Token refreshed, retrying follow request...');
          const retryResponse = await fetch(`/api/follow/${profile.spotify_id}`, {
            method: 'POST',
            headers: {
              'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
              'Content-Type': 'application/json',
            },
          });
          
          if (retryResponse.ok) {
            await refreshUser();
            const data = await retryResponse.json();
            console.log(data.message);
          } else {
            throw new Error('Retry failed');
          }
        } else {
          // Refresh failed, redirect to login
          console.log('Token refresh failed, redirecting to login...');
          spotifyLogin(window.location.pathname);
        }
        return;
      }
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      // Success
      await refreshUser();
      const data = await response.json();
      console.log(data.message);
      
    } catch (error) {
      console.error('Follow/unfollow error:', error);
    }
  };

  if (loading) {
    return (
      <div className="container" style={{ textAlign: 'center', marginTop: '50px' }}>
        <div className="spinner"></div>
        <p>Loading profile...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container" style={{ textAlign: 'center', marginTop: '50px' }}>
        <h2>Error</h2>
        <p style={{ color: 'red' }}>{error}</p>
        <button onClick={() => navigate('/search')} className="btn-submit">
          Back to Search
        </button>
      </div>
    );
  }

  if (!profile) {
    return (
      <div className="container" style={{ textAlign: 'center', marginTop: '50px' }}>
        <h2>Profile Not Found</h2>
        <button onClick={() => navigate('/search')} className="btn-submit">
          Back to Search
        </button>
      </div>
    );
  }

  return (
    <div className="container">
        <button 
          onClick={() => navigate('/search')} 
          className="btn-submit"
          style={{ marginBottom: '20px' }}
        >
          ← Back to Search
        </button>

      <h1 style={{ textAlign: 'center' }}>{profile.name}</h1>
        
      <div className="artist-info">
        <div className="profile-card">
          <img
            src={profile.image || defaultIcon}
            alt={profile.name}
            style={{ 
              borderRadius: '50%', 
              width: '150px', 
              height: '150px',
              objectFit: 'cover'
            }}
            onError={(e) => {
              e.target.src = '/static/images/default_icon.png';
            }}
          /> <br></br>

          <button 
            onClick={handleFollowToggle}
            className="btn-submit"
            style={{ marginTop: '20px' }}
          >
            {currentUser?.following?.includes(profile.spotify_id) 
              ? 'Unfollow' 
              : 'Follow'}
          </button>
          
          <p><strong>Spotify ID:</strong> {profile.spotify_id}</p>
          
          <p><strong>Email:</strong> {profile.email}</p>
          
          
        </div>

        {/* Preferences Section */}
        <div className="preferences-section" style={{ marginTop: '30px' }}>
          <h2>Music Preferences</h2>
          
          {profile.preferences ? (
            <div>
              <p><strong>Favorite Artists:</strong> {profile.preferences?.fav_artists || 'None'}</p>
              <p><strong>Favorite Genres:</strong> {profile.preferences?.fav_genres || 'None' }</p>
              <p><strong>Preferred Ranking:</strong> {profile.preferences?.fav_ranking || 'None'}</p>
            </div>
          ) : (
            <p>No preferences set yet.</p>
          )}
        </div>

        {/* Other profile sections */}
        <div className="profile-stats" style={{ marginTop: '30px' }}>
          <h2>Statistics</h2>
          <p>Followers: {profile.followers?.length || 0}</p>
        </div>
      </div>
    </div>
  );
};

export default View_Profile;
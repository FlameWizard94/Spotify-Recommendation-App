import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';

const Profile = () => {
  const { user: currentUser, authFetch, accessToken, spotifyLogin, logout, printUser, refreshUser } = useAuth();
  const [loading, setLoading] = useState(false);
  const [visibility, setVisibility] = useState(currentUser?.visibility || 'public');
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [visibilityChanged, setVisibilityChange] = useState(false);
  const artists = currentUser?.implicit_preferences?.artists || {};
  const genres = currentUser?.implicit_preferences?.genres || {};

  const [formData, setFormData] = useState({
    artists: '',
    genres: '',
    num_tracks: 10,
    ranking: 'most popular'
  });

  useEffect(() => {
    if (currentUser) {
        console.log('User data from Auth:');
        printUser(currentUser);
        console.log(currentUser.implicit_preferences);

    }
  }, [currentUser, printUser]);

  useEffect(() => {
    if (currentUser?.preferences) {
      setFormData({
        artists: currentUser.preferences.fav_artists || '',
        genres: currentUser.preferences.fav_genres || '',
        num_tracks: currentUser.preferences.num_tracks || 10,
        ranking: currentUser.preferences.fav_ranking || 'most popular'
      });
    }
  }, [currentUser]);

  const sortedImpliedArtists = Object.entries(artists)
    .map(([name, data]) => ({
      name: name,
      id: data.id,
      points: data.points
    }))
    .sort((a, b) => b.points - a.points)
    .slice(0, 10);
  

  const sortedImpliedGenres = Object.entries(genres)
    .map(([genre, count]) => ({
      name: genre,
      count: count
    }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 10);


  const handleVisibilityChange = async (event) => {
    event.preventDefault();
    const visibility = event.target.value;
    setLoading(true);

    try{
      const response = await authFetch(`api/visibility/?visibility=${encodeURIComponent(visibility)}`, {
        method : 'GET',
        headers : {
          'Authorization': `Bearer ${accessToken}`,
          'Content-Type': 'application/json',
          }
      });

      if (response.ok) {
        const data = await response.json();
        console.log(data.Message);

        await refreshUser();

        setVisibility(visibility);

        setVisibilityChange(true);

        setTimeout(() => setVisibilityChange(false), 10000);
      }
      else {
        const error = await response.json();
        console.error('Error:', error);
        alert('Failed to update visibility');
      }
    }
    catch (error) {
      console.error('Error updating visibility:', error);
      setError('Failed to load profile');
    } finally {
      setLoading(false);
    }
    };

  const handleUpdateDetails = () => {
    spotifyLogin('/profile'); 
  };

  const handleLogout = () => {
    logout();
  };

  const handleChange = (e) => {
    const { name, value, type } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'number' ? parseInt(value) : value
    }));
  };

  // Handle form submission
  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSuccess(null);
    
    try {
      // Prepare data for backend
      const preferences = {
        fav_artists: formData.artists,
        fav_genres: formData.genres,
        num_tracks: formData.num_tracks,
        fav_ranking: formData.ranking
      };
      
      const response = await authFetch('/api/set-preferences/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${accessToken}`
        },
        body: JSON.stringify(preferences)
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      console.log('Preferences updated:', data);
      
      await refreshUser();
      
      setSuccess('Preferences updated successfully!');
      
      setTimeout(() => setSuccess(null), 10000);
      
    } catch (error) {
      console.error('Error updating preferences:', error);
      setError('Failed to update preferences. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  // Handle form reset
  const handleReset = () => {
    if (currentUser?.preferences) {
      setFormData({
        artists: currentUser.preferences.fav_artists || '',
        genres: currentUser.preferences.fav_genres || '',
        num_tracks: currentUser.preferences.num_tracks || 10,
        ranking: currentUser.preferences.fav_ranking || 'most popular'
      });
    } else {
      setFormData({
        artists: '',
        genres: '',
        num_tracks: 10,
        ranking: 'most popular'
      });
    }
    setError(null);
    setSuccess(null);
  };

  return (
    <div className="container">  
      <h1>Your Spotify Profile</h1>
      <div className="artist-info">
        <img 
          src={currentUser.image} 
          alt="User name" 
          className="artist-image" 
          style={{ borderRadius: '50%' }}  // Inline styles use camelCase
        />
        
        <h2>{currentUser.name}</h2>
        
        <p><strong>Email:</strong> {currentUser.email}</p>
        <p><strong>Spotify Followers:</strong> {currentUser.data.followers.total}</p>
        <p><strong>Country:</strong> {currentUser.data.country} </p>
        <p><strong>Account Type:</strong> {currentUser.data.product} </p>
        
        <p>
          <strong>Spotify Profile: </strong> 
          <a 
            href={currentUser.data.external_urls.spotify}
            target="_blank" 
            rel="noreferrer"
            style={{ color: '#1DB954' }}
          >
            Open in Spotify
          </a>
        </p>
        
        <button 
          className="btn-submit" 
          type="submit"
          onClick={handleUpdateDetails}>Update Details</button>

        

        <button 
          className="btn-red" 
          type="submit"
          onClick={handleLogout}>Logout</button>
      </div>
      <div className="nested-container">
        <h2>
          <a className="link" href="/manage-following">
            People you follow
          </a>
        </h2>
      </div>
    
      
      <div className='nested-container'>
        <h2>Visibility</h2>
        <form className="recommendation-form">
          <div className="form-group">
            {visibilityChanged && (
              <div className="alert-success">
                {`Visibility changed to ${visibility}`}
              </div>
            )}
            <label htmlFor="visibility">Set visibility:</label>
            <select 
              name="visibility" 
              id="visibility" 
              className="form-select"
              onChange={(e) => handleVisibilityChange(e)}
            >
              <option value="public">Public</option>
              <option value="following">Following</option>
              <option value="private">Private</option>
            </select>
            <small className="form-help">
              Public, anyone on this website can search for and see your details.<br />
              Following, only those who you follow can find you.<br />
              Private, no one can see your details.<br />
            </small>
          </div>
        </form>
      </div>
      
      <div className="nested-container">
        <h2>
          <a className="link" href="/profile/presets">Edit Presets</a>
        </h2>
      </div>

      <div className="nested-container">
          <h2>Implicit Preferences</h2>
          <h3 style={{ marginBottom : 0 }}>Artists</h3>
          {sortedImpliedArtists.map((artist, index) => (
            <div key={artist.id} className="list-item">
              <span className="rank"><strong>{index + 1}. </strong></span>
              <span className="name">{artist.name}</span>
            </div>
          ))}
          {sortedImpliedArtists.length === 0 && (
            <p>No artist data available</p>
          )}

          <h3 style={{ marginBottom : 0 }}>Genres</h3>
          {sortedImpliedGenres.map((genre, index) => (
            <div key={genre.name} className="list-item">
              <span className="rank"><strong>{index + 1}. </strong></span>
              <span className="name">{genre.name}</span>
            </div>
          ))}
          {sortedImpliedGenres.length === 0 && (
            <p>No genre data available</p>
          )}
      </div>

      <div className="nested-container">
        <h2>Your Specified Preferences</h2>
        
         <form className="recommendation-form" onSubmit={handleSubmit} onReset={handleReset}>
          {error && (
            <div className="error-message" style={{ color: 'red', marginBottom: '15px' }}>
              {error}
            </div>
          )}
          
          {success && (
            <div className="success-message" style={{ color: 'green', marginBottom: '15px' }}>
              {success}
            </div>
          )}
          
          <div className="form-group">
            <label htmlFor="artist">Preferred Artists:</label>
            <input 
              type="text" 
              name="artists" 
              id="artist" 
              className="form-input" 
              placeholder="e.g., Lady Gaga, Kendrick Lamar"
              value={formData.artists}
              onChange={handleChange}
              disabled={loading}
            />
            <small className="form-help">
              For multiple artists, separate them with commas (optional)
            </small>
          </div>

          <div className="form-group">
            <label htmlFor="genres">Preferred Genres:</label>
            <input 
              type="text" 
              name="genres" 
              id="genres" 
              className="form-input" 
              placeholder="e.g., Rock, Pop, Jazz"
              value={formData.genres}
              onChange={handleChange}
              disabled={loading}
            />
            <small className="form-help">
              For multiple genres, separate them with commas
            </small>
          </div>

          <div className="form-group">
            <label htmlFor="num_tracks">Number of Recommendations:</label>
            <input 
              name="num_tracks" 
              id="num_tracks"
              type="number" 
              step="1" 
              min="1" 
              max="50" 
              className="form-input"
              value={formData.num_tracks}
              onChange={handleChange}
              disabled={loading}
            />
          </div>

          <div className="form-group">
            <label htmlFor="ranking">Preferred ranking:</label>
            <select 
              name="ranking" 
              id="ranking" 
              className="form-select"
              value={formData.ranking}
              onChange={handleChange}
              disabled={loading}
            >
              <option value="most popular">Most Popular</option>
              <option value="least popular">Least Popular</option>
              <option value="newest">Newest</option>
              <option value="oldest">Oldest</option>
              <option value="random">Random</option>
            </select>
          </div>
          
          <div className="form-actions">
            <button type="submit" className="btn-submit" disabled={loading}>
              {loading ? 'Updating...' : 'Update Preferences'}
            </button>
            <button type="reset" className="btn-reset" disabled={loading}>
              Clear Form
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default Profile;
import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';

const Profile = () => {
  const { user: currentUser, isAuthenticated, accessToken, spotifyLogin, logout, printUser, refreshUser } = useAuth();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (currentUser) {
        console.log('User data from Auth:');
        printUser(currentUser);

    }
  }, [currentUser]);

  const handleUpdateDetails = () => {
    spotifyLogin('/profile'); 
  };

  const handleLogout = () => {
    logout();
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
      <div className="form-container">
        <h2>
          <a className="link" href="/manage-following">
            People you follow
          </a>
        </h2>
      </div>

      <br />
      
      <h2>Visibility</h2>
      
      <form className="recommendation-form">
        <div className="form-group">
          <label htmlFor="visibility">Set visibility:</label>
          <select name="visibility" id="visibility" className="form-select">
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
        <button type="submit" className="btn-submit">Update Visibility</button>
      </form>

      <br /><br />
      
      <div className="form-container">
        <h2>
          <a className="link" href="/presets">Edit Presets</a>
        </h2>
      </div>

      <div className="form-container">
        <h2>Update Your Preferences</h2>
        
        <form className="recommendation-form">
          <div className="form-group">
            <label htmlFor="artist">Preferred Artists:</label>
            <input 
              type="text" 
              name="artists" 
              id="artist" 
              className="form-input" 
              placeholder="e.g., Lady Gaga, Kendrick Lamar"
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
            />
            <small className="form-help">
              For multiple genres, separate them with commas
            </small>
          </div>

          <div className="form-group">
            <label htmlFor="num_tracks">Number of Recommendations:</label>
            <input 
              name="num_tracks" 
              type="number" 
              step="1" 
              min="1" 
              max="50" 
              defaultValue="10" 
              className="form-input"
            />
          </div>

          <div className="form-group">
            <label htmlFor="ranking">Preferred ranking:</label>
            <select name="ranking" id="ranking" className="form-select">
              <option value="most popular">Most Popular</option>
              <option value="recent">Recent</option>
              <option value="random">Random</option>
            </select>
          </div>
          
          <div className="form-actions">
            <button type="submit" className="btn-submit">Update Preferences</button>
            <button type="reset" className="btn-reset">Clear Form</button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default Profile;
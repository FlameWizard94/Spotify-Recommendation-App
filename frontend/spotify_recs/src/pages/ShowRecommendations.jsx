import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate, useLocation } from 'react-router-dom';

const ShowRecommendations = () => {
  const { user: currentUser, authFetch, accessToken } = useAuth();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [playlistName, setPlaylistName] = useState('');
  const location = useLocation();
  const navigate = useNavigate();
  
  // Get the recommendations data passed from the previous page
  const { recommendations, requestData, presetName, timestamp } = location.state || {};

  const trackIds = recommendations?.map(track => track.id) || [];

  useEffect(() => {
    console.log('Recommendations:', recommendations);
    console.log('Track IDs:', trackIds);
    console.log('Request data:', requestData);
    console.log('Timestamp', timestamp);
  }, []);

  const handlePlaylistNameChange = (e) => {
    setPlaylistName(e.target.value);
  };

  const handleCreatePlaylist = async (e) => {
    e.preventDefault();
    
    if (trackIds.length === 0) {
      setError('No tracks to add to playlist');
      return;
    }
    
    setLoading(true);
    setError(null);
    
    try {
      const requestData = {
        playlist_name: playlistName,
        track_ids: trackIds,
      };
      
      const response = await authFetch('api/make_playlist_api', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${accessToken}`
        },
        body: JSON.stringify(requestData)
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      console.log('Playlist created:', data);
      
      
      // Open the playlist in Spotify
      
      if (data.playlist_url) {
        alert('Playlist created', data.playlist_url);
      } 
      
      
      // Clear the form
      setPlaylistName('');
      
      
    } catch (error) {
      console.error('Error creating playlist:', error);
      setError(error.message || 'Failed to create playlist. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  if (!recommendations || recommendations.length === 0) {
    return (
      <div className="container">
        <h2>No Recommendations Found</h2>
        <p>No recommendations were generated. Please try different criteria.</p>
        <button onClick={() => navigate('/recommendations')} className="btn-submit">
          Back to Recommendations
        </button>
      </div>
    );
  }

  return (
    <div className="recommendations-container">
      <div className="recommendations-header">
        <h2>Recommendations</h2>
        
        {/* Playlist Creation Form */}
        
          <form onSubmit={handleCreatePlaylist}>
            <div className="form-group">
              <input
                type="text"
                id="playlist_name"
                name="playlist_name"
                className="form-input"
                placeholder="Playlist name"
                value={playlistName}
                onChange={handlePlaylistNameChange}
                disabled={loading}
                required
              />
            </div>
            
            
            {error && (
              <div className="error-message" style={{ color: 'red', marginBottom: '15px' }}>
                {error}
              </div>
            )}
            
            <button 
              type="submit" 
              className="btn-submit"
              disabled={loading || !playlistName.trim()}
            >
              {loading ? 'Creating Playlist...' : 'Save to Spotify as Playlist'}
            </button>
          </form>
        
      </div>
      
      {/* Request Summary */}
      <div className="container" style={{ marginBottom: '20px', padding: '15px', background: '#f5f5f5', borderRadius: '8px' }}>
        <h3>Request Summary:</h3>
        {presetName ? (
          <p><strong>Preset Used:</strong> {presetName}</p>
        ) : (
          <>
            {requestData?.artists && (
              <>
                <h4>Artists:</h4>
                <ul>
                  {requestData.artists.split(',').map((artist, index) => (
                    <li key={index}>{artist.trim()}</li>
                  ))}
                </ul>
              </>
            )}

            {requestData?.preferences && (
              <>
                <h4>Preferences Used:</h4>
                <ul>
                  {requestData.preferences.map((preference, index) => (
                    <li key={index}>{preference.name}</li>
                  ))}
                </ul>
              </>
            )}

            {requestData?.presets && (
              <>
                <h4>Presets:</h4>
                <ul>
                  {requestData.presets.map((preset, index) => (
                    <li key={index}><strong>{preset.user_name?.trim()}:</strong> {preset.preset_name}</li>
                  ))}
                </ul>
              </>
            )}
            
            {requestData?.genres && (
              <>
                <h4>Genres:</h4>
                <ul>
                  {requestData.genres.split(',').map((genre, index) => (
                    <li key={index}>{genre.trim()}</li>
                  ))}
                </ul>
              </>
            )}
            
            {requestData?.num_tracks && (
              <p><strong>Number of Tracks:</strong> {requestData.num_tracks}</p>
            )}
            
            {requestData?.ranking && (
              <p><strong>Ranking:</strong> {requestData.ranking}</p>
            )}
          </>
        )}
        <p><strong>Generated:</strong> {new Date(timestamp).toLocaleString()}</p>
      </div>

      {/* Recommendations List */}
      {recommendations.map((track, index) => (
        <div key={track.id} className="recommendation_card">
          <div className="track_heading">
            <h3>{index + 1}. {track.name}</h3>
          </div>

          {track.album?.images && track.album.images[0] && (
            <img 
              src={track.album.images[0].url}
              alt={`${track.album.name} album cover`}
              className="album_art"
            />
          )}

          <div className="track_details">
            <p><strong>Artists:</strong> 
              {track.artists.map((artist, idx) => (
                <React.Fragment key={artist.id || idx}>
                  {artist.name}
                  {idx !== track.artists.length - 1 && ', '}
                </React.Fragment>
              ))}
            </p>
            <p><strong>Album:</strong> {track.album.name}</p>
            <p><strong>Explicit:</strong> {track.explicit ? 'Yes' : 'No'}</p>
            <p><a href={track.external_urls?.spotify} className="link" target="_blank" rel="noreferrer">Open in Spotify</a></p>
          </div>
        </div>
      ))}
    </div>
  );
};

export default ShowRecommendations;
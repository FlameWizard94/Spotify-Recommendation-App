import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';

const GroupRecommendations = () => {
  const { user: currentUser, authFetch, isAuthenticated, accessToken, printUser, refreshUser } = useAuth();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [presetError, setPresetError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [genres, setGenres] = useState([]);
  const [presets, setPresets] = useState({}); 
  const [following, setFollowing] = useState([]);
  const navigate = useNavigate();

  const [formData, setFormData] = useState({
    preferences: [],
    selectedPresets: [], // Store selected presets as array of { userId, presetName }
    num_tracks: 10,
    ranking: 'most popular'
  });

  useEffect(() => {
    if (currentUser) {
      console.log('User data from Auth:');
      printUser(currentUser);
      getFollowing();
    }
  }, [currentUser, printUser]);

  useEffect(() => {
    getGenres();
    getPresets();
  }, []);

  const getGenres = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/genres/', {
        method: 'GET',
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      setGenres(data.genres || []);
      console.log('Got genres: ', data.genres);
    } catch (error) {
      console.error('Error getting genres:', error);
      setError('Failed to load genres');
    } finally {
      setLoading(false);
    }
  };

  const getPresets = async () => {
    setLoading(true);
    try {
      const response = await authFetch('/api/get-presets/', {
        method: 'GET',
      });
      const data = await response.json();
      setPresets(data.presets || {});
      console.log('Got presets: ', data.presets);
    } catch (error) {
      console.error('Error getting presets:', error);
      setError('Failed to load presets');
    } finally {
      setLoading(false);
    }
  };

  const getFollowing = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const url = '/api/get-following/';
      console.log('Fetching from URL:', url);
      
      const response = await authFetch(url, {
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${accessToken}`
        },
      });
      
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

  const handleChange = (e) => {
    const { name, type, options, selectedOptions } = e.target;
    
    if (name === 'preferences') {
      // Extract selected user data
      const selectedValues = Array.from(selectedOptions).map(option => ({
        spotify_id: option.value,
        name: option.textContent.replace(' (you)', '')
      }));
      setFormData(prev => ({
        ...prev,
        [name]: selectedValues
      }));
    } else if (name === 'selectedPresets') {
      // Handle preset selection - store as objects with userId and presetName
      const selectedValues = Array.from(selectedOptions).map(option => {
        const [userId, presetName] = option.value.split('|');
        return {
          userId: userId,
          presetName: presetName,
          displayName: option.textContent
        };
      });
      setFormData(prev => ({
        ...prev,
        selectedPresets: selectedValues
      }));
    } else if (type === 'select-multiple') {
      const selectedValues = Array.from(selectedOptions).map(option => option.value);
      setFormData(prev => ({
        ...prev,
        [name]: selectedValues
      }));
    } else {
      setFormData(prev => ({
        ...prev,
        [name]: e.target.type === 'number' ? parseInt(e.target.value) : e.target.value
      }));
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSuccess(null);
    
    try {
      // Get selected user IDs from preferences
      const selectedUserIds = formData.preferences.map(preference => ({
        user_id: preference.spotify_id,
        name: preference.name,
      }));
      
      // Get selected presets
      const selectedPresetsData = formData.selectedPresets.map(preset => ({
        user_id: preset.userId,
        preset_name: preset.presetName,
        user_name: preset.displayName
      }));

      if (selectedUserIds.length === 0 && selectedPresetsData.length === 0){
        console.log(`No preset or preference selected`);
        setError(`No preset or preference selected`);
        setLoading(false);
        return;
      };
      
      const requestData = {
        preferences: selectedUserIds,
        presets: selectedPresetsData,
        num_tracks: formData.num_tracks,
        ranking: formData.ranking
      };

      console.log('Request data: ', requestData);
      
      const response = await authFetch('/api/get-group-recommendations/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${accessToken}`
        },
        body: JSON.stringify(requestData)
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      console.log('Recommendations:', data);
      
      navigate('/show-recommendations', { 
        state: { 
          recommendations: data.recommendations,
          requestData: requestData,
          timestamp: new Date().toISOString()
        } 
      });
      
    } catch (error) {
      console.error('Error getting recommendations:', error);
      setError('Failed to get recommendations. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setFormData({
      preferences: [],
      selectedPresets: [],
      num_tracks: 10,
      ranking: 'most popular'
    });
    setError(null);
    setSuccess(null);
  };

  // Function to render preset options from the presets object
  const renderPresetOptions = () => {
    const options = [];
    
    // Loop through each user in the presets object
    for (const [userName, userData] of Object.entries(presets)) {
      // Check if userData has spotify_id (for followed users)
      if (userData.spotify_id && userData.presets) {
        // This is a followed user with nested structure
        for (const [presetName, presetData] of Object.entries(userData.presets)) {
          options.push(
            <option 
              key={`${userData.spotify_id}|${presetName}`} 
              value={`${userData.spotify_id}|${presetName}`}
            >
              {userName} - {presetName}
            </option>
          );
        }
      } else if (typeof userData === 'object' && !userData.spotify_id) {
        // This is the current user - presets are directly in userData
        for (const [presetName, presetData] of Object.entries(userData)) {
          options.push(
            <option 
              key={`${currentUser?.spotify_id}|${presetName}`} 
              value={`${currentUser?.spotify_id}|${presetName}`}
            >
              {userName} - {presetName}
            </option>
          );
        }
      }
    }
    
    return options;
  };

  return (
    <div className="container">
      <h1 id="recommendations">Group Recommendations</h1>

      <div className="form-container">
        <h2>Group Recommendations</h2>
        <form className="recommendation-form" onSubmit={handleSubmit} onReset={handleReset}>
          {error && (
            <div className="error-message" style={{ color: 'red', marginBottom: '15px' }}>
              {error}
            </div>
          )}

          {/* User Preferences Selection */}
          <div className="form-group">
            <label htmlFor="preferences">Select Users:</label>
            <select 
              name="preferences" 
              id="preferences" 
              className="form-select" 
              multiple 
              size="5"
              value={formData.preferences.map(p => p.spotify_id)}
              onChange={handleChange}
              disabled={loading}
            >
              <option value={currentUser?.spotify_id}>{currentUser?.name} (you)</option>
              {!loading && following.map((profile) => (
                  <option key={profile.spotify_id} value={profile.spotify_id}>
                    {profile.name}
                  </option>
              ))}
            </select>
            <small className="form-help">Hold Ctrl/Cmd to select multiple users</small>
          </div>

          {/* Show selected users */}
          {formData.preferences.length > 0 && (
            <div className="form-group">
              <label>Selected Users:</label>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '5px' }}>
                {formData.preferences.map((preference, index) => (
                  <span 
                    key={index} 
                    style={{ 
                      background: '#1DB954', 
                      color: 'white', 
                      padding: '2px 8px', 
                      borderRadius: '12px',
                      fontSize: '12px'
                    }}
                  >
                    {preference.name}
                    <button
                      type="button"
                      onClick={() => {
                        setFormData(prev => ({
                          ...prev,
                          preferences: prev.preferences.filter(p => p.spotify_id !== preference.spotify_id)
                        }));
                      }}
                      style={{ 
                        background: 'none', 
                        border: 'none', 
                        color: 'white', 
                        marginLeft: '5px',
                        cursor: 'pointer'
                      }}
                    >
                      ×
                    </button>
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Presets Selection */}
          <div className="form-group">
            <label htmlFor="selectedPresets">Select Presets:</label>
            <select 
              name="selectedPresets" 
              id="selectedPresets" 
              className="form-select" 
              multiple 
              size="5"
              value={formData.selectedPresets.map(p => `${p.userId}|${p.presetName}`)}
              onChange={handleChange}
              disabled={loading}
            >
              {!loading && Object.entries(presets).map(([userName, userData]) =>
                Object.entries(userData).map(([userId, userPresets]) =>
                  Object.entries(userPresets).map(([presetName, presetData]) => (
                    <option 
                      key={`${userId}|${presetName}`} 
                      value={`${userId}|${presetName}`}
                    >
                      {userId === currentUser?.spotify_id 
                        ? `${userName} - ${presetName} (you)` 
                        : `${userName} - ${presetName}`}
                    </option>
                  ))
                )
              )}
            </select>
            <small className="form-help">Hold Ctrl/Cmd to select multiple presets</small>
          </div>

          {/* Show selected presets */}
          {formData.selectedPresets.length > 0 && (
            <div className="form-group">
              <label>Selected Presets:</label>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '5px' }}>
                {formData.selectedPresets.map((preset, index) => (
                  <span 
                    key={index} 
                    style={{ 
                      background: '#1DB954', 
                      color: 'white', 
                      padding: '2px 8px', 
                      borderRadius: '12px',
                      fontSize: '12px'
                    }}
                  >
                    {preset.displayName}
                    <button
                      type="button"
                      onClick={() => {
                        setFormData(prev => ({
                          ...prev,
                          selectedPresets: prev.selectedPresets.filter(p => 
                            !(p.userId === preset.userId && p.presetName === preset.presetName)
                          )
                        }));
                      }}
                      style={{ 
                        background: 'none', 
                        border: 'none', 
                        color: 'white', 
                        marginLeft: '5px',
                        cursor: 'pointer'
                      }}
                    >
                      ×
                    </button>
                  </span>
                ))}
              </div>
            </div>
          )}

          
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
              {loading ? 'Collecting Recommendations...' : 'Get Recommendations'}
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

export default GroupRecommendations;
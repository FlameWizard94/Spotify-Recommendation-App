import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';

const Recommendations = () => {
  const { user: currentUser, authFetch, isAuthenticated, accessToken, printUser, refreshUser } = useAuth();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [presetError, setPresetError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [genres, setGenres] = useState([]);
  const [presetFormData, setPresetFormData] = useState('');
  const navigate = useNavigate();

  const [formData, setFormData] = useState({
    artists: '',
    genres: '',
    multipleGenres: [],
    num_tracks: 10,
    ranking: 'most popular'
  });

  useEffect(() => {
    if (currentUser) {
        console.log('User data from Auth:');
        printUser(currentUser);
    }
  }, [currentUser, printUser]);

  useEffect(() => {
    getGenres();
  }, []);

  const getGenres = async () => {
    setLoading(true);
    try{
      const response = await fetch('/api/genres/', {
        method : 'GET',
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      setGenres(data.genres || []);
      console.log('Got genres: ', data.genres);
    }
    catch (error) {
      console.error('Error getting genres:', error);
      setError('Failed to load genres');
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e) => {
    const { name, value, type, options, selectedOptions } = e.target;
    
    if (type === 'select-multiple') {
      // Handle multiple select
      const selectedValues = Array.from(selectedOptions).map(option => option.value);
      setFormData(prev => ({
        ...prev,
        [name]: selectedValues
      }));
    } else {
      // Handle regular inputs
      setFormData(prev => ({
        ...prev,
        [name]: type === 'number' ? parseInt(value) : value
      }));
    }
  };

  const handlePresetChange = (e) => {
    const { value } = e.target;
    console.log(`${value}`);
    setPresetFormData(value);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSuccess(null);
    
    try {
      // Combine single genre and multiple genres
      let allGenres = [];
      if (formData.genres) {
        allGenres.push(formData.genres);
      }
      if (formData.multipleGenres && formData.multipleGenres.length > 0) {
        allGenres = [...allGenres, ...formData.multipleGenres];
      }
      
      // Remove duplicates
      allGenres = [...new Set(allGenres)];
      
      const requestData = {
        artists: formData.artists,
        genres: allGenres.join(','),  // Convert array to comma-separated string
        num_tracks: formData.num_tracks,
        ranking: formData.ranking
      };
      
      const response = await authFetch('/api/get-recommendations/', {
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
      setSuccess('Recommendations generated successfully!');

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

  const handleSubmitPreset = async (e) => {
    e.preventDefault();
    setLoading(true);
    setPresetError(null);
    setSuccess(null);

    const name = presetFormData;
    console.log('Using preset:', name);

    if (!name){
      console.log(`No preset selected`);
      setPresetError(`No preset selected`);
      setLoading(false);
      return;
    }

    try {
      
      
      const response = await authFetch(`/api/get-recommendations/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${accessToken}`
        },
        body: JSON.stringify({preset : name}),
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      console.log('Recommendations:', data);
      setSuccess('Recommendations generated successfully!');
      
      navigate('/show-recommendations', { 
        state: { 
          recommendations: data.recommendations,
          presetName: name,
          timestamp: new Date().toISOString()
        } 
      });
      
    } catch (error) {
      console.error(`Error getting preset recommendations with preset ${name}:`, error);
      setPresetError(`Failed to get recommendations from preset ${name}. Please try again.`);
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setFormData({
      artists: '',
      genres: '',
      num_tracks: 10,
      ranking: 'most popular'
    });
    
    setError(null);
    setSuccess(null);
  };


  return (
    <div className="container">
      <h1 id="recommendations" >Music Recommendations</h1>
        

      {currentUser?.presets && (
        <div className="form-container">
          <h2> Recommendations by preset </h2>
            <form className="recommendation-form" onSubmit={handleSubmitPreset}>
            {presetError && (
              <div className="error-message" style={{ color: 'red', marginBottom: '15px' }}>
                {presetError}
              </div>
            )}
              <div className="form-group">
                <label for="preset">Preset:</label>
                <select 
                  name="preset" 
                  id="preset" 
                  className="form-select"
                  onChange={handlePresetChange}
                  >
                    <option value=""
                    >-- Select a preset --</option>
                    {Object.entries(currentUser.presets).map(([presetName, presetData]) => (
                    <option 
                      value={presetName}
                      >{presetName}
                    </option>
                    ))};
                </select>
                <button type="submit" className="btn-submit" disabled={loading}>
                {loading ? 'Collecting Recommendations...' : 'Get Preset Recommendations'}
                </button>
              </div>
            </form>
        </div>
      )}
      <div className="form-container">
        <h2> Regular Recommendations </h2>
          <form className="recommendation-form" onSubmit={handleSubmit} onReset={handleReset}>
          {error && (
            <div className="error-message" style={{ color: 'red', marginBottom: '15px' }}>
              {error}
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

          {/* Single Genre Selection */}
          <div className="form-group">
            <label htmlFor="genres">Preferred Genre:</label>
            <select 
              name="genres" 
              id="genres" 
              className="form-select"
              value={formData.genres}
              onChange={handleChange}
              disabled={loading}
            >
              <option value="">-- Select a genre --</option>
              {loading && <option disabled>Loading genres...</option>}
              {!loading && genres.map((genre) => (
                <option key={genre} value={genre}>
                  {genre.charAt(0).toUpperCase() + genre.slice(1)}
                </option>
              ))}
            </select>
            <small className="form-help">Select one genre</small>
          </div>

          {/* Multiple Genre Selection */}
          <div className="form-group">
            <label htmlFor="multipleGenres">Multiple Genres (optional):</label>
            <select 
              name="multipleGenres" 
              id="multipleGenres" 
              className="form-select" 
              multiple 
              size="5"
              value={formData.multipleGenres}
              onChange={handleChange}
              disabled={loading}
            >
              {loading && <option disabled>Loading genres...</option>}
              {!loading && genres.map((genre) => (
                <option key={genre} value={genre}>
                  {genre.charAt(0).toUpperCase() + genre.slice(1)}
                </option>
              ))}
            </select>
            <small className="form-help">
              Hold Ctrl (Windows) or Cmd (Mac) to select multiple genres
            </small>
          </div>

          {/* Show selected multiple genres */}
          {formData.multipleGenres.length > 0 && (
            <div className="form-group">
              <label>Selected Genres:</label>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '5px' }}>
                {formData.multipleGenres.map((genre, index) => (
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
                    {genre}
                    <button
                      type="button"
                      onClick={() => {
                        setFormData(prev => ({
                          ...prev,
                          multipleGenres: prev.multipleGenres.filter(g => g !== genre)
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

export default Recommendations;


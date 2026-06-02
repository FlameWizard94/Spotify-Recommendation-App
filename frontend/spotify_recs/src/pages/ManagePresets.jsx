import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';

const ManagePresets = () => {
  const { user:currentUser, isAuthenticated, authFetch, accessToken, spotifyLogin, refreshUser, printUser } = useAuth();
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [genres, setGenres] = useState([]);

  const [success, setSuccess] = useState(null);
  
  const [formData, setFormData] = useState({
    namme: '',
    artists: '',
    genres: '',
    multipleGenres: [],
    num_tracks: 10,
    ranking: 'most popular'
  });

  useEffect(() => {
    if (currentUser) {
      printUser(currentUser);
      console.log('Current user presets:', currentUser.presets);
    }
  }, [currentUser]);

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

  const deletePreset = async (name) => {
    setLoading(true);
    setError(null);

    try{
      const url = `/api/presets/delete/?name=${encodeURIComponent(name)}`;
      const response = await authFetch(url, {
        method : 'DELETE',
        headers: {
          'Authorization': `Bearer ${accessToken}`
        }
      });
        const data = await response.json();
        await refreshUser();
        alert(`${data.message}`);
      }
      catch (error) {
        console.error('Error:', error);
        setError('Failed to load presets.');
      } finally {
        setLoading(false);
      };
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
    // Handle form submission
  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSuccess(null);

    if (!formData.name){
      setError(`No preset name submitted`)
      console.log(`No preset name submitted`)
      setLoading(false);
      return;
    }
    
    try {
      // Prepare data for backend
      let allGenres = [];
      if (formData.genres) {
        allGenres.push(formData.genres);
      }
      if (formData.multipleGenres && formData.multipleGenres.length > 0) {
        allGenres = [...allGenres, ...formData.multipleGenres];
      }
      
      // Remove duplicates
      allGenres = [...new Set(allGenres)];

      const preset = {
        name: formData.name,
        artists: formData.artists,
        genres: allGenres.join(','),
        num_tracks: formData.num_tracks,
        ranking: formData.ranking
      };
      
      const response = await authFetch('/api/presets/add/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${accessToken}`
        },
        body: JSON.stringify(preset)
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      console.log('Preset added:', data);
      
      await refreshUser();
      
      setSuccess(`${data.message}`);
      
      // Clear success message after 3 seconds
      setTimeout(() => setSuccess(null), 10000);
      
    } catch (error) {
      console.error('Error updating preset:', error);
      setError('Failed to update preset. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  // Handle form reset
  const handleReset = () => {
    setFormData({
      name: '',
      artists: '',
      genres: '',
      num_tracks: 10,
      ranking: 'most popular'
    });

    setError(null);
    setSuccess(null);
  };

  const hasPresets = currentUser?.presets && Object.keys(currentUser.presets).length > 0;


  return (
    <div className="container">
      <h2>Add a preset</h2>

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
          <label htmlFor="artist">Name:</label>
          <input 
            type="text" 
            name="name" 
            id="name" 
            className="form-input" 
            value={formData.name}
            onChange={handleChange}
            disabled={loading}
          />
        </div>
        
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
            {loading ? 'Updating...' : 'Add Preset'}
          </button>
          <button type="reset" className="btn-reset" disabled={loading}>
            Clear Form
          </button>
        </div>
      </form>

      <br></br>
      <h2> Your Current Presets</h2>

      {loading && <p>Loading...</p>}

      {!loading && !currentUser && <p>Loading user data...</p>}

      {!loading && currentUser && !hasPresets && (
        <p>No presets yet. Create your first preset above!</p>
      )}

      {!loading && hasPresets && (
        <div>
          {Object.entries(currentUser.presets).map(([presetName, presetData]) => (
            <div key={presetName} className="preset_card">
              <h2>{presetName}</h2>
              <p><strong>Artists:</strong> {presetData.artists || 'None'}</p>
              <p><strong>Genres:</strong> {presetData.genres || 'None'}</p>
              <p><strong>Number of Recommendations:</strong> {presetData.num_tracks || 10}</p>
              <p><strong>Ranking Type:</strong> {presetData.ranking || 'most popular'}</p>
              <p>
                <a 
                  onClick={() => deletePreset(presetName)}  
                  className="delete"
                >
                  Delete Preset
                </a>
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );

};
export default  ManagePresets;
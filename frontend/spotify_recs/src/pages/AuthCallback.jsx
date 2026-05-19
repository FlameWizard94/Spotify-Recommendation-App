// pages/AuthCallback.jsx
import React, { useEffect, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';

const AuthCallback = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const [error, setError] = useState(null);

  useEffect(() => {
    console.log('=== AuthCallback mounted ===');
    console.log('Full URL:', window.location.href);
    console.log('Search params:', location.search);
    
    const params = new URLSearchParams(location.search);
    const accessToken = params.get('access');
    const refreshToken = params.get('refresh');
    const nextUrl = params.get('next') || '/';
    const userDataParam = params.get('user');
    const errorParam = params.get('error');

    console.log('Parsed params:', {
      hasAccess: !!accessToken,
      accessTokenPreview: accessToken ? `${accessToken.substring(0, 20)}...` : null,
      hasRefresh: !!refreshToken,
      nextUrl,
      hasUser: !!userDataParam,
      errorParam
    });

    if (errorParam) {
      console.error('Error from server:', errorParam);
      setError(decodeURIComponent(errorParam));
      setTimeout(() => navigate('/'), 5000);
      return;
    }

    if (accessToken && refreshToken && userDataParam) {
      try {
        const userData = JSON.parse(decodeURIComponent(userDataParam));
        console.log('User data parsed:', userData);
        
        // Store everything
        localStorage.setItem('access_token', accessToken);
        localStorage.setItem('refresh_token', refreshToken);
        localStorage.setItem('user', JSON.stringify(userData));
        
        console.log('Tokens and user data saved to localStorage');
        console.log('Redirecting to:', nextUrl);
        
        // Use window.location for a full page redirect
        window.location.href = nextUrl;
      } catch (err) {
        console.error('Error parsing user data:', err);
        setError('Failed to process authentication data: ' + err.message);
        setTimeout(() => navigate('/'), 5000);
      }
    } else {
      console.error('Missing required parameters');
      console.log('accessToken:', accessToken);
      console.log('refreshToken:', refreshToken);
      console.log('userDataParam:', userDataParam);
      setError('Missing authentication data. Please try again.');
      setTimeout(() => navigate('/'), 5000);
    }
  }, [location, navigate]);

  if (error) {
    return (
      <div className="container" style={{ textAlign: 'center', marginTop: '50px' }}>
        <h2>Authentication Error</h2>
        <p style={{ color: 'red' }}>{error}</p>
        <p>Redirecting to home page in 5 seconds...</p>
      </div>
    );
  }

  return (
    <div className="container" style={{ textAlign: 'center', marginTop: '50px' }}>
      <h2>Completing Authentication...</h2>
      <div className="spinner"></div>
      <p>Please wait while we log you in.</p>
    </div>
  );
};

export default AuthCallback;
// components/ProtectedRoute.jsx
import React, { useEffect, useRef } from 'react';
import { useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, loading, spotifyLogin } = useAuth();
  const location = useLocation();
  const hasRedirected = useRef(false);

  console.log('ProtectedRoute - isAuthenticated:', isAuthenticated);
  console.log('ProtectedRoute - loading:', loading);
  console.log('ProtectedRoute - path:', location.pathname);

  useEffect(() => {
    if (!loading && !isAuthenticated && !hasRedirected.current) {
      // Don't redirect if we're already on the auth callback page
      if (location.pathname === '/auth/callback') {
        console.log('On auth callback page, skipping redirect');
        return;
      }
      
      console.log('Not authenticated, redirecting to Spotify login');
      hasRedirected.current = true;
      spotifyLogin(location.pathname);
    }
  }, [loading, isAuthenticated, spotifyLogin, location.pathname]);

  if (loading) {
    return <div style={{ textAlign: 'center', marginTop: '50px' }}>
      <div className="spinner"></div>
      <p>Checking authentication...</p>
    </div>;
  }

  if (!isAuthenticated) {
    return <div style={{ textAlign: 'center', marginTop: '50px' }}>
      <p>Redirecting to Spotify login...</p>
    </div>;
  }

  return children;
};

export default ProtectedRoute;
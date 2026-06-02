// contexts/AuthContext.jsx
import React, { createContext, useState, useContext, useEffect, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom' 

const AuthContext = createContext();

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

const isTokenExpired = (token) => {
  if (!token) return true;
  
  try {
    const parts = token.split('.');
    if (parts.length !== 3) return true;
    
    const payload = JSON.parse(atob(parts[1]));
    if (!payload.exp) return true;
    
    const currentTime = Math.floor(Date.now() / 1000);
    return payload.exp < currentTime;
  } catch (error) {
    return true;
  }
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [accessToken, setAccessToken] = useState(localStorage.getItem('access_token'));
  const [refreshToken, setRefreshToken] = useState(localStorage.getItem('refresh_token'));
  const [isLoggingIn, setIsLoggingIn] = useState(false);

  const isAuthenticated = useMemo(() => {
    return !!user && accessToken && !isTokenExpired(accessToken);
  }, [user, accessToken]);

  // Load user on initial load if token exists
  useEffect(() => {
    const loadUserFromStorage = async () => {
      const storedAccessToken = localStorage.getItem('access_token');
      const storedUser = localStorage.getItem('user');
      
      if (storedAccessToken && storedUser) {
        try {
          setAccessToken(storedAccessToken);
          setRefreshToken(localStorage.getItem('refresh_token'));
          setUser(JSON.parse(storedUser));
        } catch (error) {
          console.error('Error loading user from storage:', error);
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          localStorage.removeItem('user');
        }
      }
      setLoading(false);
    };
    
    loadUserFromStorage();
  }, []);

  const printUser = async (user) => {
    if (user){
      console.log(user.spotify_id);
      console.log(user.name);
      console.log(user.email);
    }
  }

  // Fetch current user from backend (optional - you might not need this if you store user data)
  const fetchCurrentUser = async () => {
    try {
      const response = await fetch('/api/current-user/', {
        headers: {
          'Authorization': `Bearer ${accessToken}`
        }
      });
      
      if (response.ok) {
        const userData = await response.json();
        setUser(userData);
        localStorage.setItem('user', JSON.stringify(userData));
      } else if (response.status === 401) {
        // Token expired, try to refresh
        const refreshed = await refreshAccessToken();
        if (!refreshed) {
          logout();
        }
      }
    } catch (error) {
      console.error('Error fetching user:', error);
    } finally {
      setLoading(false);
    }
  };

  const refreshUser = useCallback(async () => {
    if (!accessToken) return;
    
    try {
      const response = await fetch('/api/current-user/', {
        headers: {
          'Authorization': `Bearer ${accessToken}`,
        },
      });
      
      if (response.ok) {
        const userData = await response.json();
        setUser(userData);
        localStorage.setItem('user', JSON.stringify(userData));
      }
    } catch (error) {
      console.error('Error refreshing user:', error);
    }
  }, [accessToken]);

  const refreshAccessToken = async () => {
    const currentRefreshToken = localStorage.getItem('refresh_token');

    try {
      const response = await fetch('/api/token/refresh/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ refresh: currentRefreshToken })
      });
      
      if (response.ok) {
        const data = await response.json();
        setAccessToken(data.access);
        localStorage.setItem('access_token', data.access);
        return true;
      } else {
        logout();
        return false;
      }
    } catch (error) {
      console.error('Token refresh error:', error);
      logout();
      return false;
    }
  };

  const authFetch = async (url, options = {}) => {
    let currentToken = accessToken;
    
    const makeRequest = async (token) => {
        return fetch(url, {
            ...options,
            headers: {
                ...options.headers,
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json',
            },
        });
    };
    
    let response = await makeRequest(currentToken);
    
    // If unauthorized, try to refresh token once
    if (response.status === 401) {
        console.log('Token expired, refreshing...');
        const refreshed = await refreshAccessToken();
        
        if (refreshed) {
            currentToken = localStorage.getItem('access_token');
            response = await makeRequest(currentToken);
        } else {
            // Refresh failed, redirect to login
            console.log('Refresh failed, redirecting to login');
            spotifyLogin(window.location.pathname);
            // Throw error to prevent further processing
            throw new Error('Session expired');
        }
    }
    
    // If still unauthorized after refresh, handle it
    if (response.status === 401) {
        console.log('Still unauthorized after refresh');
        spotifyLogin(window.location.pathname);
        throw new Error('Authentication failed');
    }
    
    return response;
};

  const spotifyLogin = async (nextUrl = '/') => {
    if (isLoggingIn) {
      console.log('Login already in progress, skipping...');
      return;
    }

    console.log('spotifyLogin called with nextUrl:', nextUrl);
    setIsLoggingIn(true);
    
    try {
      const apiUrl = `http://127.0.0.1:8000/api/spotify-login/?next=${encodeURIComponent(nextUrl)}`;
      console.log('Fetching from URL:', apiUrl);
      
      const response = await fetch(apiUrl);
      console.log('Response status:', response.status);
      
      const data = await response.json();
      console.log('Response data:', data);
      
      if (data.auth_url) {
        console.log('Redirecting to Spotify:', data.auth_url);
        window.location.href = data.auth_url;
      } else {
        console.error('No auth_url in response:', data);
        setIsLoggingIn(false);
      }
    } catch (error) {
      console.error('Login error:', error);
      setIsLoggingIn(false);
    }
  };

  const logout = async () => {
    if (refreshToken) {
      try {
        await fetch('/api/logout/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${accessToken}`
          },
          body: JSON.stringify({ refresh: refreshToken })
        });
        setUser(null);
      } catch (error) {
        console.error('Logout error:', error);
      }
    }
    
    // Clear all auth data
    setUser(null);
    setAccessToken(null);
    setRefreshToken(null);
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
    
    // Redirect to home
    window.location.href = '/';
  };

  const value = {
    user,
    loading,
    isAuthenticated,
    spotifyLogin,
    logout,
    accessToken,
    setUser,  
    refreshUser,
    printUser,
    authFetch,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

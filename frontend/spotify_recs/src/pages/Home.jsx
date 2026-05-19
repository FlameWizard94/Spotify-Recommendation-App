import React, { useState, useEffect } from 'react';
import Navbar from '../components/Navbar';

const Home = () => {
  return (
    <div className="container">  {/* Use className, not class */}
      <div className="home-wrapper">  {/* className instead of class */}
        
        <h1 className="home-title">Music Discovery Hub</h1>
        <p className="home-subtitle">Discover new music for yourself, or join a room to build a shared playlist with your friends!</p>

        <div className="feature-card">
          <h3 className="feature-title">Community Explorer</h3>
          <p className="feature-text">Connect with other users on the app to share listening tastes and build your network.</p>
          <p style={{ marginBottom: 0 }}>  {/* Object syntax */}
            <a className="link" href="/search">→ Find Other Users</a>  {/* React Router link */}
          </p>
        </div>

        <div className="feature-card">
          <h3 className="feature-title">Your Soundtrack</h3>
          <p className="feature-text">Generate custom song recommendations based on your presets/preferences.</p>
          <p style={{ marginBottom: 0 }}>
            <a className="link" href="/recommendations">→ Get Individual Recommendations</a>
          </p>
        </div>

        <div className="feature-card">
          <h3 className="feature-title">Group Listening</h3>
          <p className="feature-text">Mix your music with others. Start a live room code session with your friends or combine your saved preferences with the people you follow.</p>
          <p style={{ marginBottom: 0 }}>
            <a className="link" href="/group-rec">→ Mix with Followers</a>
          </p>
          <p style={{ marginBottom: '10px' }}>  {/* String values need quotes */}
            <a className="link" href="/live-rooms">→ Host / Join Live Group Rooms</a>
          </p>
        </div>
        
      </div>
    </div>
  );
};

export default Home;
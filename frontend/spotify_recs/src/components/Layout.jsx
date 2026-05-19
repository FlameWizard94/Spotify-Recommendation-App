// src/components/Layout.jsx
import React from 'react';
import { Link, Outlet } from 'react-router-dom';
import './Layout.css'; 

const Layout = () => {
  return (
    <>
      {/* Top Navigation Bar - equivalent to div.top in base.html */}
      <div className="nav">
        <h1 className="nav_text">
          <Link to="/" className="nav_text">Home</Link>
        </h1>
        <h1 className="nav_text">
          <Link to="/profile" className="nav_text">Your Account</Link>
        </h1>
      </div>

      {/* Where child pages will render - equivalent to {% block content %} */}
      <main className="main-content">
        <Outlet /> {/* This is where page components render */}
      </main>
    </>
  );
};

export default Layout;
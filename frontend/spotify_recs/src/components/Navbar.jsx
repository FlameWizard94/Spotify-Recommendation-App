import React from 'react';

const Navbar = ({ user }) => {
  return (
    <div class='top'>
        <h1 class='top_text' ><a class='top_text' href="/">Home</a></h1>
        <h1 class='top_text'><a class='top_text' href="/profile"> Your Account </a></h1>
    </div>
  );
};

export default Navbar;
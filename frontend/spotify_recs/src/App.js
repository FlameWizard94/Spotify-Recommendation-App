import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import Home from './pages/Home';
import Search from './pages/Search';
import Profile from './pages/Profile';
import View_Profile from './pages/View_Profile';
import AuthCallback from './pages/AuthCallback';
import Layout from './components/Layout';
import ProtectedRoute from './components/ProtectedRoute';


function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route path="/" element={<Home />} />
          <Route path="/profile" element={<ProtectedRoute><Profile /></ProtectedRoute>} />
          <Route path="/view-profile/:spotifyId" element={<ProtectedRoute><View_Profile /></ProtectedRoute>} />
          <Route path="/auth/callback" element={<AuthCallback />} />
          <Route path="/search" element={<ProtectedRoute><Search /></ProtectedRoute>} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
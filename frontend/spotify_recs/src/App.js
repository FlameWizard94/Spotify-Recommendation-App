import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import Layout from './components/Layout';
import ProtectedRoute from './components/ProtectedRoute';
import Home from './pages/Home';
import AuthCallback from './pages/AuthCallback';
import Profile from './pages/Profile';
import ManageFollowing from './pages/ManageFollowing';
import ManagePresets from './pages/ManagePresets';
import Search from './pages/Search';
import View_Profile from './pages/View_Profile';
import Recommendations from './pages/Recommendations';
import GroupRecommendations from './pages/GroupRecommendations';
import ShowRecommendations from './pages/ShowRecommendations';





function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route path="/" element={<Home />} />
          <Route path="/auth/callback" element={<AuthCallback />} />
          <Route path="/profile" element={<ProtectedRoute><Profile /></ProtectedRoute>} />
          <Route path="/manage-following" element={<ProtectedRoute><ManageFollowing /></ProtectedRoute>} />
          <Route path="/profile/presets" element={<ProtectedRoute><ManagePresets /></ProtectedRoute>} />
          <Route path="/search" element={<ProtectedRoute><Search /></ProtectedRoute>} />
          <Route path="/view-profile/:spotifyId" element={<ProtectedRoute><View_Profile /></ProtectedRoute>} />
          <Route path="/recommendations" element={<ProtectedRoute><Recommendations /></ProtectedRoute>} />
          <Route path="/group-recommendations" element={<ProtectedRoute><GroupRecommendations /></ProtectedRoute>}> </Route>
          <Route path="/show-recommendations" element={<ProtectedRoute><ShowRecommendations /></ProtectedRoute>} />
          
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import AppLayout from './components/AppLayout';
import ProtectedRoute from './components/ProtectedRoute';
import LandingPage from './pages/LandingPage';
import PharmacyDashboard from './pages/PharmacyDashboard';
import DistributorDashboard from './pages/DistributorDashboard';
import ManufacturerDashboard from './pages/ManufacturerDashboard';
import FacilityDashboard from './pages/FacilityDashboard';
import RegulatorDashboard from './pages/RegulatorDashboard';
import RedistributionDashboard from './pages/RedistributionDashboard';
import { authAPI } from './services/api';

export default function App() {
  const [currentUser, setCurrentUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Attempt auto-login with default demo user (Pharmacy / MedPlus)
    initializeAuth();
  }, []);

  const initializeAuth = async () => {
    const token = localStorage.getItem('access_token');
    if (token) {
      try {
        const res = await authAPI.getMe();
        setCurrentUser(res.data);
      } catch (e) {
        // Token expired or invalid, auto login as pharmacy default
        await loginDefaultUser('PHARMACY');
      }
    } else {
      await loginDefaultUser('PHARMACY');
    }
    setLoading(false);
  };

  const loginDefaultUser = async (role) => {
    try {
      const res = await authAPI.switchRole(role);
      localStorage.setItem('access_token', res.data.access_token);
      setCurrentUser(res.data.user);
    } catch (e) {
      console.error('Failed to auto-login default role:', e);
    }
  };

  const handleRoleSwitch = async (role) => {
    try {
      const res = await authAPI.switchRole(role);
      localStorage.setItem('access_token', res.data.access_token);
      setCurrentUser(res.data.user);
    } catch (e) {
      console.error('Failed to switch role:', e);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    setCurrentUser(null);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="text-center space-y-3">
          <div className="w-10 h-10 border-4 border-blue-800 border-t-transparent rounded-full animate-spin mx-auto"></div>
          <p className="text-xs font-semibold text-slate-600">Initializing PharmMedian Platform...</p>
        </div>
      </div>
    );
  }

  return (
    <Router>
      <AppLayout currentUser={currentUser} onRoleSwitch={handleRoleSwitch} onLogout={handleLogout}>
        <Routes>
          <Route path="/" element={<LandingPage onSelectRole={handleRoleSwitch} />} />
          <Route
            path="/pharmacy"
            element={
              <ProtectedRoute currentUser={currentUser} allowedRoles={['PHARMACY']}>
                <PharmacyDashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/distributor"
            element={
              <ProtectedRoute currentUser={currentUser} allowedRoles={['DISTRIBUTOR']}>
                <DistributorDashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/manufacturer"
            element={
              <ProtectedRoute currentUser={currentUser} allowedRoles={['MANUFACTURER']}>
                <ManufacturerDashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/facility"
            element={
              <ProtectedRoute currentUser={currentUser} allowedRoles={['FACILITY']}>
                <FacilityDashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/regulator"
            element={
              <ProtectedRoute currentUser={currentUser} allowedRoles={['REGULATOR']}>
                <RegulatorDashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/redistribution"
            element={
              <ProtectedRoute currentUser={currentUser} allowedRoles={['PHARMACY', 'DISTRIBUTOR', 'MANUFACTURER', 'REGULATOR']}>
                <RedistributionDashboard />
              </ProtectedRoute>
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AppLayout>
    </Router>
  );
}

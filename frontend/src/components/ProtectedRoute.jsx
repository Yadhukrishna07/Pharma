import React from 'react';
import { Navigate } from 'react-router-dom';

export default function ProtectedRoute({ currentUser, allowedRoles, children }) {
  if (!currentUser) {
    return <Navigate to="/" replace />;
  }

  if (allowedRoles && !allowedRoles.includes(currentUser.role)) {
    return (
      <div className="max-w-4xl mx-auto my-12 p-8 bg-white border border-rose-200 rounded-xl shadow-sm text-center">
        <h2 className="text-xl font-bold text-rose-800 mb-2">Access Restricted</h2>
        <p className="text-sm text-slate-600 mb-4">
          Your current active role (<span className="font-bold">{currentUser.role}</span>) does not have access to this dashboard.
        </p>
        <p className="text-xs text-slate-500">
          Use the <strong>Switch Role</strong> menu in the navbar to change your active persona.
        </p>
      </div>
    );
  }

  return children;
}

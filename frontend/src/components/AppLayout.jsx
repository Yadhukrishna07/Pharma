import React from 'react';
import { useLocation } from 'react-router-dom';
import Navbar from './Navbar';

export default function AppLayout({ currentUser, onRoleSwitch, onLogout, children }) {
  const location = useLocation();
  const isLanding = location.pathname === '/';

  return (
    <div className="min-h-screen flex flex-col font-sans bg-slate-50 text-slate-800">
      <Navbar currentUser={currentUser} onRoleSwitch={onRoleSwitch} onLogout={onLogout} isLanding={isLanding} />
      <main className="flex-1 w-full mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-8">
        {children}
      </main>
      <footer className="py-6 text-center text-xs bg-white border-t border-slate-200 text-slate-500">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row justify-between items-center gap-2">
          <span>PharmMedian © 2026 — Closed-Loop Drug Return Platform</span>
          <span className="font-mono text-[11px] opacity-75">
            Cryptographic SHA-256 Audit Engine • Gemini Compliance AI
          </span>
        </div>
      </footer>
    </div>
  );
}

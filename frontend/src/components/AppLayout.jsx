import React from 'react';
import Navbar from './Navbar';

export default function AppLayout({ currentUser, onRoleSwitch, onLogout, children }) {
  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
      <Navbar currentUser={currentUser} onRoleSwitch={onRoleSwitch} onLogout={onLogout} />
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {children}
      </main>
      <footer className="bg-white border-t border-slate-200 py-6 text-center text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row justify-between items-center gap-2">
          <span>PharmMedian © 2026 — Closed-Loop Drug Return Platform</span>
          <span className="font-mono text-[11px] text-slate-400">
            Cryptographic SHA-256 Audit Engine • Gemini Compliance AI
          </span>
        </div>
      </footer>
    </div>
  );
}

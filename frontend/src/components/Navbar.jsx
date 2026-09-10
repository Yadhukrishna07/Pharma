import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Pill, Shield, Bell, ChevronDown, LogOut, Building2 } from 'lucide-react';
import { authAPI } from '../services/api';

const ROLES = [
  { id: 'PHARMACY', label: 'Pharmacy', path: '/pharmacy' },
  { id: 'DISTRIBUTOR', label: 'Distributor', path: '/distributor' },
  { id: 'MANUFACTURER', label: 'Manufacturer', path: '/manufacturer' },
  { id: 'FACILITY', label: 'Waste Facility', path: '/facility' },
  { id: 'REGULATOR', label: 'Regulator (CDSCO)', path: '/regulator' },
];

export default function Navbar({ currentUser, onRoleSwitch, onLogout }) {
  const [unreadCount, setUnreadCount] = useState(0);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    if (currentUser) {
      fetchNotificationsCount();
    }
  }, [currentUser]);

  const fetchNotificationsCount = async () => {
    try {
      const res = await authAPI.getNotificationsCount();
      setUnreadCount(res.data.count || 0);
    } catch (e) {
      // ignore
    }
  };

  const handleRoleSelect = async (roleId, path) => {
    setDropdownOpen(false);
    await onRoleSwitch(roleId);
    navigate(path);
  };

  return (
    <nav className="sticky top-0 z-50 bg-white border-b border-slate-200 text-slate-800 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          {/* Brand */}
          <div className="flex items-center gap-3">
            <Link to="/" className="flex items-center gap-2.5 group">
              <div className="w-9 h-9 rounded-lg flex items-center justify-center bg-blue-800 text-white shadow-sm">
                <Pill className="w-5 h-5" />
              </div>
              <div>
                <span className="font-black text-base tracking-tight flex items-center gap-2 text-slate-900">
                  PharmMedian
                  <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-blue-50 text-blue-800 border border-blue-200">
                    VERIFIED LOOP
                  </span>
                </span>
                <span className="text-[10px] block font-medium -mt-0.5 text-slate-500">
                  Closed-Loop Drug Return Platform
                </span>
              </div>
            </Link>
          </div>

          {/* User & Role Switcher */}
          {currentUser && (
            <div className="flex items-center gap-3 sm:gap-4">
              {/* Notification Badge */}
              <div className="relative">
                <button
                  className="p-2 rounded-lg transition-colors relative text-slate-500 hover:text-slate-700 hover:bg-slate-100"
                  title="Notifications"
                >
                  <Bell className="w-4 h-4" />
                  {unreadCount > 0 && (
                    <span className="absolute top-1.5 right-1.5 w-4 h-4 bg-rose-600 text-white rounded-full text-[10px] font-bold flex items-center justify-center">
                      {unreadCount}
                    </span>
                  )}
                </button>
              </div>

              {/* Active Role Indicator */}
              <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs bg-slate-50 border border-slate-200 text-slate-800">
                <Building2 className="w-3.5 h-3.5 text-blue-700" />
                <div>
                  <div className="font-bold">{currentUser.organization_name}</div>
                  <div className="text-[10px] text-slate-400 font-mono">{currentUser.role}</div>
                </div>
              </div>

              {/* Role Switcher Dropdown */}
              <div className="relative">
                <button
                  onClick={() => setDropdownOpen(!dropdownOpen)}
                  className="text-xs py-1.5 px-3 rounded-lg flex items-center gap-1.5 font-medium transition-colors bg-white hover:bg-slate-50 text-slate-700 border border-slate-200"
                >
                  <Shield className="w-3.5 h-3.5" />
                  <span>Switch Role</span>
                  <ChevronDown className="w-3.5 h-3.5 opacity-70" />
                </button>

                {dropdownOpen && (
                  <div className="absolute right-0 mt-2 w-56 rounded-xl shadow-xl py-1.5 z-50 border bg-white border-slate-200 text-slate-800">
                    <div className="px-3 py-1.5 text-[10px] font-mono font-bold text-slate-400 uppercase tracking-wider border-b border-slate-100">
                      Switch Role Context
                    </div>
                    {ROLES.map((r) => (
                      <button
                        key={r.id}
                        onClick={() => handleRoleSelect(r.id, r.path)}
                        className={`w-full text-left px-3 py-2 text-xs transition-colors flex items-center justify-between ${
                          currentUser.role === r.id ? 'font-bold text-blue-800 bg-blue-50/50' : 'hover:bg-slate-50 text-slate-700'
                        }`}
                      >
                        <span>{r.label}</span>
                        {currentUser.role === r.id && (
                          <span className="w-2 h-2 rounded-full bg-blue-600"></span>
                        )}
                      </button>
                    ))}
                    <div className="border-t mt-1 pt-1 border-slate-100">
                      <button
                        onClick={onLogout}
                        className="w-full text-left px-3 py-1.5 text-xs text-rose-500 hover:bg-rose-50 flex items-center gap-2 transition-colors"
                      >
                        <LogOut className="w-3.5 h-3.5" />
                        <span>Logout</span>
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </nav>
  );
}

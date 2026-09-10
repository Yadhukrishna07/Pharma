import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Building2, Truck, Factory, Flame, ShieldAlert, ArrowRight,
  Lock, CheckCircle2, RefreshCw, Cpu, Activity, Hash
} from 'lucide-react';

const ROLES = [
  {
    id: 'PHARMACY',
    stepNumber: '01',
    title: 'Pharmacy Operations',
    organization: 'MedPlus Central Indiranagar',
    icon: Building2,
    shortAction: 'Scan & Initiate Return',
    description: 'Scans expired batches & initiates reverse return handoff with cryptographically hashed metadata.',
    path: '/pharmacy',
    color: 'emerald',
    position: 'top-left',
  },
  {
    id: 'DISTRIBUTOR',
    stepNumber: '02',
    title: 'Pharma Logistics',
    organization: 'BlueDart Pharma Logistics',
    icon: Truck,
    shortAction: 'Verify & Transport',
    description: 'Confirms physical pickup, verifies unit counts, and logs transport handoff to prevent diversion.',
    path: '/distributor',
    color: 'blue',
    position: 'top-right',
  },
  {
    id: 'MANUFACTURER',
    stepNumber: '03',
    title: 'Manufacturer Portal',
    organization: 'Sun Pharma Laboratories',
    icon: Factory,
    shortAction: 'Acknowledge & Schedule',
    description: 'Receives reverse shipment, resolves quantity disputes, and authorizes scheduled destruction.',
    path: '/manufacturer',
    color: 'purple',
    position: 'bottom-right',
  },
  {
    id: 'FACILITY',
    stepNumber: '04',
    title: 'Biomedical Waste Facility',
    organization: 'BioClean Waste Facility',
    icon: Flame,
    shortAction: 'Destroy & Certify',
    description: 'Executes high-temperature destruction, logs destroyed weight, and issues verified certificate.',
    path: '/facility',
    color: 'rose',
    position: 'bottom-left',
  },
];

const REGULATOR_ROLE = {
  id: 'REGULATOR',
  title: 'CDSCO Regulator Oversight',
  organization: 'Central Drugs Standard Control Organization',
  icon: ShieldAlert,
  description: 'Audits full ledger integrity, monitors critical alerts, and verifies destruction certificates.',
  path: '/regulator',
};

export default function LandingPage({ onSelectRole }) {
  const navigate = useNavigate();
  const [activeHover, setActiveHover] = useState(null);
  const [tickerTime, setTickerTime] = useState(2);
  const [activeBatchIndex, setActiveBatchIndex] = useState(0);

  const sampleBatches = [
    { number: 'BATCH-001', med: 'Augmentin Duo 625mg', status: 'EXPIRED -> CLOSED' },
    { number: 'BATCH-004', med: 'Amoxicillin 500mg', status: 'RETURN_REQUESTED' },
    { number: 'BATCH-009', med: 'Metformin 850mg', status: 'DESTRUCTION_SCHEDULED' },
  ];

  // Ticking timestamp timer to feel alive
  useEffect(() => {
    const timer = setInterval(() => {
      setTickerTime((prev) => (prev <= 1 ? 5 : prev - 1));
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  // Cycle active batch preview
  useEffect(() => {
    const interval = setInterval(() => {
      setActiveBatchIndex((prev) => (prev + 1) % sampleBatches.length);
    }, 4000);
    return () => clearInterval(interval);
  }, []);

  const handleRoleClick = async (roleId, path) => {
    await onSelectRole(roleId);
    navigate(path);
  };

  const currentBatch = sampleBatches[activeBatchIndex];

  return (
    <div className="space-y-12 py-4">
      {/* Hero Header */}
      <div className="text-center space-y-4 max-w-3xl mx-auto">
        <div className="inline-flex items-center gap-2.5 px-3.5 py-1.5 rounded-full bg-blue-50 border border-blue-200 text-blue-700 text-xs font-mono font-bold tracking-wider">
          <span className="w-2 h-2 rounded-full bg-blue-500 animate-ping"></span>
          [ VERIFIED_LOOP :: SHA-256_AUDIT_ACTIVE ]
        </div>

        <div className="space-y-2">
          <h1 className="text-3xl sm:text-5xl font-black text-slate-900 tracking-tight font-sans">
            The Verified Loop
          </h1>
          <h2 className="text-lg sm:text-xl font-medium text-slate-500 max-w-xl mx-auto">
            Closed-Loop Chain of Custody & Regulatory Oversight
          </h2>
        </div>

        <p className="text-xs sm:text-sm text-slate-500 leading-relaxed font-sans max-w-2xl mx-auto">
          Every expired pharmaceutical batch flows through an authoritative 4-stage handoff loop.
          Overseen in real-time by CDSCO regulators with cryptographic audit chaining.
        </p>

        {/* Live Ticker Bar */}
        <div className="inline-flex flex-wrap items-center justify-center gap-4 sm:gap-6 bg-white border border-slate-200 px-4 sm:px-6 py-2.5 rounded-xl font-mono text-[11px] text-slate-600 shadow-sm">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
            <span className="text-slate-400">Chain:</span>
            <span className="font-bold text-emerald-600">100% Closed Loop</span>
          </div>
          <div className="flex items-center gap-2 border-l border-slate-200 pl-4 sm:pl-6">
            <Hash className="w-3.5 h-3.5 text-blue-600" />
            <span className="text-slate-400">Active Batch:</span>
            <span className="font-bold text-blue-700">{currentBatch.number}</span>
          </div>
          <div className="hidden sm:flex items-center gap-2 border-l border-slate-200 pl-6">
            <Activity className="w-3.5 h-3.5 text-purple-500" />
            <span className="text-slate-400">Last verified:</span>
            <span className="font-bold text-purple-600">{tickerTime}s ago</span>
          </div>
        </div>
      </div>

      {/* Main Loop Diagram (Desktop Layout) */}
      <div className="relative max-w-5xl mx-auto hidden lg:block my-8">
        {/* SVG Animated Loop Paths */}
        <svg
          className="absolute inset-0 w-full h-full pointer-events-none z-0"
          viewBox="0 0 1000 650"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <defs>
            <linearGradient id="blueGlow" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#3b82f6" stopOpacity="0.8" />
              <stop offset="100%" stopColor="#6366f1" stopOpacity="0.8" />
            </linearGradient>
            <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="3" result="blur" />
              <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>
          </defs>

          {/* Outer Ring Rectangle Path */}
          <path
            d="M 280 200 L 720 200 L 720 520 L 280 520 Z"
            stroke="#e2e8f0"
            strokeWidth="3"
            strokeDasharray="6 6"
            rx="30"
          />

          {/* Connected Loop Segment 1: Pharmacy -> Distributor */}
          <path
            d="M 330 200 L 670 200"
            stroke={activeHover === 'PHARMACY' || activeHover === 'DISTRIBUTOR' ? '#3b82f6' : '#cbd5e1'}
            strokeWidth={activeHover === 'PHARMACY' || activeHover === 'DISTRIBUTOR' ? '3.5' : '2'}
            filter={activeHover === 'PHARMACY' || activeHover === 'DISTRIBUTOR' ? 'url(#glow)' : 'none'}
            className="transition-all duration-300"
          />

          {/* Connected Loop Segment 2: Distributor -> Manufacturer */}
          <path
            d="M 720 250 L 720 470"
            stroke={activeHover === 'DISTRIBUTOR' || activeHover === 'MANUFACTURER' ? '#3b82f6' : '#cbd5e1'}
            strokeWidth={activeHover === 'DISTRIBUTOR' || activeHover === 'MANUFACTURER' ? '3.5' : '2'}
            filter={activeHover === 'DISTRIBUTOR' || activeHover === 'MANUFACTURER' ? 'url(#glow)' : 'none'}
            className="transition-all duration-300"
          />

          {/* Connected Loop Segment 3: Manufacturer -> Facility */}
          <path
            d="M 670 520 L 330 520"
            stroke={activeHover === 'MANUFACTURER' || activeHover === 'FACILITY' ? '#3b82f6' : '#cbd5e1'}
            strokeWidth={activeHover === 'MANUFACTURER' || activeHover === 'FACILITY' ? '3.5' : '2'}
            filter={activeHover === 'MANUFACTURER' || activeHover === 'FACILITY' ? 'url(#glow)' : 'none'}
            className="transition-all duration-300"
          />

          {/* Connected Loop Segment 4: Facility -> Pharmacy (Closed Loop) */}
          <path
            d="M 280 470 L 280 250"
            stroke={activeHover === 'FACILITY' || activeHover === 'PHARMACY' ? '#3b82f6' : '#cbd5e1'}
            strokeWidth={activeHover === 'FACILITY' || activeHover === 'PHARMACY' ? '3.5' : '2'}
            filter={activeHover === 'FACILITY' || activeHover === 'PHARMACY' ? 'url(#glow)' : 'none'}
            className="transition-all duration-300"
          />

          {/* Continuous Traveling Batch Pulse Dot */}
          <circle r="5" fill="#3b82f6" filter="url(#glow)">
            <animateMotion
              path="M 280 200 L 720 200 L 720 520 L 280 520 Z"
              dur="10s"
              repeatCount="indefinite"
            />
          </circle>

          {/* Lines from Regulator (Top Core) to all 4 nodes */}
          <path d="M 500 90 L 280 160" stroke="#3b82f6" strokeWidth="1" strokeDasharray="3 3" opacity="0.25" />
          <path d="M 500 90 L 720 160" stroke="#3b82f6" strokeWidth="1" strokeDasharray="3 3" opacity="0.25" />
          <path d="M 500 90 L 720 480" stroke="#3b82f6" strokeWidth="1" strokeDasharray="3 3" opacity="0.25" />
          <path d="M 500 90 L 280 480" stroke="#3b82f6" strokeWidth="1" strokeDasharray="3 3" opacity="0.25" />
        </svg>

        {/* Regulator Core Node (Top Center) */}
        <div className="flex justify-center mb-10 relative z-10">
          <div
            onClick={() => handleRoleClick(REGULATOR_ROLE.id, REGULATOR_ROLE.path)}
            onMouseEnter={() => setActiveHover('REGULATOR')}
            onMouseLeave={() => setActiveHover(null)}
            className="w-full max-w-md bg-white border border-emerald-200 rounded-2xl p-4 shadow-md hover:border-emerald-400 hover:shadow-lg transition-all cursor-pointer group"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-600 flex items-center justify-center font-bold">
                  <ShieldAlert className="w-5 h-5" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-extrabold text-slate-800 text-sm">{REGULATOR_ROLE.title}</span>
                    <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                  </div>
                  <div className="text-[11px] font-mono text-emerald-600">{REGULATOR_ROLE.organization}</div>
                </div>
              </div>
              <div className="text-[10px] font-mono bg-emerald-50 text-emerald-700 px-2.5 py-1 rounded border border-emerald-200 font-bold flex items-center gap-1.5">
                <Lock className="w-3 h-3" />
                <span>OVERSEER</span>
              </div>
            </div>
            <p className="text-xs text-slate-500 mt-2 font-sans">{REGULATOR_ROLE.description}</p>
          </div>
        </div>

        {/* 4 Circular Flow Nodes Grid */}
        <div className="grid grid-cols-2 gap-x-32 gap-y-24 relative z-10">
          {ROLES.map((r) => {
            const Icon = r.icon;
            const isHovered = activeHover === r.id;

            return (
              <div
                key={r.id}
                onClick={() => handleRoleClick(r.id, r.path)}
                onMouseEnter={() => setActiveHover(r.id)}
                onMouseLeave={() => setActiveHover(null)}
                className={`bg-white border rounded-2xl p-5 shadow-md transition-all cursor-pointer group relative ${
                  isHovered
                    ? 'border-blue-400 shadow-lg shadow-blue-100 scale-[1.03]'
                    : 'border-slate-200 hover:border-slate-300 hover:shadow-lg'
                }`}
              >
                {/* Node Step Badge */}
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <span className="w-6 h-6 rounded-lg bg-blue-50 border border-blue-200 text-blue-700 font-mono text-xs font-bold flex items-center justify-center">
                      {r.stepNumber}
                    </span>
                    <span className="text-[11px] font-mono font-bold text-slate-400 tracking-wider">
                      STEP {r.stepNumber}
                    </span>
                  </div>
                  <span className="text-[10px] font-mono text-blue-600 bg-blue-50 px-2 py-0.5 rounded border border-blue-200">
                    NODE: {r.id}
                  </span>
                </div>

                <div className="flex items-start gap-3.5">
                  <div className="w-11 h-11 rounded-xl bg-slate-50 border border-slate-200 text-blue-600 flex items-center justify-center flex-shrink-0 group-hover:border-blue-300 group-hover:bg-blue-50 transition-colors">
                    <Icon className="w-5 h-5" />
                  </div>
                  <div className="space-y-1">
                    <h3 className="text-base font-extrabold text-slate-800 group-hover:text-blue-700 transition-colors">
                      {r.title}
                    </h3>
                    <p className="text-xs font-mono text-blue-600 font-medium">{r.organization}</p>
                    <p className="text-xs text-slate-500 leading-relaxed font-sans pt-1">{r.description}</p>
                  </div>
                </div>

                <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs font-mono text-blue-600 group-hover:translate-x-1 transition-transform">
                  <span className="font-bold">{r.shortAction}</span>
                  <ArrowRight className="w-4 h-4" />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Mobile Vertical Flow (Shown on < lg screens) */}
      <div className="block lg:hidden space-y-6 max-w-md mx-auto">
        {/* Regulator Overseer Mobile Card */}
        <div
          onClick={() => handleRoleClick(REGULATOR_ROLE.id, REGULATOR_ROLE.path)}
          className="bg-white border border-emerald-200 rounded-2xl p-4 shadow-md cursor-pointer"
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-600 flex items-center justify-center">
                <ShieldAlert className="w-4 h-4" />
              </div>
              <div>
                <div className="font-extrabold text-slate-800 text-sm">{REGULATOR_ROLE.title}</div>
                <div className="text-[10px] font-mono text-emerald-600">{REGULATOR_ROLE.organization}</div>
              </div>
            </div>
            <span className="text-[10px] font-mono bg-emerald-50 text-emerald-700 px-2 py-0.5 rounded border border-emerald-200">
              OVERSEER
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-2">{REGULATOR_ROLE.description}</p>
        </div>

        {/* 4 Vertical Step Nodes */}
        <div className="relative pl-6 space-y-6 border-l-2 border-blue-200">
          {ROLES.map((r) => {
            const Icon = r.icon;
            return (
              <div
                key={r.id}
                onClick={() => handleRoleClick(r.id, r.path)}
                className="bg-white border border-slate-200 rounded-2xl p-4 shadow-md cursor-pointer relative hover:shadow-lg hover:border-blue-300 transition-all"
              >
                {/* Node circle on vertical line */}
                <div className="absolute -left-[31px] top-5 w-4 h-4 rounded-full bg-blue-50 border-2 border-blue-500 flex items-center justify-center">
                  <div className="w-1.5 h-1.5 rounded-full bg-blue-500"></div>
                </div>

                <div className="flex items-center justify-between mb-2">
                  <span className="text-[10px] font-mono text-blue-600 font-bold">STEP {r.stepNumber}</span>
                  <span className="text-[10px] font-mono text-slate-400">ROLE: {r.id}</span>
                </div>

                <div className="flex items-start gap-3">
                  <div className="w-9 h-9 rounded-lg bg-slate-50 border border-slate-200 text-blue-600 flex items-center justify-center flex-shrink-0">
                    <Icon className="w-4 h-4" />
                  </div>
                  <div>
                    <h3 className="text-sm font-extrabold text-slate-800">{r.title}</h3>
                    <p className="text-[11px] font-mono text-blue-600">{r.organization}</p>
                    <p className="text-xs text-slate-500 mt-1">{r.description}</p>
                  </div>
                </div>

                <div className="mt-3 pt-2 border-t border-slate-100 flex items-center justify-between text-xs font-mono text-blue-600">
                  <span>Enter Portal</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Bottom Features Strip */}
      <div className="bg-white border border-slate-200 rounded-2xl p-6 grid grid-cols-1 sm:grid-cols-3 gap-6 text-center max-w-4xl mx-auto shadow-sm">
        <div className="space-y-1.5">
          <div className="text-xs font-mono font-bold text-blue-700 uppercase tracking-wider flex items-center justify-center gap-1.5">
            <Lock className="w-3.5 h-3.5" /> SHA-256 HASH CHAIN
          </div>
          <p className="text-xs text-slate-500 font-sans">Sequential block-linked ledger with zero tamper tolerance.</p>
        </div>
        <div className="space-y-1.5 border-t sm:border-t-0 sm:border-l border-slate-200 pt-4 sm:pt-0">
          <div className="text-xs font-mono font-bold text-emerald-600 uppercase tracking-wider flex items-center justify-center gap-1.5">
            <CheckCircle2 className="w-3.5 h-3.5" /> STATE MACHINE
          </div>
          <p className="text-xs text-slate-500 font-sans">Strict linear transitions prevent supply chain leakage.</p>
        </div>
        <div className="space-y-1.5 border-t sm:border-t-0 sm:border-l border-slate-200 pt-4 sm:pt-0">
          <div className="text-xs font-mono font-bold text-purple-600 uppercase tracking-wider flex items-center justify-center gap-1.5">
            <Cpu className="w-3.5 h-3.5" /> GEMINI AI MODERATOR
          </div>
          <p className="text-xs text-slate-500 font-sans">Autonomous fraud & re-entry detection via Gemini AI.</p>
        </div>
      </div>
    </div>
  );
}

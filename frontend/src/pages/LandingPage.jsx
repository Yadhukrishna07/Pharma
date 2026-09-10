import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Building2, Truck, Factory, Flame, ShieldAlert, ArrowRight, ShieldCheck, Pill } from 'lucide-react';

const ROLES = [
  {
    id: 'PHARMACY',
    title: 'Pharmacy Operations',
    organization: 'MedPlus Central Indiranagar',
    icon: Building2,
    color: 'text-blue-700 bg-blue-50 border-blue-200',
    description: 'Scan expired medication batches, trigger return requests, and monitor re-entry fraud alerts.',
    path: '/pharmacy',
  },
  {
    id: 'DISTRIBUTOR',
    title: 'Pharma Logistics',
    organization: 'BlueDart Pharma Logistics',
    icon: Truck,
    color: 'text-indigo-700 bg-indigo-50 border-indigo-200',
    description: 'Confirm batch pickups, verify quantities received, and raise or inspect quantity disputes.',
    path: '/distributor',
  },
  {
    id: 'MANUFACTURER',
    title: 'Manufacturer Portal',
    organization: 'Sun Pharma Laboratories',
    icon: Factory,
    color: 'text-purple-700 bg-purple-50 border-purple-200',
    description: 'Confirm reverse handoffs from distributors and schedule destruction at authorized facilities.',
    path: '/manufacturer',
  },
  {
    id: 'FACILITY',
    title: 'Biomedical Waste Facility',
    organization: 'BioClean Waste Facility',
    icon: Flame,
    color: 'text-rose-700 bg-rose-50 border-rose-200',
    description: 'Record batch destruction, log destroyed quantities, and issue verified destruction certificates.',
    path: '/facility',
  },
  {
    id: 'REGULATOR',
    title: 'CDSCO Regulator Oversight',
    organization: 'CDSCO Regulator',
    icon: ShieldAlert,
    color: 'text-emerald-700 bg-emerald-50 border-emerald-200',
    description: 'Monitor overall network stats, verify cryptographic SHA-256 audit chains, and audit critical alerts.',
    path: '/regulator',
  },
];

export default function LandingPage({ onSelectRole }) {
  const navigate = useNavigate();

  const handleRoleClick = async (roleId, path) => {
    await onSelectRole(roleId);
    navigate(path);
  };

  return (
    <div className="max-w-6xl mx-auto space-y-10">
      {/* Hero Section */}
      <div className="text-center space-y-4 py-6">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-50 border border-blue-200 text-blue-800 text-xs font-bold">
          <ShieldCheck className="w-4 h-4 text-blue-700" />
          Enterprise Closed-Loop Compliance Platform
        </div>
        <h1 className="text-4xl sm:text-5xl font-extrabold text-slate-900 tracking-tight leading-tight">
          Cryptographic Drug Return &<br />
          <span className="text-blue-800">Verified Destruction Network</span>
        </h1>
        <p className="max-w-2xl mx-auto text-base text-slate-600 leading-relaxed">
          PharmMedian secures the reverse pharmaceutical supply chain with state-machine integrity,
          SHA-256 cryptographic audit chaining, and autonomous Gemini AI compliance moderation.
        </p>
      </div>

      {/* Role Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {ROLES.map((r) => {
          const Icon = r.icon;
          return (
            <div
              key={r.id}
              className="enterprise-card flex flex-col justify-between group hover:border-blue-300 hover:shadow-lg transition-all cursor-pointer"
              onClick={() => handleRoleClick(r.id, r.path)}
            >
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className={`w-12 h-12 rounded-xl border flex items-center justify-center ${r.color}`}>
                    <Icon className="w-6 h-6" />
                  </div>
                  <span className="text-[11px] font-mono text-slate-400 font-medium">Role: {r.id}</span>
                </div>

                <div>
                  <h3 className="text-lg font-bold text-slate-900 group-hover:text-blue-800 transition-colors">
                    {r.title}
                  </h3>
                  <p className="text-xs font-semibold text-blue-700 mt-0.5">{r.organization}</p>
                </div>

                <p className="text-xs text-slate-600 leading-relaxed">{r.description}</p>
              </div>

              <div className="mt-6 pt-4 border-t border-slate-100 flex items-center justify-between text-xs font-bold text-blue-800 group-hover:translate-x-1 transition-transform">
                <span>Enter Portal</span>
                <ArrowRight className="w-4 h-4" />
              </div>
            </div>
          );
        })}
      </div>

      {/* Technical Banner */}
      <div className="bg-slate-900 text-white rounded-2xl p-6 shadow-md border border-slate-800 grid grid-cols-1 md:grid-cols-3 gap-6 text-center">
        <div className="space-y-1">
          <div className="text-xl font-bold text-blue-400 font-mono">SHA-256</div>
          <div className="text-xs text-slate-300 font-medium">Tamper-Evident Hash Chain</div>
          <div className="text-[11px] text-slate-400">Sequential block verification</div>
        </div>
        <div className="space-y-1 border-t md:border-t-0 md:border-l border-slate-800 pt-4 md:pt-0">
          <div className="text-xl font-bold text-emerald-400 font-mono">100% Closed Loop</div>
          <div className="text-xs text-slate-300 font-medium">Authoritative State Transitions</div>
          <div className="text-[11px] text-slate-400">Prevents reverse supply leakage</div>
        </div>
        <div className="space-y-1 border-t md:border-t-0 md:border-l border-slate-800 pt-4 md:pt-0">
          <div className="text-xl font-bold text-purple-400 font-mono">Gemini AI Agent</div>
          <div className="text-xs text-slate-300 font-medium">Real-time Risk Moderation</div>
          <div className="text-[11px] text-slate-400">Autonomous fraud detection</div>
        </div>
      </div>
    </div>
  );
}

import React from 'react';
import { Building2, Truck, Factory, Flame, ShieldAlert, CheckCircle2, ArrowRight } from 'lucide-react';

const STAGES = [
  { id: 'PHARMACY', label: '1. Pharmacy', icon: Building2, color: 'border-blue-500 text-blue-700 bg-blue-50' },
  { id: 'DISTRIBUTOR', label: '2. Distributor', icon: Truck, color: 'border-indigo-500 text-indigo-700 bg-indigo-50' },
  { id: 'MANUFACTURER', label: '3. Manufacturer', icon: Factory, color: 'border-purple-500 text-purple-700 bg-purple-50' },
  { id: 'FACILITY', label: '4. Waste Facility', icon: Flame, color: 'border-rose-500 text-rose-700 bg-rose-50' },
  { id: 'REGULATOR', label: '5. Regulator', icon: ShieldAlert, color: 'border-emerald-500 text-emerald-700 bg-emerald-50' },
];

const STATUS_STAGE_MAP = {
  ACTIVE: 0,
  EXPIRED: 0,
  RETURN_REQUESTED: 1,
  PICKUP_CONFIRMED: 1,
  RECEIVED_BY_DISTRIBUTOR: 1,
  DISPUTED: 1,
  RECEIVED_BY_MANUFACTURER: 2,
  DESTRUCTION_SCHEDULED: 3,
  DESTROYED: 3,
  CERTIFICATE_VERIFIED: 4,
  CLOSED: 4,
};

export default function BatchJourneyMap({ currentStatus, batchNumber }) {
  const activeStageIdx = STATUS_STAGE_MAP[currentStatus] ?? 0;
  const isDisputed = currentStatus === 'DISPUTED';

  return (
    <div className="bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 text-white rounded-2xl p-6 shadow-xl border border-slate-700/80 mb-6">
      <div className="flex items-center justify-between flex-wrap gap-2 border-b border-slate-700/80 pb-3 mb-6">
        <div className="flex items-center gap-2">
          <div className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse"></div>
          <h3 className="font-extrabold text-sm text-slate-100 tracking-wide uppercase">
            Reverse Supply Chain Journey Map
          </h3>
        </div>
        {batchNumber && (
          <span className="font-mono text-xs text-blue-300 font-bold bg-blue-950/80 px-3 py-1 rounded-full border border-blue-700/60">
            {batchNumber} • Status: {currentStatus}
          </span>
        )}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-5 gap-4 relative">
        {STAGES.map((stage, idx) => {
          const Icon = stage.icon;
          const isPassed = idx < activeStageIdx;
          const isActive = idx === activeStageIdx;

          return (
            <div key={stage.id} className="flex flex-col items-center text-center relative group">
              {/* Connector line on desktop */}
              {idx < STAGES.length - 1 && (
                <div
                  className={`hidden sm:block absolute top-7 left-1/2 w-full h-1 z-0 transition-colors duration-300 ${
                    idx < activeStageIdx ? 'bg-emerald-500' : 'bg-slate-700'
                  }`}
                />
              )}

              {/* Node Icon Circle */}
              <div
                className={`w-14 h-14 rounded-2xl border-2 flex items-center justify-center relative z-10 transition-all duration-300 shadow-lg ${
                  isActive
                    ? isDisputed
                      ? 'bg-amber-500 border-amber-300 text-white ring-4 ring-amber-500/40 scale-110'
                      : 'bg-blue-600 border-white text-white ring-4 ring-blue-500/40 scale-110'
                    : isPassed
                    ? 'bg-emerald-950 border-emerald-500 text-emerald-400'
                    : 'bg-slate-800 border-slate-700 text-slate-500'
                }`}
              >
                {isPassed ? (
                  <CheckCircle2 className="w-7 h-7 text-emerald-400" />
                ) : (
                  <Icon className="w-6 h-6" />
                )}

                {isActive && (
                  <span className="absolute -top-1 -right-1 flex h-3.5 w-3.5">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-3.5 w-3.5 bg-blue-500"></span>
                  </span>
                )}
              </div>

              {/* Node Label */}
              <div className="mt-3 space-y-0.5">
                <span
                  className={`text-xs font-bold block ${
                    isActive
                      ? isDisputed
                        ? 'text-amber-400'
                        : 'text-blue-300 font-extrabold'
                      : isPassed
                      ? 'text-emerald-300'
                      : 'text-slate-500'
                  }`}
                >
                  {stage.label}
                </span>
                <span className="text-[10px] text-slate-400 block font-mono">
                  {isPassed ? 'Verified' : isActive ? (isDisputed ? 'DISPUTED' : 'In Progress') : 'Pending'}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

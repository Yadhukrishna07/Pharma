import React from 'react';
import { Check, AlertTriangle, ShieldCheck } from 'lucide-react';

const STEPS = [
  { id: 'EXPIRED', label: 'Expired' },
  { id: 'RETURN_REQUESTED', label: 'Return Req.' },
  { id: 'PICKUP_CONFIRMED', label: 'Pickup' },
  { id: 'RECEIVED_BY_DISTRIBUTOR', label: 'Distributor' },
  { id: 'RECEIVED_BY_MANUFACTURER', label: 'Manufacturer' },
  { id: 'DESTRUCTION_SCHEDULED', label: 'Scheduled' },
  { id: 'DESTROYED', label: 'Destroyed' },
  { id: 'CLOSED', label: 'Verified & Closed' },
];

const STATUS_ORDER = {
  ACTIVE: 0,
  EXPIRED: 1,
  RETURN_REQUESTED: 2,
  PICKUP_CONFIRMED: 3,
  RECEIVED_BY_DISTRIBUTOR: 4,
  DISPUTED: 4, // Disputed happens at distributor stage
  RECEIVED_BY_MANUFACTURER: 5,
  DESTRUCTION_SCHEDULED: 6,
  DESTROYED: 7,
  CERTIFICATE_VERIFIED: 8,
  CLOSED: 8,
};

export default function ProgressTracker({ currentStatus }) {
  const currentIndex = STATUS_ORDER[currentStatus] ?? 0;
  const isDisputed = currentStatus === 'DISPUTED';

  return (
    <div className="w-full py-4">
      {isDisputed && (
        <div className="mb-4 bg-amber-50 border border-amber-300 text-amber-800 px-4 py-2 rounded-lg flex items-center gap-2 text-sm font-medium">
          <AlertTriangle className="w-5 h-5 text-amber-600" />
          <span>Batch is currently in DISPUTED state — normal flow paused until resolution.</span>
        </div>
      )}
      <div className="flex items-center justify-between overflow-x-auto pb-2">
        {STEPS.map((step, idx) => {
          const stepIndex = idx + 1;
          const isCompleted = currentIndex > stepIndex;
          const isCurrent = currentIndex === stepIndex;
          const isPending = currentIndex < stepIndex;

          return (
            <div key={step.id} className="flex flex-col items-center min-w-[90px] relative">
              <div className="flex items-center w-full">
                {idx > 0 && (
                  <div
                    className={`h-0.5 flex-1 ${
                      isCompleted || isCurrent ? 'bg-blue-600' : 'bg-slate-200'
                    }`}
                  />
                )}
                <div
                  className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold transition-all ${
                    isCurrent
                      ? isDisputed
                        ? 'bg-amber-500 text-white ring-4 ring-amber-100'
                        : 'bg-blue-700 text-white ring-4 ring-blue-100'
                      : isCompleted
                      ? 'bg-blue-600 text-white'
                      : 'bg-slate-200 text-slate-500'
                  }`}
                >
                  {isCompleted ? (
                    <Check className="w-4 h-4" />
                  ) : isCurrent && isDisputed ? (
                    <AlertTriangle className="w-4 h-4" />
                  ) : (
                    idx + 1
                  )}
                </div>
                {idx < STEPS.length - 1 && (
                  <div
                    className={`h-0.5 flex-1 ${
                      isCompleted ? 'bg-blue-600' : 'bg-slate-200'
                    }`}
                  />
                )}
              </div>
              <span
                className={`text-[11px] font-medium mt-1 text-center whitespace-nowrap ${
                  isCurrent
                    ? 'text-blue-800 font-bold'
                    : isCompleted
                    ? 'text-slate-700'
                    : 'text-slate-400'
                }`}
              >
                {step.label}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

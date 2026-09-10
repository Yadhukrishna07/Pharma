import React from 'react';

const statusConfig = {
  ACTIVE: { label: 'Active', bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200' },
  EXPIRED: { label: 'Expired', bg: 'bg-slate-100', text: 'text-slate-700', border: 'border-slate-300' },
  RETURN_REQUESTED: { label: 'Return Requested', bg: 'bg-blue-50', text: 'text-blue-700', border: 'border-blue-200' },
  PICKUP_CONFIRMED: { label: 'Pickup Confirmed', bg: 'bg-indigo-50', text: 'text-indigo-700', border: 'border-indigo-200' },
  RECEIVED_BY_DISTRIBUTOR: { label: 'With Distributor', bg: 'bg-cyan-50', text: 'text-cyan-700', border: 'border-cyan-200' },
  DISPUTED: { label: 'Disputed', bg: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-300' },
  RECEIVED_BY_MANUFACTURER: { label: 'With Manufacturer', bg: 'bg-purple-50', text: 'text-purple-700', border: 'border-purple-200' },
  DESTRUCTION_SCHEDULED: { label: 'Destruction Scheduled', bg: 'bg-violet-50', text: 'text-violet-700', border: 'border-violet-200' },
  DESTROYED: { label: 'Destroyed', bg: 'bg-rose-50', text: 'text-rose-700', border: 'border-rose-200' },
  CERTIFICATE_VERIFIED: { label: 'Cert Verified', bg: 'bg-teal-50', text: 'text-teal-700', border: 'border-teal-200' },
  CLOSED: { label: 'Closed & Archived', bg: 'bg-emerald-100', text: 'text-emerald-800', border: 'border-emerald-300' },
};

export default function StatusBadge({ status }) {
  const config = statusConfig[status] || {
    label: status || 'Unknown',
    bg: 'bg-slate-50',
    text: 'text-slate-600',
    border: 'border-slate-200',
  };

  return (
    <span
      className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold border ${config.bg} ${config.text} ${config.border}`}
    >
      <span className="w-1.5 h-1.5 rounded-full bg-current mr-1.5"></span>
      {config.label}
    </span>
  );
}

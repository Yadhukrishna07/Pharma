import React from 'react';
import { Clock, ShieldAlert, CheckCircle, ArrowRight, AlertTriangle, Flame, Award, Building2 } from 'lucide-react';

const ROLE_COLORS = {
  PHARMACY: 'bg-blue-50 text-blue-800 border-blue-200',
  DISTRIBUTOR: 'bg-sky-50 text-sky-800 border-sky-200',
  MANUFACTURER: 'bg-purple-50 text-purple-800 border-purple-200',
  FACILITY: 'bg-amber-50 text-amber-900 border-amber-200',
  REGULATOR: 'bg-emerald-50 text-emerald-800 border-emerald-200',
  SYSTEM: 'bg-slate-100 text-slate-700 border-slate-200',
};

function getEventDescription(event) {
  const t = event.event_type;
  const d = event.data || {};

  if (t === 'BATCH_EXPIRED') return 'Expiry detected';
  if (t === 'RETURN_REQUESTED') return `Return request created • ${d.declared_quantity || 100} packs`;
  if (t === 'PICKUP_CONFIRMED') return 'Pickup confirmed';
  if (t === 'RECEIVED_BY_DISTRIBUTOR') return `${d.received_qty || 95} packs received`;
  if (t === 'DISCREPANCY_DETECTED') return `${d.received_qty || 95} packs received — HIGH RISK discrepancy`;
  if (t === 'DISPUTE_RESOLVED') return 'Dispute resolved — Forwarded to Manufacturer';
  if (t === 'MANUFACTURER_RECEIVED') return 'Receipt confirmed at Manufacturer';
  if (t === 'DESTRUCTION_SCHEDULED') return `Destruction scheduled at ${d.facility_name || 'BioClean Facility'}`;
  if (t === 'DESTRUCTION_RECORDED') return `Destruction completed • ${d.quantity_destroyed || 95} packs`;
  if (t === 'CERTIFICATE_VERIFIED') return 'Certificate verified • COMPLIANCE CLOSED';
  if (t === 'BATCH_CLOSED') return 'Compliance lifecycle CLOSED';
  if (t === 'REENTRY_FRAUD_SCAN') return 'BATCH-001 scanned — CRITICAL RE-ENTRY';
  if (t === 'SCAN') return 'Batch scanned';

  return t.replace(/_/g, ' ');
}

export default function RecentActivityFeed({ events = [], title = "Recent Activity" }) {
  if (!events || events.length === 0) {
    return (
      <div className="bg-white border border-slate-200 rounded-xl p-4 text-xs text-slate-400 italic">
        No recent activity logged.
      </div>
    );
  }

  return (
    <div className="enterprise-card bg-white border border-slate-200 p-5 rounded-2xl shadow-sm space-y-3">
      <div className="flex items-center justify-between border-b border-slate-100 pb-3">
        <div className="flex items-center gap-2">
          <Clock className="w-4 h-4 text-blue-800" />
          <h3 className="font-bold text-slate-900 text-sm">{title}</h3>
        </div>
        <span className="text-[10px] font-mono bg-blue-50 text-blue-700 px-2 py-0.5 rounded-full font-bold border border-blue-200">
          LIVE FROM POSTGRESQL
        </span>
      </div>

      <div className="space-y-2.5 max-h-[380px] overflow-y-auto pr-1">
        {events.map((evt) => {
          const isFraud = evt.event_type === 'REENTRY_FRAUD_SCAN';
          const isDiscrepancy = evt.event_type === 'DISCREPANCY_DETECTED';
          const roleClass = ROLE_COLORS[evt.actor_role] || ROLE_COLORS.SYSTEM;

          return (
            <div
              key={evt.id}
              className={`p-3 rounded-xl border transition-all text-xs flex items-start justify-between gap-3 ${
                isFraud
                  ? 'bg-rose-50 border-rose-300 text-rose-950 ring-1 ring-rose-200'
                  : isDiscrepancy
                  ? 'bg-amber-50 border-amber-200 text-amber-950'
                  : 'bg-slate-50 border-slate-200 text-slate-800 hover:bg-slate-100/70'
              }`}
            >
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className={`text-[10px] font-extrabold uppercase px-2 py-0.5 rounded-full border ${roleClass}`}>
                    {evt.actor_role || 'SYSTEM'}
                  </span>
                  <span className="font-mono text-[11px] text-slate-400">
                    {evt.time_display || 'N/A'}
                  </span>
                </div>

                <div className="font-bold text-slate-900 text-xs flex items-center gap-1.5 pt-0.5">
                  {isFraud && <ShieldAlert className="w-3.5 h-3.5 text-rose-600 shrink-0" />}
                  {isDiscrepancy && <AlertTriangle className="w-3.5 h-3.5 text-amber-600 shrink-0" />}
                  <span>{getEventDescription(evt)}</span>
                </div>

                <div className="text-[11px] text-slate-500 font-sans">
                  {evt.actor_name && <span>{evt.actor_name}</span>}
                  {evt.to_status && (
                    <span className="font-mono text-[10px] text-slate-400 ml-1.5">
                      [{evt.to_status}]
                    </span>
                  )}
                </div>
              </div>

              {evt.data?.declared_qty && evt.data?.received_qty && (
                <div className="text-right shrink-0 font-mono text-[10px] bg-white px-2 py-1 rounded border border-slate-200">
                  <span className="text-slate-400 block">QTY</span>
                  <span className="font-bold text-slate-800">{evt.data.received_qty}/{evt.data.declared_qty}</span>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

import React from 'react';
import { Clock, ShieldAlert, ArrowRight, User } from 'lucide-react';
import StatusBadge from './StatusBadge';

export default function TimelineEvent({ event, isLast }) {
  const formattedTime = event.created_at
    ? new Date(event.created_at).toLocaleString()
    : 'N/A';

  return (
    <div className="flex gap-4 relative">
      {!isLast && (
        <div className="absolute left-[19px] top-8 bottom-0 w-0.5 bg-slate-200" />
      )}
      <div className="w-10 h-10 rounded-full bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-700 shrink-0 z-10">
        <Clock className="w-5 h-5" />
      </div>
      <div className="bg-white border border-slate-200 rounded-xl p-4 flex-1 mb-4 shadow-sm">
        <div className="flex items-center justify-between flex-wrap gap-2 mb-2">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-slate-800 text-sm">{event.event_type}</span>
            {event.to_status && <StatusBadge status={event.to_status} />}
          </div>
          <span className="text-xs text-slate-400 font-mono">{formattedTime}</span>
        </div>

        {event.actor_name && (
          <div className="flex items-center gap-1.5 text-xs text-slate-600 mb-2">
            <User className="w-3.5 h-3.5 text-slate-400" />
            <span className="font-medium">{event.actor_name}</span>
            {event.actor_role && (
              <span className="bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded text-[10px] font-mono">
                {event.actor_role}
              </span>
            )}
          </div>
        )}

        {event.data && (
          <div className="bg-slate-50 border border-slate-100 rounded-lg p-2.5 text-xs font-mono text-slate-600 overflow-x-auto">
            {typeof event.data === 'string' ? event.data : JSON.stringify(event.data, null, 2)}
          </div>
        )}
      </div>
    </div>
  );
}

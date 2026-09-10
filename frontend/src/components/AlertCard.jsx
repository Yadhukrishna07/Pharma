import React from 'react';
import { AlertCircle, AlertTriangle, Info, ShieldAlert, CheckCircle2 } from 'lucide-react';

const severityStyles = {
  CRITICAL: {
    bg: 'bg-rose-50',
    border: 'border-rose-300',
    text: 'text-rose-900',
    icon: ShieldAlert,
    badgeBg: 'bg-rose-600 text-white',
  },
  HIGH: {
    bg: 'bg-amber-50',
    border: 'border-amber-300',
    text: 'text-amber-900',
    icon: AlertTriangle,
    badgeBg: 'bg-amber-500 text-white',
  },
  MEDIUM: {
    bg: 'bg-yellow-50',
    border: 'border-yellow-200',
    text: 'text-yellow-900',
    icon: AlertCircle,
    badgeBg: 'bg-yellow-500 text-white',
  },
  LOW: {
    bg: 'bg-blue-50',
    border: 'border-blue-200',
    text: 'text-blue-900',
    icon: Info,
    badgeBg: 'bg-blue-500 text-white',
  },
};

export default function AlertCard({ alert, onAcknowledge }) {
  const style = severityStyles[alert.severity] || severityStyles.LOW;
  const Icon = style.icon;

  return (
    <div className={`border rounded-xl p-4 mb-3 ${style.bg} ${style.border} shadow-sm transition-all`}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <div className="mt-0.5">
            <Icon className={`w-5 h-5 ${style.text}`} />
          </div>
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${style.badgeBg}`}>
                {alert.severity}
              </span>
              <h4 className={`font-bold text-sm ${style.text}`}>{alert.title}</h4>
            </div>
            <p className="text-xs text-slate-700 leading-relaxed mb-2">{alert.description}</p>
            {alert.created_at && (
              <span className="text-[10px] text-slate-400 font-mono">
                {new Date(alert.created_at).toLocaleString()}
              </span>
            )}
          </div>
        </div>

        <div>
          {alert.is_acknowledged ? (
            <span className="inline-flex items-center gap-1 text-xs text-emerald-700 font-medium bg-emerald-50 px-2.5 py-1 rounded-lg border border-emerald-200">
              <CheckCircle2 className="w-3.5 h-3.5" /> Acked
            </span>
          ) : (
            onAcknowledge && (
              <button
                onClick={() => onAcknowledge(alert.id)}
                className="btn-secondary text-xs py-1 px-2.5"
              >
                Acknowledge
              </button>
            )
          )}
        </div>
      </div>
    </div>
  );
}

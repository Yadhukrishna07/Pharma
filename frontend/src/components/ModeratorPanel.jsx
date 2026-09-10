import React from 'react';
import { Bot, ShieldAlert, CheckCircle, AlertTriangle, ArrowRight } from 'lucide-react';

const riskBadges = {
  CRITICAL: 'bg-rose-600 text-white',
  HIGH: 'bg-amber-500 text-white',
  MEDIUM: 'bg-yellow-500 text-white',
  LOW: 'bg-emerald-600 text-white',
};

export default function ModeratorPanel({ moderatorEvent }) {
  if (!moderatorEvent) return null;

  const riskClass = riskBadges[moderatorEvent.risk_level] || 'bg-blue-600 text-white';

  return (
    <div className="bg-gradient-to-br from-slate-900 to-slate-800 text-white rounded-xl p-5 shadow-lg border border-slate-700 mb-6">
      <div className="flex items-center justify-between mb-4 border-b border-slate-700/80 pb-3">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-blue-600/30 border border-blue-400/40 flex items-center justify-center text-blue-400">
            <Bot className="w-5 h-5" />
          </div>
          <div>
            <h3 className="font-bold text-sm text-slate-100">Gemini Compliance Moderator</h3>
            <p className="text-[11px] text-slate-400">Autonomous AI Risk & Verification Engine</p>
          </div>
        </div>
        <span className={`px-2.5 py-1 rounded-full text-xs font-bold uppercase tracking-wider ${riskClass}`}>
          {moderatorEvent.risk_level} RISK
        </span>
      </div>

      <div className="space-y-3.5 text-xs">
        {moderatorEvent.analysis && (
          <div>
            <span className="font-semibold text-slate-400 uppercase tracking-wider text-[10px]">Technical Analysis</span>
            <p className="text-slate-200 mt-1 leading-relaxed bg-slate-800/60 p-2.5 rounded-lg border border-slate-700/50">
              {moderatorEvent.analysis}
            </p>
          </div>
        )}

        {moderatorEvent.recommended_action && (
          <div>
            <span className="font-semibold text-slate-400 uppercase tracking-wider text-[10px]">Recommended Operational Action</span>
            <div className="flex items-start gap-2 mt-1 bg-blue-950/40 border border-blue-800/40 text-blue-200 p-2.5 rounded-lg">
              <ArrowRight className="w-4 h-4 text-blue-400 shrink-0 mt-0.5" />
              <p className="leading-relaxed">{moderatorEvent.recommended_action}</p>
            </div>
          </div>
        )}

        {moderatorEvent.message && (
          <div>
            <span className="font-semibold text-slate-400 uppercase tracking-wider text-[10px]">Stakeholder Briefing</span>
            <p className="text-slate-300 italic mt-0.5">{moderatorEvent.message}</p>
          </div>
        )}
      </div>
    </div>
  );
}

import React from 'react';
import { Bot, ShieldAlert, AlertTriangle, CheckCircle, ArrowRight } from 'lucide-react';

const RISK_BADGES = {
  CRITICAL: 'bg-rose-600 text-white',
  HIGH: 'bg-amber-500 text-white',
  MEDIUM: 'bg-yellow-500 text-white',
  LOW: 'bg-emerald-600 text-white',
};

export default function ModeratorInsightCard({ insight, defaultRole = 'COMPLIANCE' }) {
  if (!insight) {
    return (
      <div className="bg-gradient-to-r from-slate-900 to-slate-800 text-white rounded-2xl p-5 shadow-sm border border-slate-700">
        <div className="flex items-center justify-between border-b border-slate-700 pb-3 mb-3">
          <div className="flex items-center gap-2">
            <Bot className="w-4 h-4 text-blue-400" />
            <span className="text-xs font-mono font-bold uppercase tracking-wider text-blue-300">
              MODERATOR AI
            </span>
          </div>
          <span className="text-[10px] font-mono text-slate-400">STANDBY</span>
        </div>
        <p className="text-xs text-slate-300 italic">
          Awaiting lifecycle transition to execute automated risk and compliance analysis.
        </p>
      </div>
    );
  }

  const riskClass = RISK_BADGES[insight.risk_level] || 'bg-blue-600 text-white';

  return (
    <div className="bg-gradient-to-r from-slate-900 to-slate-800 text-white rounded-2xl p-5 shadow-md border border-slate-700 space-y-3">
      <div className="flex items-center justify-between border-b border-slate-700 pb-2.5">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-lg bg-blue-600/30 border border-blue-400/40 flex items-center justify-center text-blue-400">
            <Bot className="w-4 h-4" />
          </div>
          <span className="text-xs font-mono font-bold uppercase tracking-wider text-blue-300">
            MODERATOR AI
          </span>
        </div>
        <span className={`px-2 py-0.5 rounded-full text-[10px] font-extrabold uppercase tracking-wider ${riskClass}`}>
          {insight.risk_level} RISK
        </span>
      </div>

      <div>
        <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider block mb-1">
          Latest Insight:
        </span>
        <p className="text-xs font-semibold text-slate-100 bg-slate-800/80 p-3 rounded-xl border border-slate-700 leading-relaxed">
          "{insight.message || insight.analysis || 'Analysis recorded.'}"
        </p>
      </div>

      {insight.recommended_action && (
        <div className="flex items-start gap-2 text-xs bg-blue-950/50 p-2.5 rounded-xl border border-blue-900/50 text-blue-200">
          <ArrowRight className="w-3.5 h-3.5 text-blue-400 shrink-0 mt-0.5" />
          <div>
            <span className="font-semibold text-blue-300">Action: </span>
            <span>{insight.recommended_action}</span>
          </div>
        </div>
      )}
    </div>
  );
}

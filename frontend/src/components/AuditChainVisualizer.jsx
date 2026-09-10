import React, { useState } from 'react';
import { ShieldCheck, Lock, Play, CheckCircle2, AlertTriangle, Link2 } from 'lucide-react';

export default function AuditChainVisualizer({ auditLogs, onVerify, auditResult }) {
  const [isVerifying, setIsVerifying] = useState(false);
  const [activeStep, setActiveStep] = useState(null);

  const handleStartVerify = async () => {
    setIsVerifying(true);
    setActiveStep(0);

    // Animate verification step by step across blocks
    for (let i = 0; i < auditLogs.length; i++) {
      setActiveStep(i);
      await new Promise((r) => setTimeout(r, 250));
    }

    if (onVerify) {
      await onVerify();
    }

    setIsVerifying(false);
    setActiveStep(null);
  };

  const records = auditLogs || [];

  return (
    <div className="bg-slate-900 text-white rounded-2xl p-6 shadow-xl border border-slate-800 space-y-6">
      {/* Visualizer Header */}
      <div className="flex items-center justify-between flex-wrap gap-4 border-b border-slate-800 pb-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-emerald-950 border border-emerald-700/60 flex items-center justify-center text-emerald-400">
            <Lock className="w-5 h-5" />
          </div>
          <div>
            <h3 className="font-extrabold text-base text-slate-100 flex items-center gap-2">
              SHA-256 Tamper-Evident Chain Visualizer
              <span className="text-[10px] font-mono bg-emerald-900/60 text-emerald-300 px-2 py-0.5 rounded border border-emerald-700/50">
                LIVE CHAIN
              </span>
            </h3>
            <p className="text-xs text-slate-400">Sequential block linking via SHA-256 hashes</p>
          </div>
        </div>

        <button
          onClick={handleStartVerify}
          disabled={isVerifying || records.length === 0}
          className="btn-primary bg-emerald-700 hover:bg-emerald-800 text-xs font-bold py-2 px-4 flex items-center gap-2 shadow-lg shadow-emerald-950"
        >
          {isVerifying ? (
            <>
              <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
              <span>Verifying Block {activeStep + 1}...</span>
            </>
          ) : (
            <>
              <Play className="w-3.5 h-3.5 fill-current" />
              <span>Run Interactive Chain Verification</span>
            </>
          )}
        </button>
      </div>

      {/* Linked Hash Blocks Visual Row */}
      {records.length === 0 ? (
        <p className="text-xs text-slate-400 italic">No audit block records available to visualize.</p>
      ) : (
        <div className="relative overflow-x-auto pb-4 pt-2">
          {/* Animated Green Laser Line during verification */}
          {isVerifying && (
            <div className="absolute top-1/2 left-0 h-1 bg-gradient-to-r from-emerald-500 to-cyan-400 z-20 transition-all duration-300 shadow-[0_0_12px_#10b981]"
                 style={{ width: `${((activeStep + 1) / records.length) * 100}%` }}
            />
          )}

          <div className="flex items-center gap-4 min-w-max">
            {records.map((log, idx) => {
              const isCurrentVerifying = activeStep === idx;
              const isVerified = activeStep !== null && activeStep > idx;

              return (
                <React.Fragment key={log.id}>
                  {/* Block Card */}
                  <div
                    className={`w-64 rounded-xl p-4 border transition-all duration-200 relative ${
                      isCurrentVerifying
                        ? 'bg-emerald-950 border-emerald-400 ring-4 ring-emerald-500/30 scale-105 z-10'
                        : isVerified
                        ? 'bg-slate-800/90 border-emerald-500/60'
                        : 'bg-slate-800/60 border-slate-700'
                    }`}
                  >
                    <div className="flex items-center justify-between border-b border-slate-700/80 pb-2 mb-2">
                      <span className="text-[10px] font-mono text-emerald-400 font-bold">
                        BLOCK #{idx + 1}
                      </span>
                      {isVerified ? (
                        <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                      ) : (
                        <Lock className="w-3.5 h-3.5 text-slate-500" />
                      )}
                    </div>

                    <div className="space-y-1.5 text-[11px]">
                      <div>
                        <span className="text-slate-400 block text-[9px] font-mono uppercase">Action</span>
                        <span className="font-bold text-slate-200 font-mono truncate block">
                          {log.action}
                        </span>
                      </div>

                      <div>
                        <span className="text-slate-400 block text-[9px] font-mono uppercase">Previous Hash</span>
                        <span className="font-mono text-[9px] text-slate-400 block truncate">
                          {log.previous_hash.slice(0, 16)}...
                        </span>
                      </div>

                      <div>
                        <span className="text-slate-400 block text-[9px] font-mono uppercase">Current Hash</span>
                        <span className="font-mono text-[9px] text-emerald-300 font-semibold block truncate">
                          {log.current_hash.slice(0, 16)}...
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Chain Link Indicator */}
                  {idx < records.length - 1 && (
                    <div className="flex items-center justify-center text-slate-600">
                      <Link2 className="w-5 h-5 text-emerald-500/80" />
                    </div>
                  )}
                </React.Fragment>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

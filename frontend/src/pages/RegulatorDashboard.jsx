import React, { useState, useEffect } from 'react';
import { ShieldCheck, ShieldAlert, Activity, CheckCircle2, AlertTriangle, RefreshCw, Award, Lock, Check } from 'lucide-react';
import { dashboardAPI, certificateAPI, auditAPI } from '../services/api';
import StatusBadge from '../components/StatusBadge';
import TimelineEvent from '../components/TimelineEvent';
import ModeratorPanel from '../components/ModeratorPanel';

export default function RegulatorDashboard() {
  const [data, setData] = useState(null);
  const [auditResult, setAuditResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [actionMsg, setActionMsg] = useState(null);

  useEffect(() => {
    fetchDashboard();

    const interval = setInterval(() => {
      if (!document.hidden) {
        fetchDashboard(false);
      }
    }, 3500);

    return () => clearInterval(interval);
  }, []);

  const fetchDashboard = async (showLoading = false) => {
    if (showLoading) setLoading(true);
    try {
      const res = await dashboardAPI.getRegulatorDashboard();
      setData(res.data);
      if (res.data?.audit_verification && !auditResult) {
        setAuditResult(res.data.audit_verification);
      }
    } catch (e) {
      console.error('Error fetching regulator dashboard:', e);
    } finally {
      if (showLoading) setLoading(false);
    }
  };

  const handleVerifyAuditChain = async () => {
    setLoading(true);
    setAuditResult(null);
    try {
      const res = await auditAPI.verifyAudit();
      setAuditResult(res.data);
      setActionMsg({
        type: 'success',
        text: 'Cryptographic audit chain verified across all records in PostgreSQL!',
      });
    } catch (err) {
      setAuditResult({
        is_valid: false,
        message: err.response?.data?.detail || 'Audit chain verification failed.',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyCertificate = async (certId) => {
    setLoading(true);
    setActionMsg(null);
    try {
      await certificateAPI.verifyCertificate(certId);
      setActionMsg({
        type: 'success',
        text: 'Certificate verified! Batch lifecycle transitioned to CERTIFICATE_VERIFIED → CLOSED.',
      });
      fetchDashboard(false);
    } catch (err) {
      setActionMsg({ type: 'error', text: err.response?.data?.detail || 'Certificate verification failed.' });
    } finally {
      setLoading(false);
    }
  };

  const handleAcknowledgeAlert = async (alertId) => {
    try {
      await auditAPI.acknowledgeAlert(alertId);
      fetchDashboard(false);
    } catch (e) {
      console.error(e);
    }
  };

  const batch = data?.batch;
  const summary = data?.summary_cards || {
    active_returns: 0,
    pending_destruction: 0,
    verified_destruction: 0,
    critical_fraud_alerts: 0,
  };
  const timeline = data?.timeline || [];
  const alerts = data?.alerts || [];
  const certificates = data?.certificates || [];
  const moderatorInsight = data?.moderator_insight;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
              CDSCO Regulator Compliance Oversight
            </h1>
            <span className="inline-flex items-center gap-1 bg-emerald-50 text-emerald-700 text-[10px] font-bold px-2 py-0.5 rounded-full border border-emerald-200">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
              LIVE POLLING
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Logged in as <span className="font-bold text-slate-700">{data?.organization_name || 'Central Drugs Standard Control Organization (CDSCO)'}</span>
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleVerifyAuditChain}
            disabled={loading}
            className="btn-primary text-xs bg-emerald-700 hover:bg-emerald-800"
          >
            <ShieldCheck className="w-4 h-4" /> Verify Audit Chain
          </button>
          <button onClick={() => fetchDashboard(true)} className="btn-secondary text-xs">
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} /> Refresh
          </button>
        </div>
      </div>

      {/* Action Notification */}
      {actionMsg && (
        <div
          className={`p-4 rounded-xl border text-xs font-medium flex items-center gap-2 ${
            actionMsg.type === 'success'
              ? 'bg-emerald-50 border-emerald-200 text-emerald-900'
              : 'bg-rose-50 border-rose-200 text-rose-900'
          }`}
        >
          <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
          <span>{actionMsg.text}</span>
        </div>
      )}

      {/* Target Batch Overview Card */}
      {batch && (
        <div className="enterprise-card bg-white border border-slate-200 p-5 rounded-2xl shadow-sm space-y-3">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <div>
              <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider block">
                Regulatory Monitored Batch
              </span>
              <h2 className="text-lg font-bold text-slate-900">
                {batch.batch_number} — {batch.medicine_name}
              </h2>
            </div>
            <StatusBadge status={batch.current_status} />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs font-mono pt-2 border-t border-slate-100">
            <div>
              <span className="text-slate-400 block text-[10px] font-sans font-semibold">CURRENT STATUS</span>
              <span className="font-extrabold text-blue-900">{batch.current_status}</span>
            </div>
            <div>
              <span className="text-slate-400 block text-[10px] font-sans font-semibold">CURRENT LOCATION</span>
              <span className="font-bold text-slate-800">{batch.current_location}</span>
            </div>
            <div>
              <span className="text-slate-400 block text-[10px] font-sans font-semibold">CURRENT QUANTITY</span>
              <span className="font-bold text-slate-800">{batch.quantity} Packs</span>
            </div>
          </div>
        </div>
      )}

      {/* Small Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <div className="enterprise-card bg-white border border-slate-200 p-5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500">Active Returns</span>
            <div className="w-8 h-8 rounded-lg bg-blue-50 text-blue-700 flex items-center justify-center">
              <Activity className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-extrabold text-slate-900 mt-2 font-mono">
            {summary.active_returns}
          </div>
          <span className="text-[11px] text-slate-400">In reverse supply chain</span>
        </div>

        <div className="enterprise-card bg-white border border-slate-200 p-5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500">Pending Destruction</span>
            <div className="w-8 h-8 rounded-lg bg-violet-50 text-violet-700 flex items-center justify-center">
              <Activity className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-extrabold text-slate-900 mt-2 font-mono">
            {summary.pending_destruction}
          </div>
          <span className="text-[11px] text-slate-400">Scheduled at facilities</span>
        </div>

        <div className="enterprise-card bg-white border border-slate-200 p-5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500">Verified Destruction</span>
            <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-700 flex items-center justify-center">
              <CheckCircle2 className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-extrabold text-slate-900 mt-2 font-mono">
            {summary.verified_destruction}
          </div>
          <span className="text-[11px] text-slate-400">Closed & certified</span>
        </div>

        <div className="enterprise-card bg-white border border-slate-200 p-5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500">Critical Alerts</span>
            <div className="w-8 h-8 rounded-lg bg-rose-50 text-rose-700 flex items-center justify-center">
              <ShieldAlert className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-extrabold text-rose-700 mt-2 font-mono">
            {summary.critical_fraud_alerts}
          </div>
          <span className="text-[11px] text-rose-600 font-medium">Unacknowledged events</span>
        </div>
      </div>

      {/* Cryptographic SHA-256 Hash Verification Card */}
      {auditResult && (
        <div
          className={`p-5 rounded-2xl border ${
            auditResult.is_valid
              ? 'bg-emerald-50 border-emerald-300 text-emerald-950'
              : 'bg-rose-50 border-rose-300 text-rose-950'
          } shadow-sm space-y-2`}
        >
          <div className="flex items-center gap-2.5">
            {auditResult.is_valid ? (
              <ShieldCheck className="w-6 h-6 text-emerald-600" />
            ) : (
              <ShieldAlert className="w-6 h-6 text-rose-600" />
            )}
            <h3 className="font-extrabold text-base">
              {auditResult.is_valid
                ? 'SHA-256 Tamper-Evident Hash Chain: VERIFIED & INTACT'
                : 'CRYPTOGRAPHIC TAMPERING DETECTED'}
            </h3>
          </div>
          <p className="text-xs leading-relaxed">{auditResult.message}</p>
          {auditResult.total_records !== undefined && (
            <div className="text-[11px] font-mono text-slate-600 pt-1">
              Verified Records in PostgreSQL: {auditResult.verified_records} / {auditResult.total_records}
            </div>
          )}
        </div>
      )}

      {/* AI Assessment & Recommended Action */}
      {moderatorInsight && (
        <ModeratorPanel moderatorEvent={moderatorInsight} />
      )}

      {/* Pending Certificate Verification */}
      {certificates.length > 0 && (
        <div className="enterprise-card bg-white border border-slate-200 p-6 rounded-2xl space-y-4">
          <div className="flex items-center gap-2 border-b border-slate-100 pb-3">
            <Award className="w-5 h-5 text-blue-800" />
            <h3 className="font-bold text-slate-900 text-base">Destruction Certificate Verification</h3>
          </div>

          <div className="space-y-3">
            {certificates.map((c) => (
              <div
                key={c.id}
                className="bg-slate-50 border border-slate-200 p-4 rounded-xl flex items-center justify-between flex-wrap gap-4 text-xs font-mono"
              >
                <div>
                  <span className="font-bold text-sm text-slate-900">{c.certificate_number}</span>
                  <span className="text-slate-500 block text-xs font-sans mt-0.5">
                    Certified Quantity: <strong>{c.quantity} Packs</strong> • Issued Date: {c.issued_date}
                  </span>
                </div>

                {c.is_verified || batch?.current_status === 'CLOSED' ? (
                  <span className="inline-flex items-center gap-1 text-emerald-700 bg-emerald-50 px-3 py-1.5 rounded-lg border border-emerald-200 font-bold">
                    <Check className="w-4 h-4" /> Certificate Verified — Compliance CLOSED
                  </span>
                ) : (
                  <button
                    onClick={() => handleVerifyCertificate(c.id)}
                    disabled={loading}
                    className="btn-primary text-xs bg-teal-700 hover:bg-teal-800"
                  >
                    Verify & Close Batch Lifecycle
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Grid: Alerts & LIVE WORKFLOW TIMELINE */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Security & Re-entry Alerts Panel */}
        <div className="enterprise-card space-y-4 lg:col-span-1">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div className="flex items-center gap-2">
              <ShieldAlert className="w-5 h-5 text-rose-600" />
              <h3 className="font-bold text-slate-900 text-base">Security Alerts</h3>
            </div>
            <span className="text-xs font-mono text-slate-400">{alerts.length} Total</span>
          </div>

          {alerts.length === 0 ? (
            <p className="text-xs text-slate-400 italic">No security alerts recorded.</p>
          ) : (
            <div className="space-y-3 max-h-[520px] overflow-y-auto pr-1">
              {alerts.map((a) => {
                const isCritical = a.severity === 'CRITICAL';
                return (
                  <div
                    key={a.id}
                    className={`p-3.5 rounded-xl border text-xs space-y-1.5 ${
                      isCritical
                        ? 'bg-rose-50 border-rose-300 text-rose-950 ring-1 ring-rose-200'
                        : a.severity === 'HIGH'
                        ? 'bg-amber-50 border-amber-200 text-amber-950'
                        : 'bg-slate-50 border-slate-200 text-slate-900'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className={`font-extrabold uppercase tracking-wider text-[10px] px-2 py-0.5 rounded ${
                        isCritical ? 'bg-rose-600 text-white' : 'bg-amber-500 text-white'
                      }`}>
                        {a.severity}
                      </span>
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] text-slate-400 font-mono">{a.time_display}</span>
                        {!a.is_acknowledged && (
                          <button
                            onClick={() => handleAcknowledgeAlert(a.id)}
                            className="text-[10px] text-blue-700 font-bold hover:underline"
                          >
                            Mark Ack
                          </button>
                        )}
                      </div>
                    </div>
                    <div className="font-bold text-sm">{a.title}</div>
                    <p className="text-[11px] leading-relaxed text-slate-700">{a.description}</p>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* LIVE WORKFLOW TIMELINE FROM POSTGRESQL */}
        <div className="enterprise-card space-y-4 lg:col-span-2">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div className="flex items-center gap-2">
              <Lock className="w-5 h-5 text-blue-800" />
              <div>
                <h3 className="font-bold text-slate-900 text-base">
                  LIVE WORKFLOW TIMELINE ({batch?.batch_number || 'BATCH-001'})
                </h3>
                <p className="text-[11px] text-slate-500">Real-time sequence populated directly from PostgreSQL</p>
              </div>
            </div>
            <span className="text-xs font-mono text-slate-400">{timeline.length} Events</span>
          </div>

          {timeline.length === 0 ? (
            <p className="text-xs text-slate-400 italic">No timeline entries found in database.</p>
          ) : (
            <div className="space-y-2 pt-2 max-h-[600px] overflow-y-auto pr-2">
              {timeline.map((evt, idx) => (
                <TimelineEvent key={evt.id} event={evt} isLast={idx === timeline.length - 1} />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

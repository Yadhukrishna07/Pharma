import React, { useState, useEffect } from 'react';
import { Flame, FileCheck, CheckCircle, RefreshCw, Award } from 'lucide-react';
import { dashboardAPI, destructionAPI, certificateAPI } from '../services/api';
import StatusBadge from '../components/StatusBadge';
import ProgressTracker from '../components/ProgressTracker';
import RecentActivityFeed from '../components/RecentActivityFeed';
import ModeratorInsightCard from '../components/ModeratorInsightCard';
import EvidenceCapture from '../components/EvidenceCapture';

export default function FacilityDashboard() {
  const [data, setData] = useState(null);
  const [qtyDestroyedInput, setQtyDestroyedInput] = useState(95);
  const [certNumInput, setCertNumInput] = useState(`CERT-${Math.floor(100000 + Math.random() * 900000)}`);
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
      const res = await dashboardAPI.getFacilityDashboard();
      setData(res.data);
      if (res.data?.batch?.quantity_to_destroy) {
        setQtyDestroyedInput(res.data.batch.quantity_to_destroy);
      }
    } catch (e) {
      console.error('Error fetching facility dashboard:', e);
    } finally {
      if (showLoading) setLoading(false);
    }
  };

  const handleRecordDestruction = async (e) => {
    e.preventDefault();
    if (!data?.batch?.id) return;
    setLoading(true);
    setActionMsg(null);

    try {
      await destructionAPI.recordDestruction(data.batch.id, Number(qtyDestroyedInput));
      setActionMsg({
        type: 'success',
        text: `Incineration destruction recorded successfully! ${qtyDestroyedInput} packs destroyed. Status updated to DESTROYED.`,
      });
      fetchDashboard(false);
    } catch (err) {
      setActionMsg({ type: 'error', text: err.response?.data?.detail || 'Failed to record destruction.' });
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateCertificate = async (e) => {
    e.preventDefault();
    if (!data?.batch?.id) return;
    setLoading(true);
    setActionMsg(null);

    try {
      const res = await certificateAPI.createCertificate(
        certNumInput,
        data.batch.id,
        Number(qtyDestroyedInput)
      );
      setActionMsg({
        type: 'success',
        text: `Destruction Certificate issued! Cert #${res.data.certificate_number}. Ready for CDSCO Regulator verification.`,
      });
      fetchDashboard(false);
    } catch (err) {
      setActionMsg({ type: 'error', text: err.response?.data?.detail || 'Failed to generate certificate.' });
    } finally {
      setLoading(false);
    }
  };

  const batch = data?.batch;
  const currentStatus = batch?.current_status || 'NOT_INITIATED';
  const certificate = data?.certificate;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
              Biomedical Waste Facility Portal
            </h1>
            <span className="inline-flex items-center gap-1 bg-emerald-50 text-emerald-700 text-[10px] font-bold px-2 py-0.5 rounded-full border border-emerald-200">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
              LIVE POLLING
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Logged in as <span className="font-bold text-slate-700">{data?.organization_name || 'BioClean Biomedical Waste Facility'}</span>
          </p>
        </div>
        <button onClick={() => fetchDashboard(true)} className="btn-secondary text-xs self-start sm:self-auto">
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} /> Refresh Data
        </button>
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
          <CheckCircle className="w-4 h-4 text-emerald-600 shrink-0" />
          <span>{actionMsg.text}</span>
        </div>
      )}

      {/* Active Batch Overview */}
      {batch && (
        <div className="enterprise-card bg-white border border-slate-200 p-6 rounded-2xl shadow-sm space-y-4">
          <div className="flex items-center justify-between flex-wrap gap-4 border-b border-slate-100 pb-4">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-xl bg-rose-50 border border-rose-200 flex items-center justify-center text-rose-700">
                <Flame className="w-6 h-6" />
              </div>
              <div>
                <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider block">
                  Designated Incineration Batch
                </span>
                <h2 className="text-xl font-extrabold text-slate-900">
                  {batch.batch_number} — {batch.medicine_name}
                </h2>
              </div>
            </div>
            <StatusBadge status={batch.current_status} />
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs font-mono">
            <div>
              <span className="text-slate-400 block text-[10px] font-sans font-semibold">QUANTITY TO DESTROY</span>
              <span className="font-extrabold text-rose-700 text-sm">{batch.quantity_to_destroy} Packs</span>
            </div>
            <div>
              <span className="text-slate-400 block text-[10px] font-sans font-semibold">SCHEDULED STATUS</span>
              <span className={`font-bold text-sm ${batch.scheduled_status === 'SCHEDULED' ? 'text-purple-700' : 'text-slate-500'}`}>
                {batch.scheduled_status} ({batch.scheduled_date})
              </span>
            </div>
            <div>
              <span className="text-slate-400 block text-[10px] font-sans font-semibold">DESTRUCTION STATUS</span>
              <span className={`font-bold text-sm ${batch.destruction_status === 'DESTROYED' ? 'text-rose-600' : 'text-slate-500'}`}>
                {batch.destruction_status}
              </span>
            </div>
            <div>
              <span className="text-slate-400 block text-[10px] font-sans font-semibold">CERTIFICATE STATUS</span>
              <span className={`font-bold text-xs ${data.certificate_status.includes('VERIFIED') ? 'text-emerald-700' : data.certificate_status.includes('ISSUED') ? 'text-blue-700' : 'text-slate-500'}`}>
                {data.certificate_status === 'CERTIFICATE_VERIFIED_CLOSED'
                  ? 'CERTIFICATE VERIFIED / CLOSED'
                  : data.certificate_status === 'ISSUED_AWAITING_VERIFICATION'
                  ? 'ISSUED (AWAITING REGULATOR)'
                  : 'PENDING ISSUANCE'}
              </span>
            </div>
          </div>

          {/* Derived Next Action Banner */}
          <div className="bg-rose-50 border border-rose-200 rounded-xl p-3 text-xs flex items-center gap-2.5">
            <span className="bg-rose-700 text-white text-[10px] font-extrabold px-2 py-0.5 rounded uppercase tracking-wider shrink-0">
              NEXT ACTION
            </span>
            <span className="text-rose-900 font-medium">{data.next_action}</span>
          </div>

          <ProgressTracker currentStatus={batch.current_status} />
        </div>
      )}

      {/* Grid: Record Destruction & Generate Certificate */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Record Destruction Form */}
        <div className="enterprise-card space-y-4">
          <div className="flex items-center gap-2 border-b border-slate-100 pb-3">
            <Flame className="w-5 h-5 text-rose-600" />
            <h3 className="font-bold text-slate-900 text-base">Record Incineration Destruction</h3>
          </div>

          <form onSubmit={handleRecordDestruction} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Target Batch</label>
              <input
                type="text"
                disabled
                className="input-field bg-slate-100 text-xs font-mono"
                value={`${batch?.batch_number || 'BATCH-001'} (${currentStatus})`}
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Quantity Destroyed (Packs)
              </label>
              <input
                type="number"
                className="input-field font-mono text-sm"
                value={qtyDestroyedInput}
                onChange={(e) => setQtyDestroyedInput(e.target.value)}
                disabled={currentStatus !== 'DESTRUCTION_SCHEDULED'}
              />
              <p className="text-[11px] text-slate-400 mt-1">
                Quantity automatically synchronized with verified intake count (95 packs).
              </p>
            </div>

            <button
              type="submit"
              disabled={
                loading ||
                currentStatus !== 'DESTRUCTION_SCHEDULED'
              }
              className="btn-danger w-full text-xs"
            >
              {loading
                ? 'Recording...'
                : currentStatus === 'DESTRUCTION_SCHEDULED'
                ? 'Record High-Temp Incineration Destruction'
                : batch?.destruction_status === 'DESTROYED'
                ? 'Destruction Recorded (DESTROYED)'
                : 'Awaiting Destruction Scheduling from Manufacturer'}
            </button>
          </form>
        </div>

        {/* Certificate Generation Card */}
        <div className="enterprise-card space-y-4">
          <div className="flex items-center gap-2 border-b border-slate-100 pb-3">
            <Award className="w-5 h-5 text-blue-800" />
            <h3 className="font-bold text-slate-900 text-base">Generate Destruction Certificate</h3>
          </div>

          <form onSubmit={handleGenerateCertificate} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Certificate ID Number</label>
              <input
                type="text"
                className="input-field font-mono uppercase text-xs"
                value={certNumInput}
                onChange={(e) => setCertNumInput(e.target.value)}
                disabled={currentStatus !== 'DESTROYED' || certificate !== null}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Issued Date</label>
                <input
                  type="text"
                  disabled
                  className="input-field bg-slate-100 text-xs font-mono"
                  value={certificate?.issued_date || new Date().toISOString().split('T')[0]}
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Certified Quantity</label>
                <input
                  type="text"
                  disabled
                  className="input-field bg-slate-100 text-xs font-mono"
                  value={`${certificate?.quantity || qtyDestroyedInput} Packs`}
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading || currentStatus !== 'DESTROYED' || certificate !== null}
              className="btn-primary w-full text-xs"
            >
              {loading
                ? 'Generating...'
                : certificate
                ? `Certificate Issued: #${certificate.certificate_number}`
                : currentStatus === 'DESTROYED'
                ? 'Generate & Issue Destruction Certificate'
                : 'Batch Must Be DESTROYED First'}
            </button>
          </form>

          {/* Certificate Details Card */}
          {certificate && (
            <div className="mt-4 border-t border-slate-100 pt-3 space-y-2 font-mono text-xs">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                Certificate Details
              </span>
              <div className="bg-slate-50 border border-slate-200 p-3 rounded-xl flex items-center justify-between">
                <div>
                  <span className="font-bold text-slate-900">{certificate.certificate_number}</span>
                  <span className="text-slate-500 block text-[11px] font-sans">
                    Certified {certificate.quantity} packs • Issued: {certificate.issued_date}
                  </span>
                </div>
                <span className={`px-2 py-1 rounded text-[10px] font-bold ${
                  certificate.is_verified || currentStatus === 'CLOSED'
                    ? 'bg-emerald-100 text-emerald-800'
                    : 'bg-amber-100 text-amber-800'
                }`}>
                  {certificate.is_verified || currentStatus === 'CLOSED'
                    ? 'CERTIFICATE VERIFIED / CLOSED'
                    : 'Awaiting CDSCO Regulator'}
                </span>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Waste Facility Photo Evidence Capture & AI Moderator Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <EvidenceCapture
          role="Waste Facility"
          batchNumber={batch?.batch_number || 'BATCH-001'}
          certificateId={certificate?.certificate_number || certNumInput}
          productName={batch?.medicine_name || 'Augmentin Duo 625mg'}
          stageName="Incineration Chamber Feed"
          organizationName={data?.organization_name || 'BioClean Biomedical Waste Facility'}
          title="Photo Evidence"
          description="Capture real photographic evidence of waste intake, high-temperature incineration chamber feed, destruction residue, or certificate issuance."
        />
        <ModeratorInsightCard insight={data?.moderator_insight} />
      </div>

      {/* Grid: Live Recent Activity Feed */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <RecentActivityFeed events={data?.recent_activity} title="Recent Activity (BATCH-001)" />
      </div>
    </div>
  );
}

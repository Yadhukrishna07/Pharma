import React, { useState, useEffect } from 'react';
import { Flame, FileCheck, CheckCircle, RefreshCw, Award } from 'lucide-react';
import { destructionAPI, certificateAPI, batchAPI } from '../services/api';
import StatusBadge from '../components/StatusBadge';
import ProgressTracker from '../components/ProgressTracker';

export default function FacilityDashboard() {
  const [batches, setBatches] = useState([]);
  const [certificates, setCertificates] = useState([]);
  const [qtyDestroyedInput, setQtyDestroyedInput] = useState(95); // 95 per spec
  const [certNumInput, setCertNumInput] = useState(`CERT-${Math.floor(100000 + Math.random() * 900000)}`);
  const [loading, setLoading] = useState(false);
  const [actionMsg, setActionMsg] = useState(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [batchesRes, certsRes] = await Promise.all([
        batchAPI.getBatches(),
        certificateAPI.getCertificates(),
      ]);
      setBatches(batchesRes.data);
      setCertificates(certsRes.data);
    } catch (e) {
      console.error(e);
    }
  };

  const primaryBatch = batches.find((b) => b.batch_number === 'BATCH-001') || batches[0];

  const handleRecordDestruction = async (e) => {
    e.preventDefault();
    if (!primaryBatch) return;
    setLoading(true);
    setActionMsg(null);

    try {
      await destructionAPI.recordDestruction(primaryBatch.id, Number(qtyDestroyedInput));
      setActionMsg({
        type: 'success',
        text: `Destruction recorded successfully! ${qtyDestroyedInput} packs destroyed. Batch status updated to DESTROYED.`,
      });
      loadData();
    } catch (err) {
      setActionMsg({ type: 'error', text: err.response?.data?.detail || 'Failed to record destruction.' });
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateCertificate = async (e) => {
    e.preventDefault();
    if (!primaryBatch) return;
    setLoading(true);
    setActionMsg(null);

    try {
      const res = await certificateAPI.createCertificate(
        certNumInput,
        primaryBatch.id,
        Number(qtyDestroyedInput)
      );
      setActionMsg({
        type: 'success',
        text: `Destruction Certificate generated! Cert #${res.data.certificate_number}. Ready for CDSCO Regulator verification.`,
      });
      loadData();
    } catch (err) {
      setActionMsg({ type: 'error', text: err.response?.data?.detail || 'Failed to generate certificate.' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
            Biomedical Waste Facility Portal
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Logged in as <span className="font-bold text-slate-700">BioClean Biomedical Waste Facility</span>
          </p>
        </div>
        <button onClick={loadData} className="btn-secondary text-xs self-start sm:self-auto">
          <RefreshCw className="w-3.5 h-3.5" /> Refresh Data
        </button>
      </div>

      {/* Notification */}
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
      {primaryBatch && (
        <div className="enterprise-card bg-white border border-slate-200 p-6 rounded-2xl shadow-sm space-y-4">
          <div className="flex items-center justify-between flex-wrap gap-4 border-b border-slate-100 pb-4">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-xl bg-rose-50 border border-rose-200 flex items-center justify-center text-rose-700">
                <Flame className="w-6 h-6" />
              </div>
              <div>
                <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider block">Target Batch</span>
                <h2 className="text-xl font-extrabold text-slate-900">
                  {primaryBatch.batch_number} — {primaryBatch.medicine_name || 'Augmentin Duo 625mg'}
                </h2>
              </div>
            </div>
            <StatusBadge status={primaryBatch.current_status} />
          </div>

          <ProgressTracker currentStatus={primaryBatch.current_status} />
        </div>
      )}

      {/* Grid: Destruction Record Form & Certificate Upload */}
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
                value={`${primaryBatch?.batch_number || 'BATCH-001'} (${primaryBatch?.current_status || ''})`}
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
              />
              <p className="text-[11px] text-slate-400 mt-1">
                Default set to <strong>95</strong> (matching received resolved quantity).
              </p>
            </div>

            <button
              type="submit"
              disabled={
                loading ||
                ['DESTROYED', 'CERTIFICATE_VERIFIED', 'CLOSED'].includes(primaryBatch?.current_status)
              }
              className="btn-danger w-full text-xs"
            >
              {loading ? 'Recording...' : 'Record High-Temp Incineration Destruction'}
            </button>
          </form>
        </div>

        {/* Certificate Generation & Upload */}
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
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Issued Date</label>
                <input
                  type="text"
                  disabled
                  className="input-field bg-slate-100 text-xs font-mono"
                  value={new Date().toISOString().split('T')[0]}
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Certified Quantity</label>
                <input
                  type="text"
                  disabled
                  className="input-field bg-slate-100 text-xs font-mono"
                  value={`${qtyDestroyedInput} Packs`}
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading || primaryBatch?.current_status !== 'DESTROYED'}
              className="btn-primary w-full text-xs"
            >
              {loading ? 'Generating...' : 'Generate & Issue Destruction Certificate'}
            </button>
          </form>

          {/* Certificate Log */}
          {certificates.length > 0 && (
            <div className="mt-4 border-t border-slate-100 pt-3">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-2">
                Issued Certificates
              </span>
              <div className="space-y-2">
                {certificates.map((c) => (
                  <div key={c.id} className="bg-slate-50 border border-slate-200 p-2.5 rounded-lg flex items-center justify-between text-xs font-mono">
                    <div>
                      <span className="font-bold text-slate-800">{c.certificate_number}</span>
                      <span className="text-slate-500 block text-[10px]">Quantity: {c.quantity} Packs</span>
                    </div>
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${c.is_verified ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'}`}>
                      {c.is_verified ? 'Verified' : 'Pending Regulator'}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

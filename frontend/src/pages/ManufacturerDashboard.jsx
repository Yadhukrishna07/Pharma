import React, { useState, useEffect } from 'react';
import { Factory, Flame, CheckCircle, ArrowRight, RefreshCw, Building } from 'lucide-react';
import { destructionAPI, batchAPI } from '../services/api';
import StatusBadge from '../components/StatusBadge';
import ProgressTracker from '../components/ProgressTracker';

export default function ManufacturerDashboard() {
  const [batches, setBatches] = useState([]);
  const [loading, setLoading] = useState(false);
  const [actionMsg, setActionMsg] = useState(null);

  useEffect(() => {
    fetchBatches();
  }, []);

  const fetchBatches = async () => {
    try {
      const res = await batchAPI.getBatches();
      setBatches(res.data);
    } catch (e) {
      console.error(e);
    }
  };

  const primaryBatch = batches.find((b) => b.batch_number === 'BATCH-001') || batches[0];

  const handleHandoff = async () => {
    if (!primaryBatch) return;
    setLoading(true);
    setActionMsg(null);
    try {
      await destructionAPI.handoff({
        batch_id: primaryBatch.id,
        from_role: 'DISTRIBUTOR',
        to_role: 'MANUFACTURER',
        received_quantity: primaryBatch.quantity,
      });
      setActionMsg({ type: 'success', text: 'Reverse handoff confirmed! Batch received at Sun Pharma facility.' });
      fetchBatches();
    } catch (err) {
      setActionMsg({ type: 'error', text: err.response?.data?.detail || 'Handoff confirmation failed.' });
    } finally {
      setLoading(false);
    }
  };

  const handleScheduleDestruction = async () => {
    if (!primaryBatch) return;
    setLoading(true);
    setActionMsg(null);
    try {
      await destructionAPI.scheduleDestruction(primaryBatch.id, 5); // BioClean Facility ID=5
      setActionMsg({
        type: 'success',
        text: 'Destruction scheduled successfully at BioClean Biomedical Waste Facility!',
      });
      fetchBatches();
    } catch (err) {
      setActionMsg({ type: 'error', text: err.response?.data?.detail || 'Failed to schedule destruction.' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">Manufacturer Compliance Portal</h1>
          <p className="text-xs text-slate-500 mt-1">
            Logged in as <span className="font-bold text-slate-700">Sun Pharma Laboratories</span>
          </p>
        </div>
        <button onClick={fetchBatches} className="btn-secondary text-xs self-start sm:self-auto">
          <RefreshCw className="w-3.5 h-3.5" /> Refresh Batches
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

      {/* Primary Batch Overview */}
      {primaryBatch && (
        <div className="enterprise-card bg-white border border-slate-200 p-6 rounded-2xl shadow-sm space-y-6">
          <div className="flex items-center justify-between flex-wrap gap-4 border-b border-slate-100 pb-4">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-xl bg-purple-50 border border-purple-200 flex items-center justify-center text-purple-700">
                <Factory className="w-6 h-6" />
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

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-4 border-t border-slate-100">
            {/* Action 1: Handoff Confirmation */}
            <div className="bg-slate-50 p-5 rounded-xl border border-slate-200 space-y-3">
              <div className="flex items-center gap-2">
                <Building className="w-5 h-5 text-purple-700" />
                <h3 className="font-bold text-slate-900 text-sm">Handoff Confirmation Screen</h3>
              </div>
              <p className="text-xs text-slate-600 leading-relaxed">
                Acknowledge receipt of returned batch from Distributor warehouse into Manufacturer quarantine.
              </p>
              <div className="text-xs font-mono bg-white p-2.5 rounded border border-slate-200">
                Current Location: <span className="font-bold text-slate-800">{primaryBatch.current_location}</span>
              </div>
              <button
                onClick={handleHandoff}
                disabled={loading || primaryBatch.current_status === 'RECEIVED_BY_MANUFACTURER'}
                className="btn-primary w-full text-xs"
              >
                {primaryBatch.current_status === 'RECEIVED_BY_MANUFACTURER'
                  ? 'Reverse Handoff Already Confirmed'
                  : 'Confirm Reverse Handoff Receipt'}
              </button>
            </div>

            {/* Action 2: Schedule Destruction */}
            <div className="bg-purple-50/50 p-5 rounded-xl border border-purple-100 space-y-3">
              <div className="flex items-center gap-2">
                <Flame className="w-5 h-5 text-purple-800" />
                <h3 className="font-bold text-slate-900 text-sm">Schedule Facility Destruction</h3>
              </div>
              <p className="text-xs text-slate-600 leading-relaxed">
                Dispatch batch for high-temperature incineration at authorized biomedical waste facility.
              </p>
              <div className="text-xs font-semibold text-purple-900 bg-white p-2.5 rounded border border-purple-200 flex items-center justify-between">
                <span>Authorized Facility:</span>
                <span className="font-mono font-bold">BioClean Biomedical Waste</span>
              </div>
              <button
                onClick={handleScheduleDestruction}
                disabled={
                  loading ||
                  ['DESTRUCTION_SCHEDULED', 'DESTROYED', 'CERTIFICATE_VERIFIED', 'CLOSED'].includes(
                    primaryBatch.current_status
                  )
                }
                className="btn-primary w-full text-xs bg-purple-800 hover:bg-purple-900"
              >
                Schedule Destruction at BioClean Facility
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

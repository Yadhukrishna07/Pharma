import React, { useState, useEffect } from 'react';
import { Factory, Flame, CheckCircle, ArrowRight, RefreshCw, Building } from 'lucide-react';
import { dashboardAPI, destructionAPI } from '../services/api';
import StatusBadge from '../components/StatusBadge';
import ProgressTracker from '../components/ProgressTracker';
import RecentActivityFeed from '../components/RecentActivityFeed';
import ModeratorInsightCard from '../components/ModeratorInsightCard';
import EvidenceCapture from '../components/EvidenceCapture';

export default function ManufacturerDashboard() {
  const [data, setData] = useState(null);
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
      const res = await dashboardAPI.getManufacturerDashboard();
      setData(res.data);
    } catch (e) {
      console.error('Error fetching manufacturer dashboard:', e);
    } finally {
      if (showLoading) setLoading(false);
    }
  };

  const handleHandoff = async () => {
    if (!data?.batch?.id) return;
    setLoading(true);
    setActionMsg(null);
    try {
      await destructionAPI.handoff({
        batch_id: data.batch.id,
        from_role: 'DISTRIBUTOR',
        to_role: 'MANUFACTURER',
        received_quantity: data.batch.quantity,
      });
      setActionMsg({
        type: 'success',
        text: 'Reverse chain handoff confirmed! Batch received into Sun Pharma quarantine warehouse.',
      });
      fetchDashboard(false);
    } catch (err) {
      setActionMsg({ type: 'error', text: err.response?.data?.detail || 'Handoff confirmation failed.' });
    } finally {
      setLoading(false);
    }
  };

  const handleScheduleDestruction = async () => {
    if (!data?.batch?.id) return;
    setLoading(true);
    setActionMsg(null);
    try {
      await destructionAPI.scheduleDestruction(data.batch.id, data.facility_id || 5);
      setActionMsg({
        type: 'success',
        text: `Destruction successfully scheduled at ${data.facility_name || 'BioClean Biomedical Waste Facility'}!`,
      });
      fetchDashboard(false);
    } catch (err) {
      setActionMsg({ type: 'error', text: err.response?.data?.detail || 'Failed to schedule destruction.' });
    } finally {
      setLoading(false);
    }
  };

  const batch = data?.batch;
  const currentStatus = batch?.current_status || 'NOT_INITIATED';

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
              Manufacturer Compliance Portal
            </h1>
            <span className="inline-flex items-center gap-1 bg-emerald-50 text-emerald-700 text-[10px] font-bold px-2 py-0.5 rounded-full border border-emerald-200">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
              LIVE POLLING
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Logged in as <span className="font-bold text-slate-700">{data?.organization_name || 'Sun Pharma Laboratories'}</span>
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

      {/* Primary Batch Overview */}
      {batch && (
        <div className="enterprise-card bg-white border border-slate-200 p-6 rounded-2xl shadow-sm space-y-6">
          <div className="flex items-center justify-between flex-wrap gap-4 border-b border-slate-100 pb-4">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-xl bg-purple-50 border border-purple-200 flex items-center justify-center text-purple-700">
                <Factory className="w-6 h-6" />
              </div>
              <div>
                <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider block">
                  Managed Batch
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
              <span className="text-slate-400 block text-[10px] font-sans font-semibold">CURRENT QUANTITY</span>
              <span className="font-extrabold text-slate-900 text-sm">{batch.quantity} Packs</span>
            </div>
            <div>
              <span className="text-slate-400 block text-[10px] font-sans font-semibold">MANUFACTURER RECEIPT</span>
              <span className={`font-bold text-sm ${data.manufacturer_receipt_state === 'CONFIRMED' ? 'text-emerald-700' : 'text-amber-600'}`}>
                {data.manufacturer_receipt_state}
              </span>
            </div>
            <div>
              <span className="text-slate-400 block text-[10px] font-sans font-semibold">DESTRUCTION SCHEDULING</span>
              <span className={`font-bold text-sm ${data.destruction_scheduling_state === 'SCHEDULED' ? 'text-purple-700' : 'text-slate-600'}`}>
                {data.destruction_scheduling_state}
              </span>
            </div>
            <div>
              <span className="text-slate-400 block text-[10px] font-sans font-semibold">FACILITY</span>
              <span className="font-bold text-slate-800 text-xs font-sans block truncate">{data.facility_name}</span>
            </div>
          </div>

          {/* Derived Next Action Banner */}
          <div className="bg-purple-50 border border-purple-200 rounded-xl p-3 text-xs flex items-center gap-2.5">
            <span className="bg-purple-700 text-white text-[10px] font-extrabold px-2 py-0.5 rounded uppercase tracking-wider shrink-0">
              NEXT ACTION
            </span>
            <span className="text-purple-900 font-medium">{data.next_action}</span>
          </div>

          <ProgressTracker currentStatus={batch.current_status} />

          {/* Action Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-4 border-t border-slate-100">
            {/* Action 1: Handoff Confirmation */}
            <div className="bg-slate-50 p-5 rounded-xl border border-slate-200 space-y-3">
              <div className="flex items-center gap-2">
                <Building className="w-5 h-5 text-purple-700" />
                <h3 className="font-bold text-slate-900 text-sm">Handoff Confirmation Screen</h3>
              </div>
              <p className="text-xs text-slate-600 leading-relaxed">
                Acknowledge custody receipt of returned batch from Distributor warehouse into Manufacturer quarantine.
              </p>
              <div className="text-xs font-mono bg-white p-2.5 rounded border border-slate-200">
                Current Location: <span className="font-bold text-slate-800">{batch.current_location}</span>
              </div>
              <button
                onClick={handleHandoff}
                disabled={loading || data.manufacturer_receipt_state === 'CONFIRMED' || !['RECEIVED_BY_DISTRIBUTOR', 'DISPUTED'].includes(currentStatus)}
                className="btn-primary w-full text-xs"
              >
                {data.manufacturer_receipt_state === 'CONFIRMED'
                  ? 'Reverse Handoff Confirmed'
                  : currentStatus === 'DISPUTED'
                  ? 'Resolve Dispute First'
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
                Dispatch quarantined batch for high-temperature incineration at authorized biomedical waste facility.
              </p>
              <div className="text-xs font-semibold text-purple-900 bg-white p-2.5 rounded border border-purple-200 flex items-center justify-between">
                <span>Authorized Facility:</span>
                <span className="font-mono font-bold">{data.facility_name}</span>
              </div>
              <button
                onClick={handleScheduleDestruction}
                disabled={
                  loading ||
                  currentStatus !== 'RECEIVED_BY_MANUFACTURER'
                }
                className="btn-primary w-full text-xs bg-purple-800 hover:bg-purple-900"
              >
                {data.destruction_scheduling_state === 'SCHEDULED'
                  ? 'Destruction Scheduled'
                  : currentStatus === 'RECEIVED_BY_MANUFACTURER'
                  ? `Schedule Destruction at ${data.facility_name}`
                  : 'Awaiting Manufacturer Receipt'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Manufacturer Photo Evidence Capture & AI Moderator Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <EvidenceCapture
          role="Manufacturer"
          batchNumber={batch?.batch_number || 'BATCH-001'}
          productionId="PROD-2026-088"
          productName={batch?.medicine_name || 'Augmentin Duo 625mg'}
          stageName="Quality Inspection & Quarantine"
          organizationName={data?.organization_name || 'Sun Pharma Laboratories'}
          title="Photo Evidence"
          description="Capture real photograph of pharmaceutical products, manufacturing/packaging process, lot info, or quality inspection."
        />
        <ModeratorInsightCard insight={data?.moderator_insight} />
      </div>

      {/* Grid: Recent Activity Feed */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <RecentActivityFeed events={data?.recent_activity} title="Recent Activity (BATCH-001)" />
      </div>
    </div>
  );
}

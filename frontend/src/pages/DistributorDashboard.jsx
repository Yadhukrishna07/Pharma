import React, { useState, useEffect } from 'react';
import { Truck, CheckCircle, AlertTriangle, PackageCheck, RefreshCw, FileText, ArrowRight } from 'lucide-react';
import { dashboardAPI, returnAPI, disputeAPI } from '../services/api';
import StatusBadge from '../components/StatusBadge';
import ProgressTracker from '../components/ProgressTracker';
import RecentActivityFeed from '../components/RecentActivityFeed';
import ModeratorInsightCard from '../components/ModeratorInsightCard';
import EvidenceCapture from '../components/EvidenceCapture';

export default function DistributorDashboard() {
  const [data, setData] = useState(null);
  const [receivedQtyInput, setReceivedQtyInput] = useState(95); // Default 95 per spec to demo discrepancy
  const [resolutionNotes, setResolutionNotes] = useState(
    'Discrepancy verified: 5 units damaged in transit and discarded per SOP.'
  );
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
      const res = await dashboardAPI.getDistributorDashboard();
      setData(res.data);
    } catch (e) {
      console.error('Error fetching distributor dashboard:', e);
    } finally {
      if (showLoading) setLoading(false);
    }
  };

  const handlePickup = async () => {
    if (!data?.incoming_return?.id) return;
    setLoading(true);
    setActionMsg(null);
    try {
      await returnAPI.confirmPickup(data.incoming_return.id);
      setActionMsg({
        type: 'success',
        text: 'Physical pickup confirmed at MedPlus Central! Status updated to PICKUP_CONFIRMED.',
      });
      fetchDashboard(false);
    } catch (err) {
      setActionMsg({ type: 'error', text: err.response?.data?.detail || 'Pickup failed.' });
    } finally {
      setLoading(false);
    }
  };

  const handleReceive = async () => {
    if (!data?.incoming_return?.id) return;
    setLoading(true);
    setActionMsg(null);
    try {
      const res = await returnAPI.receiveReturn(data.incoming_return.id, Number(receivedQtyInput));
      if (res.data.status === 'disputed' || res.data.status === 'DISPUTED' || res.data.batch_status === 'DISPUTED') {
        setActionMsg({
          type: 'warning',
          text: `Quantity Discrepancy Detected! Status moved to DISPUTED (${data.expected_quantity} declared vs ${receivedQtyInput} received). Dispute created & Moderator AI notified.`,
        });
      } else {
        setActionMsg({
          type: 'success',
          text: 'Receipt count matched! Inventory verified & forwarded to Manufacturer.',
        });
      }
      fetchDashboard(false);
    } catch (err) {
      setActionMsg({ type: 'error', text: err.response?.data?.detail || 'Receipt processing failed.' });
    } finally {
      setLoading(false);
    }
  };

  const handleResolveDispute = async () => {
    if (!data?.dispute?.id) return;
    setLoading(true);
    setActionMsg(null);
    try {
      await disputeAPI.resolveDispute(data.dispute.id, resolutionNotes);
      setActionMsg({
        type: 'success',
        text: 'Dispute resolved! Workflow resumed → RECEIVED_BY_MANUFACTURER.',
      });
      fetchDashboard(false);
    } catch (err) {
      setActionMsg({ type: 'error', text: err.response?.data?.detail || 'Failed to resolve dispute.' });
    } finally {
      setLoading(false);
    }
  };

  const batch = data?.batch;
  const currentStatus = batch?.current_status || 'NOT_INITIATED';
  const dispute = data?.dispute;
  const hasOpenDispute = dispute && dispute.status === 'OPEN';

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
              Distributor Logistics Portal
            </h1>
            <span className="inline-flex items-center gap-1 bg-emerald-50 text-emerald-700 text-[10px] font-bold px-2 py-0.5 rounded-full border border-emerald-200">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
              LIVE POLLING
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Logged in as <span className="font-bold text-slate-700">{data?.organization_name || 'BlueDart Pharma Logistics'}</span>
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
              : actionMsg.type === 'warning'
              ? 'bg-amber-50 border-amber-300 text-amber-900'
              : 'bg-rose-50 border-rose-200 text-rose-900'
          }`}
        >
          {actionMsg.type === 'warning' ? (
            <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
          ) : (
            <CheckCircle className="w-4 h-4 text-emerald-600 shrink-0" />
          )}
          <span>{actionMsg.text}</span>
        </div>
      )}

      {/* Active Batch Banner */}
      {batch && (
        <div className="enterprise-card bg-white border border-slate-200 p-6 rounded-2xl shadow-sm space-y-4">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <div>
              <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider block">
                Incoming Return Shipment
              </span>
              <h2 className="text-lg font-bold text-slate-900">
                {batch.batch_number} — {batch.medicine_name}
              </h2>
            </div>
            <StatusBadge status={batch.current_status} />
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 pt-3 border-t border-slate-100 text-xs font-mono">
            <div>
              <span className="text-slate-400 block text-[10px] font-sans font-semibold">EXPECTED QUANTITY</span>
              <span className="font-extrabold text-slate-800">{data.expected_quantity} Packs</span>
            </div>
            <div>
              <span className="text-slate-400 block text-[10px] font-sans font-semibold">RECEIVED QUANTITY</span>
              <span className="font-extrabold text-blue-700">
                {data.received_quantity !== null ? `${data.received_quantity} Packs` : 'Pending Intake'}
              </span>
            </div>
            <div>
              <span className="text-slate-400 block text-[10px] font-sans font-semibold">PICKUP STATE</span>
              <span className={`font-bold ${data.pickup_state === 'CONFIRMED' ? 'text-emerald-700' : 'text-amber-600'}`}>
                {data.pickup_state}
              </span>
            </div>
            <div>
              <span className="text-slate-400 block text-[10px] font-sans font-semibold">RECEIPT STATE</span>
              <span className={`font-bold ${data.receipt_state === 'RECEIVED' ? 'text-emerald-700' : data.receipt_state === 'DISPUTED' ? 'text-rose-700' : 'text-slate-600'}`}>
                {data.receipt_state}
              </span>
            </div>
            <div>
              <span className="text-slate-400 block text-[10px] font-sans font-semibold">DISPUTE STATUS</span>
              <span className={`font-bold ${hasOpenDispute ? 'text-rose-600' : dispute?.status === 'RESOLVED' ? 'text-emerald-700' : 'text-slate-500'}`}>
                {hasOpenDispute ? 'DISPUTE OPEN' : dispute ? `DISPUTE ${dispute.status}` : 'NONE'}
              </span>
            </div>
          </div>

          {/* Next Action Banner */}
          <div className="bg-sky-50 border border-sky-200 rounded-xl p-3 text-xs flex items-center gap-2.5">
            <span className="bg-sky-700 text-white text-[10px] font-extrabold px-2 py-0.5 rounded uppercase tracking-wider shrink-0">
              NEXT ACTION
            </span>
            <span className="text-sky-900 font-medium">{data.next_action}</span>
          </div>

          <ProgressTracker currentStatus={batch.current_status} />
        </div>
      )}

      {/* DISPUTE ALERT INDICATOR PANEL */}
      {dispute && (
        <div className={`enterprise-card p-6 rounded-2xl shadow-sm space-y-4 border-2 ${
          hasOpenDispute ? 'bg-amber-50 border-amber-300' : 'bg-emerald-50 border-emerald-300'
        }`}>
          <div className="flex items-center gap-3 border-b border-amber-200 pb-3">
            <AlertTriangle className={`w-6 h-6 shrink-0 ${hasOpenDispute ? 'text-amber-600' : 'text-emerald-600'}`} />
            <div>
              <h3 className={`font-extrabold text-base ${hasOpenDispute ? 'text-amber-900' : 'text-emerald-900'}`}>
                {hasOpenDispute ? 'DISPUTE OPEN: QUANTITY MISMATCH' : 'DISPUTE RESOLVED'}
              </h3>
              <p className={`text-xs ${hasOpenDispute ? 'text-amber-700' : 'text-emerald-700'}`}>
                {hasOpenDispute
                  ? 'Discrepancy detected: 100 declared vs 95 received.'
                  : `Dispute resolved with notes: "${dispute.resolution_notes}"`}
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs bg-white/90 p-3.5 rounded-xl border border-amber-200 font-mono">
            <div>
              <span className="text-slate-500 block text-[10px] font-sans">EXPECTED (DECLARED)</span>
              <span className="font-bold text-slate-900 text-sm">{dispute.declared_qty} Packs</span>
            </div>
            <div>
              <span className="text-slate-500 block text-[10px] font-sans">PHYSICAL (RECEIVED)</span>
              <span className="font-bold text-amber-700 text-sm">{dispute.received_qty} Packs</span>
            </div>
            <div>
              <span className="text-slate-500 block text-[10px] font-sans">VARIANCE</span>
              <span className="font-bold text-rose-700 text-sm">
                -{dispute.variance} Packs (Discrepancy)
              </span>
            </div>
          </div>

          {hasOpenDispute && (
            <div className="space-y-3 pt-2">
              <label className="block text-xs font-semibold text-amber-900">
                Dispute Resolution Explanation & Audit Trail Note
              </label>
              <textarea
                className="input-field text-xs font-sans h-20"
                value={resolutionNotes}
                onChange={(e) => setResolutionNotes(e.target.value)}
                placeholder="Enter details explaining resolution of discrepancy..."
              />
              <button
                onClick={handleResolveDispute}
                disabled={loading}
                className="btn-warning w-full text-xs font-bold py-2.5"
              >
                {loading ? 'Resolving...' : 'Resolve Dispute & Resume Workflow to Manufacturer'}
              </button>
            </div>
          )}
        </div>
      )}

      {/* Logistics Actions Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Step 1: Confirm Pickup */}
        <div className="enterprise-card space-y-4">
          <div className="flex items-center gap-2 border-b border-slate-100 pb-3">
            <Truck className="w-5 h-5 text-blue-800" />
            <h3 className="font-bold text-slate-900 text-base">Step 1: Confirm Pharmacy Pickup</h3>
          </div>

          <p className="text-xs text-slate-600 leading-relaxed">
            Confirm physical collection of expired batch from <strong>MedPlus Central Indiranagar</strong>.
          </p>

          <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 space-y-3 text-xs">
            <div className="flex justify-between">
              <span className="text-slate-500">Return Request:</span>
              <span className="font-mono font-bold">
                {data?.incoming_return ? `#${data.incoming_return.id}` : 'None'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Pickup Status:</span>
              <span className="font-bold text-blue-700">{data?.pickup_state || 'PENDING'}</span>
            </div>

            <button
              onClick={handlePickup}
              disabled={loading || data?.pickup_state === 'CONFIRMED' || currentStatus !== 'RETURN_REQUESTED'}
              className="btn-primary w-full text-xs mt-2"
            >
              {data?.pickup_state === 'CONFIRMED'
                ? 'Pickup Confirmed'
                : currentStatus === 'RETURN_REQUESTED'
                ? 'Confirm Pickup at Pharmacy'
                : 'Awaiting Pharmacy Return Request'}
            </button>
          </div>
        </div>

        {/* Step 2: Warehouse Receipt Verification */}
        <div className="enterprise-card space-y-4">
          <div className="flex items-center gap-2 border-b border-slate-100 pb-3">
            <PackageCheck className="w-5 h-5 text-blue-800" />
            <h3 className="font-bold text-slate-900 text-base">Step 2: Receipt Verification & Quantity Check</h3>
          </div>

          <p className="text-xs text-slate-600 leading-relaxed">
            Input physical received quantity upon arrival at BlueDart warehouse. Discrepancies trigger a DISPUTED state.
          </p>

          <div className="space-y-4">
            <div className="bg-blue-50/50 p-3 rounded-xl border border-blue-100 text-xs flex justify-between">
              <span className="text-slate-600 font-medium">Expected Declared Quantity:</span>
              <span className="font-bold text-blue-900">{data?.expected_quantity || 100} Packs</span>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Input Actual Received Quantity
              </label>
              <input
                type="number"
                className="input-field font-mono text-sm"
                value={receivedQtyInput}
                onChange={(e) => setReceivedQtyInput(e.target.value)}
                disabled={currentStatus !== 'PICKUP_CONFIRMED'}
              />
              <p className="text-[11px] text-amber-700 mt-1 font-medium">
                Note: Default is <strong>95</strong> (demonstrating 100 declared vs 95 received discrepancy).
              </p>
            </div>

            <button
              onClick={handleReceive}
              disabled={loading || currentStatus !== 'PICKUP_CONFIRMED'}
              className="btn-primary w-full text-xs"
            >
              {loading
                ? 'Processing...'
                : currentStatus === 'PICKUP_CONFIRMED'
                ? 'Verify Receipt & Process Quantity Check'
                : `Receipt Verification [Status: ${currentStatus}]`}
            </button>
          </div>
        </div>
      </div>

      {/* Photo Evidence Capture & AI Moderator Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <EvidenceCapture
          role="Distributor"
          batchNumber={batch?.batch_number || 'BATCH-001'}
          shipmentId={data?.incoming_return ? `SHIP-RET-${data.incoming_return.id}` : 'SHIP-2026-0042'}
          organizationName={data?.organization_name || 'BlueDart Pharma Logistics'}
          title="Photo Evidence"
          description="Capture real photograph showing pharmaceutical shipment being received, stored, transferred, or dispatched."
        />
        <ModeratorInsightCard insight={data?.moderator_insight} />
      </div>

      {/* Live Recent Activity Feed */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <RecentActivityFeed events={data?.recent_activity} title="Recent Activity (BATCH-001)" />
      </div>
    </div>
  );
}

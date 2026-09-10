import React, { useState, useEffect } from 'react';
import { Truck, CheckCircle, AlertTriangle, PackageCheck, RefreshCw, FileText } from 'lucide-react';
import { returnAPI, disputeAPI, batchAPI } from '../services/api';
import StatusBadge from '../components/StatusBadge';
import ProgressTracker from '../components/ProgressTracker';

export default function DistributorDashboard() {
  const [returns, setReturns] = useState([]);
  const [disputes, setDisputes] = useState([]);
  const [batches, setBatches] = useState([]);
  const [receivedQtyInput, setReceivedQtyInput] = useState(95); // Default 95 to demo discrepancy
  const [resolutionNotes, setResolutionNotes] = useState(
    'Discrepancy verified: 5 units damaged in transit and discarded per SOP.'
  );
  const [loading, setLoading] = useState(false);
  const [actionMsg, setActionMsg] = useState(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [returnsRes, disputesRes, batchesRes] = await Promise.all([
        returnAPI.getReturns(),
        disputeAPI.getDisputes(),
        batchAPI.getBatches(),
      ]);
      setReturns(returnsRes.data);
      setDisputes(disputesRes.data);
      setBatches(batchesRes.data);
    } catch (e) {
      console.error(e);
    }
  };

  const handlePickup = async (returnId) => {
    setLoading(true);
    setActionMsg(null);
    try {
      await returnAPI.confirmPickup(returnId);
      setActionMsg({ type: 'success', text: 'Pickup confirmed! Status updated to PICKUP_CONFIRMED.' });
      loadData();
    } catch (err) {
      setActionMsg({ type: 'error', text: err.response?.data?.detail || 'Pickup failed.' });
    } finally {
      setLoading(false);
    }
  };

  const handleReceive = async (returnId) => {
    setLoading(true);
    setActionMsg(null);
    try {
      const res = await returnAPI.receiveReturn(returnId, Number(receivedQtyInput));
      if (res.data.status === 'disputed') {
        setActionMsg({
          type: 'warning',
          text: `Quantity Discrepancy Detected! State moved to DISPUTED. (Declared: 100, Received: ${receivedQtyInput})`,
        });
      } else {
        setActionMsg({ type: 'success', text: 'Receipt verified and matched! Forwarded to Manufacturer.' });
      }
      loadData();
    } catch (err) {
      setActionMsg({ type: 'error', text: err.response?.data?.detail || 'Receive processing failed.' });
    } finally {
      setLoading(false);
    }
  };

  const handleResolveDispute = async (disputeId) => {
    setLoading(true);
    setActionMsg(null);
    try {
      await disputeAPI.resolveDispute(disputeId, resolutionNotes);
      setActionMsg({ type: 'success', text: 'Dispute resolved! Workflow resumed → RECEIVED_BY_MANUFACTURER.' });
      loadData();
    } catch (err) {
      setActionMsg({ type: 'error', text: err.response?.data?.detail || 'Failed to resolve dispute.' });
    } finally {
      setLoading(false);
    }
  };

  const activeReturn = returns[0];
  const activeBatch = batches.find((b) => b.id === activeReturn?.batch_id) || batches[0];
  const openDispute = disputes.find((d) => d.status === 'OPEN');

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">Distributor Logistics Portal</h1>
          <p className="text-xs text-slate-500 mt-1">
            Logged in as <span className="font-bold text-slate-700">BlueDart Pharma Logistics</span>
          </p>
        </div>
        <button onClick={loadData} className="btn-secondary text-xs self-start sm:self-auto">
          <RefreshCw className="w-3.5 h-3.5" /> Refresh Data
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
      {activeBatch && (
        <div className="enterprise-card bg-white border border-slate-200 p-6 rounded-2xl shadow-sm space-y-4">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <div>
              <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider block">Managed Batch</span>
              <h2 className="text-lg font-bold text-slate-900">{activeBatch.batch_number} — {activeBatch.medicine_name}</h2>
            </div>
            <StatusBadge status={activeBatch.current_status} />
          </div>

          <ProgressTracker currentStatus={activeBatch.current_status} />
        </div>
      )}

      {/* DISPUTE ALERT INDICATOR PANEL */}
      {openDispute && (
        <div className="enterprise-card bg-amber-50 border-2 border-amber-300 rounded-2xl p-6 shadow-sm space-y-4">
          <div className="flex items-center gap-3 border-b border-amber-200 pb-3">
            <AlertTriangle className="w-6 h-6 text-amber-600 shrink-0" />
            <div>
              <h3 className="font-extrabold text-amber-900 text-base">QUANTITY DISPUTE ACTIVE</h3>
              <p className="text-xs text-amber-700">
                Discrepancy detected between Pharmacy declaration and Distributor receipt.
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs bg-white/80 p-3.5 rounded-xl border border-amber-200">
            <div>
              <span className="text-slate-500 block text-[10px]">DECLARED QUANTITY</span>
              <span className="font-bold text-slate-900 text-sm">{openDispute.declared_qty} Packs</span>
            </div>
            <div>
              <span className="text-slate-500 block text-[10px]">RECEIVED QUANTITY</span>
              <span className="font-bold text-amber-700 text-sm">{openDispute.received_qty} Packs</span>
            </div>
            <div>
              <span className="text-slate-500 block text-[10px]">VARIANCE</span>
              <span className="font-bold text-rose-700 text-sm">
                -{openDispute.declared_qty - openDispute.received_qty} Packs (Discrepancy)
              </span>
            </div>
          </div>

          <div className="space-y-3 pt-2">
            <label className="block text-xs font-semibold text-amber-900">Resolution Notes & Audit Explanation</label>
            <textarea
              className="input-field text-xs font-sans h-20"
              value={resolutionNotes}
              onChange={(e) => setResolutionNotes(e.target.value)}
              placeholder="Enter details explaining resolution of discrepancy..."
            />
            <button
              onClick={() => handleResolveDispute(openDispute.id)}
              disabled={loading}
              className="btn-warning w-full text-xs font-bold py-2.5"
            >
              {loading ? 'Resolving...' : 'Resolve Dispute & Resume Workflow to Manufacturer'}
            </button>
          </div>
        </div>
      )}

      {/* Logistics Verification & Actions */}
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

          {activeReturn ? (
            <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 space-y-3 text-xs">
              <div className="flex justify-between">
                <span className="text-slate-500">Return Request ID:</span>
                <span className="font-mono font-bold">#{activeReturn.id}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Declared Quantity:</span>
                <span className="font-bold">{activeReturn.declared_quantity} Packs</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Status:</span>
                <span className="font-bold text-blue-700">{activeReturn.status}</span>
              </div>

              <button
                onClick={() => handlePickup(activeReturn.id)}
                disabled={loading || activeReturn.status !== 'PENDING'}
                className="btn-primary w-full text-xs mt-2"
              >
                {activeReturn.status === 'PENDING' ? 'Confirm Pickup at Pharmacy' : 'Pickup Already Confirmed'}
              </button>
            </div>
          ) : (
            <p className="text-xs text-slate-400 italic">No active return requests pending pickup.</p>
          )}
        </div>

        {/* Step 2: Warehouse Receipt Verification */}
        <div className="enterprise-card space-y-4">
          <div className="flex items-center gap-2 border-b border-slate-100 pb-3">
            <PackageCheck className="w-5 h-5 text-blue-800" />
            <h3 className="font-bold text-slate-900 text-base">Step 2: Receipt Verification & Quantity Check</h3>
          </div>

          <p className="text-xs text-slate-600 leading-relaxed">
            Input physical received quantity upon warehouse arrival. Discrepancies automatically trigger a DISPUTE state.
          </p>

          {activeReturn ? (
            <div className="space-y-4">
              <div className="bg-blue-50/50 p-3 rounded-xl border border-blue-100 text-xs flex justify-between">
                <span className="text-slate-600 font-medium">Expected Declared Quantity:</span>
                <span className="font-bold text-blue-900">{activeReturn.declared_quantity} Packs</span>
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
                />
                <p className="text-[11px] text-amber-700 mt-1 font-medium">
                  Note: Default set to <strong>95</strong> to demonstrate automatic Discrepancy & Dispute trigger.
                </p>
              </div>

              <button
                onClick={() => handleReceive(activeReturn.id)}
                disabled={loading || activeBatch?.current_status === 'DISPUTED'}
                className="btn-primary w-full text-xs"
              >
                {loading ? 'Processing...' : 'Verify Receipt & Process Quantity Check'}
              </button>
            </div>
          ) : (
            <p className="text-xs text-slate-400 italic">No active returns awaiting warehouse receipt.</p>
          )}
        </div>
      </div>
    </div>
  );
}

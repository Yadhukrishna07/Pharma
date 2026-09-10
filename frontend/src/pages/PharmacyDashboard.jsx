import React, { useState, useEffect } from 'react';
import { Pill, QrCode, ArrowUpRight, ShieldAlert, CheckCircle2, AlertTriangle, RefreshCw } from 'lucide-react';
import { batchAPI, returnAPI } from '../services/api';
import StatusBadge from '../components/StatusBadge';
import ProgressTracker from '../components/ProgressTracker';

export default function PharmacyDashboard() {
  const [batches, setBatches] = useState([]);
  const [scanInput, setScanInput] = useState('BATCH-001');
  const [scanResult, setScanResult] = useState(null);
  const [fraudModal, setFraudModal] = useState(null);
  const [loading, setLoading] = useState(false);
  const [returnMsg, setReturnMsg] = useState(null);

  // Pre-filled return request form
  const [returnForm, setReturnForm] = useState({
    batch_id: 1,
    declared_quantity: 100,
    distributor_id: 3, // BlueDart
  });

  useEffect(() => {
    fetchBatches();
  }, []);

  const fetchBatches = async () => {
    try {
      const res = await batchAPI.getBatches();
      setBatches(res.data);
      if (res.data.length > 0) {
        setReturnForm((prev) => ({ ...prev, batch_id: res.data[0].id }));
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleScan = async (e) => {
    e.preventDefault();
    if (!scanInput) return;

    setLoading(true);
    setScanResult(null);

    try {
      const res = await batchAPI.scanBatch(
        scanInput,
        'MedPlus Central Indiranagar',
        'PHARMACY'
      );
      setScanResult(res.data);

      if (res.data.fraud_detected) {
        setFraudModal(res.data);
      }
      fetchBatches();
    } catch (err) {
      setScanResult({
        fraud_detected: false,
        message: err.response?.data?.detail || 'Batch scan failed or batch not found.',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleTriggerReturn = async (e) => {
    e.preventDefault();
    setLoading(true);
    setReturnMsg(null);

    try {
      const res = await returnAPI.createReturnRequest({
        batch_id: Number(returnForm.batch_id),
        declared_quantity: Number(returnForm.declared_quantity),
        distributor_id: Number(returnForm.distributor_id),
      });
      setReturnMsg({ type: 'success', text: `Return request created successfully! Request ID: ${res.data.id}` });
      fetchBatches();
    } catch (err) {
      setReturnMsg({
        type: 'error',
        text: err.response?.data?.detail || 'Failed to trigger return request.',
      });
    } finally {
      setLoading(false);
    }
  };

  const primaryBatch = batches.find((b) => b.batch_number === 'BATCH-001') || batches[0];

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">Pharmacy Operations Portal</h1>
          <p className="text-xs text-slate-500 mt-1">
            Logged in as <span className="font-bold text-slate-700">MedPlus Central Indiranagar</span>
          </p>
        </div>
        <button onClick={fetchBatches} className="btn-secondary text-xs self-start sm:self-auto">
          <RefreshCw className="w-3.5 h-3.5" /> Refresh Batches
        </button>
      </div>

      {/* Batch Expiry Status Card */}
      {primaryBatch && (
        <div className="enterprise-card bg-gradient-to-r from-blue-900 to-slate-900 text-white p-6 rounded-2xl shadow-md border-0">
          <div className="flex items-start justify-between flex-wrap gap-4 mb-4">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-xl bg-blue-800/80 border border-blue-700 flex items-center justify-center text-blue-300">
                <Pill className="w-6 h-6" />
              </div>
              <div>
                <span className="text-xs font-mono text-blue-300 uppercase tracking-wider">Active Shelf Inventory</span>
                <h2 className="text-xl font-extrabold text-white">{primaryBatch.medicine_name || 'Augmentin Duo 625mg'}</h2>
              </div>
            </div>
            <StatusBadge status={primaryBatch.current_status} />
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-4 border-t border-slate-800 text-xs">
            <div>
              <span className="text-slate-400 block text-[10px] font-mono">BATCH NUMBER</span>
              <span className="font-bold text-white font-mono">{primaryBatch.batch_number}</span>
            </div>
            <div>
              <span className="text-slate-400 block text-[10px] font-mono">QUANTITY</span>
              <span className="font-bold text-white">{primaryBatch.quantity} Packs</span>
            </div>
            <div>
              <span className="text-slate-400 block text-[10px] font-mono">EXPIRY DATE</span>
              <span className="font-bold text-amber-300">{primaryBatch.expiry_date}</span>
            </div>
            <div>
              <span className="text-slate-400 block text-[10px] font-mono">CURRENT LOCATION</span>
              <span className="font-bold text-slate-200">{primaryBatch.current_location || 'Pharmacy Shelf'}</span>
            </div>
          </div>

          {/* Progress Tracker */}
          <div className="mt-6 pt-4 border-t border-slate-800">
            <ProgressTracker currentStatus={primaryBatch.current_status} />
          </div>
        </div>
      )}

      {/* Grid of Actions: Scanner & Return Trigger */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Scanner Interface */}
        <div className="enterprise-card space-y-4">
          <div className="flex items-center gap-2 border-b border-slate-100 pb-3">
            <QrCode className="w-5 h-5 text-blue-800" />
            <h3 className="font-bold text-slate-900 text-base">Barcode / RFID Batch Scanner</h3>
          </div>

          <form onSubmit={handleScan} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Enter or Scan Batch ID</label>
              <div className="flex gap-2">
                <input
                  type="text"
                  className="input-field font-mono uppercase text-sm"
                  value={scanInput}
                  onChange={(e) => setScanInput(e.target.value)}
                  placeholder="e.g. BATCH-001"
                />
                <button type="submit" disabled={loading} className="btn-primary shrink-0 text-xs">
                  {loading ? 'Scanning...' : 'Scan Batch'}
                </button>
              </div>
              <p className="text-[11px] text-slate-400 mt-1">
                Tip: Scanning a destroyed or closed batch triggers real-time Re-Entry Fraud detection.
              </p>
            </div>
          </form>

          {scanResult && (
            <div
              className={`p-4 rounded-xl border text-xs leading-relaxed ${
                scanResult.fraud_detected
                  ? 'bg-rose-50 border-rose-300 text-rose-900'
                  : 'bg-emerald-50 border-emerald-200 text-emerald-900'
              }`}
            >
              <div className="font-bold flex items-center gap-1.5 mb-1">
                {scanResult.fraud_detected ? (
                  <ShieldAlert className="w-4 h-4 text-rose-600" />
                ) : (
                  <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                )}
                <span>{scanResult.fraud_detected ? 'FRAUD ALERT TRIGGERED' : 'Scan Verified'}</span>
              </div>
              <p>{scanResult.message}</p>
            </div>
          )}
        </div>

        {/* Return Request Trigger Form */}
        <div className="enterprise-card space-y-4">
          <div className="flex items-center gap-2 border-b border-slate-100 pb-3">
            <ArrowUpRight className="w-5 h-5 text-blue-800" />
            <h3 className="font-bold text-slate-900 text-base">Initiate Closed-Loop Return</h3>
          </div>

          <form onSubmit={handleTriggerReturn} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Select Batch</label>
              <select
                className="input-field text-xs font-mono"
                value={returnForm.batch_id}
                onChange={(e) => setReturnForm({ ...returnForm, batch_id: e.target.value })}
              >
                {batches.map((b) => (
                  <option key={b.id} value={b.id}>
                    {b.batch_number} — {b.medicine_name} ({b.quantity} packs) [{b.current_status}]
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Declared Quantity (Packs)</label>
              <input
                type="number"
                className="input-field text-xs font-mono"
                value={returnForm.declared_quantity}
                onChange={(e) => setReturnForm({ ...returnForm, declared_quantity: e.target.value })}
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Designated Logistics Partner</label>
              <select
                className="input-field text-xs"
                value={returnForm.distributor_id}
                onChange={(e) => setReturnForm({ ...returnForm, distributor_id: e.target.value })}
              >
                <option value={3}>BlueDart Pharma Logistics</option>
              </select>
            </div>

            <button type="submit" disabled={loading} className="btn-primary w-full text-xs">
              {loading ? 'Submitting...' : 'Submit Reverse Chain Return Request'}
            </button>
          </form>

          {returnMsg && (
            <div
              className={`p-3 rounded-lg border text-xs ${
                returnMsg.type === 'success'
                  ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
                  : 'bg-rose-50 border-rose-200 text-rose-800'
              }`}
            >
              {returnMsg.text}
            </div>
          )}
        </div>
      </div>

      {/* Critical Re-Entry Fraud Popup Modal */}
      {fraudModal && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-white border-2 border-rose-600 rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-4">
            <div className="w-14 h-14 rounded-full bg-rose-100 border border-rose-300 flex items-center justify-center text-rose-600 mx-auto">
              <ShieldAlert className="w-8 h-8" />
            </div>

            <div className="text-center space-y-2">
              <span className="bg-rose-600 text-white font-extrabold text-[10px] px-3 py-1 rounded-full uppercase tracking-wider">
                CRITICAL RE-ENTRY FRAUD DETECTED
              </span>
              <h3 className="text-xl font-extrabold text-slate-900">Counterfeit / Re-Entry Warning</h3>
              <p className="text-xs text-slate-600 leading-relaxed">{fraudModal.alert}</p>
            </div>

            <div className="bg-slate-50 border border-slate-200 rounded-xl p-3 text-xs space-y-1 font-mono">
              <div>
                <span className="text-slate-500">Scanned Batch:</span>{' '}
                <span className="font-bold text-slate-800">{fraudModal.batch?.batch_number}</span>
              </div>
              <div>
                <span className="text-slate-500">Batch Status:</span>{' '}
                <span className="font-bold text-rose-700">{fraudModal.batch?.current_status}</span>
              </div>
              <div>
                <span className="text-slate-500">Destruction Status:</span>{' '}
                <span className="font-bold text-rose-700">{fraudModal.batch?.destruction_status || 'N/A'}</span>
              </div>
            </div>

            <p className="text-[11px] text-slate-500 text-center">
              The Gemini Moderator AI and CDSCO Regulator have been automatically alerted.
              This batch must remain quarantined.
            </p>

            <button onClick={() => setFraudModal(null)} className="btn-danger w-full text-xs">
              Acknowledge & Close Modal
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

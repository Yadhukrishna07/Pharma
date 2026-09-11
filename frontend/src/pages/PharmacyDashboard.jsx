import React, { useState, useEffect, useRef } from 'react';
import { Pill, QrCode, ArrowUpRight, ShieldAlert, CheckCircle2, AlertTriangle, RefreshCw, Camera, Sparkles } from 'lucide-react';
import { dashboardAPI, batchAPI, returnAPI } from '../services/api';
import StatusBadge from '../components/StatusBadge';
import ProgressTracker from '../components/ProgressTracker';
import BarcodeScanner from '../components/BarcodeScanner';
import RecentActivityFeed from '../components/RecentActivityFeed';
import ModeratorInsightCard from '../components/ModeratorInsightCard';
import EvidenceCapture from '../components/EvidenceCapture';

export default function PharmacyDashboard() {
  const [data, setData] = useState(null);
  const [scanInput, setScanInput] = useState('BATCH-001');
  const [scanResult, setScanResult] = useState(null);
  const [fraudModal, setFraudModal] = useState(null);
  const [loading, setLoading] = useState(false);
  const [actionMsg, setActionMsg] = useState(null);
  const [showScanner, setShowScanner] = useState(false);
  const [isPolling, setIsPolling] = useState(true);

  // Return request form
  const [returnQty, setReturnQty] = useState(100);
  const [distributorId, setDistributorId] = useState(3); // BlueDart

  useEffect(() => {
    fetchDashboard();

    // Live polling every 3.5 seconds while tab is active
    const interval = setInterval(() => {
      if (!document.hidden) {
        fetchDashboard(false);
      }
    }, 3500);

    return () => clearInterval(interval);
  }, []);

  const fetchDashboard = async (showLoadingState = false) => {
    if (showLoadingState) setLoading(true);
    try {
      const res = await dashboardAPI.getPharmacyDashboard();
      setData(res.data);
    } catch (e) {
      console.error('Error fetching pharmacy dashboard:', e);
    } finally {
      if (showLoadingState) setLoading(false);
    }
  };

  const executeBatchScan = async (batchNum) => {
    if (!batchNum) return;
    setLoading(true);
    setScanResult(null);

    try {
      const res = await batchAPI.scanBatch(
        batchNum,
        data?.organization_name || 'MedPlus Central Indiranagar',
        'PHARMACY'
      );
      setScanResult(res.data);

      if (res.data.fraud_detected) {
        setFraudModal(res.data);
      }
      fetchDashboard(false);
    } catch (err) {
      setScanResult({
        error: true,
        message: err.response?.data?.detail || 'Scan failed. Batch not found or server unavailable.',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleScan = (e) => {
    e.preventDefault();
    executeBatchScan(scanInput);
  };

  const handleBarcodeDetected = (rawBarcode) => {
    let cleaned = rawBarcode ? rawBarcode.trim() : '';
    if (cleaned.includes('BATCH-001')) cleaned = 'BATCH-001';
    setScanInput(cleaned);
    setShowScanner(false);
    executeBatchScan(cleaned);
  };

  const handleTriggerReturn = async (e) => {
    e.preventDefault();
    if (!data?.batch) return;
    setLoading(true);
    setActionMsg(null);

    try {
      const res = await returnAPI.createReturnRequest({
        batch_id: Number(data.batch.id),
        declared_quantity: Number(returnQty),
        distributor_id: Number(distributorId),
      });
      setActionMsg({
        type: 'success',
        text: `Reverse chain return created! Request ID: #${res.data.id}. BlueDart Logistics notified for pickup.`,
      });
      fetchDashboard(false);
    } catch (err) {
      setActionMsg({
        type: 'error',
        text: err.response?.data?.detail || 'Failed to trigger return request.',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleReset = async (mode) => {
    try {
      setLoading(true);
      await dashboardAPI.resetDashboard(mode);
      await fetchDashboard(false);
      setActionMsg({
        type: 'success',
        text: `Demo reset to ${mode.toUpperCase()} mode!`,
      });
    } catch (e) {
      setActionMsg({ type: 'error', text: 'Reset failed' });
    } finally {
      setLoading(false);
    }
  };

  const batch = data?.batch;
  const currentStatus = batch?.current_status || 'EXPIRED';

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">Pharmacy Operations Portal</h1>
            <span className="inline-flex items-center gap-1 bg-emerald-50 text-emerald-700 text-[10px] font-bold px-2 py-0.5 rounded-full border border-emerald-200">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
              LIVE POLLING
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Logged in as <span className="font-bold text-slate-700">{data?.organization_name || 'MedPlus Central Indiranagar'}</span>
          </p>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <button
            onClick={() => handleReset('fresh')}
            className="btn-secondary text-[11px] py-1.5 px-2.5 text-slate-600 hover:text-blue-800"
            title="Reset BATCH-001 to initial EXPIRED state for live walkthrough"
          >
            Reset (Fresh)
          </button>
          <button
            onClick={() => handleReset('history')}
            className="btn-secondary text-[11px] py-1.5 px-2.5 text-purple-700 hover:bg-purple-50"
            title="Populate full Day 1-11 realistic operational history"
          >
            Load Day 1–11 Demo
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
          {actionMsg.type === 'success' ? (
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
          ) : (
            <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0" />
          )}
          <span>{actionMsg.text}</span>
        </div>
      )}

      {/* Primary Batch Card */}
      {batch && (
        <div className="enterprise-card bg-gradient-to-r from-blue-900 to-slate-900 text-white p-6 rounded-2xl shadow-md border-0 space-y-6">
          <div className="flex items-start justify-between flex-wrap gap-4">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-xl bg-blue-800/80 border border-blue-700 flex items-center justify-center text-blue-300">
                <Pill className="w-6 h-6" />
              </div>
              <div>
                <span className="text-xs font-mono text-blue-300 uppercase tracking-wider">
                  Target Batch Monitor
                </span>
                <h2 className="text-xl font-extrabold text-white">
                  {batch.batch_number} — {batch.medicine_name}
                </h2>
              </div>
            </div>
            <StatusBadge status={batch.current_status} />
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-5 gap-4 pt-4 border-t border-slate-800 text-xs">
            <div>
              <span className="text-slate-400 block text-[10px] font-mono">BATCH ID</span>
              <span className="font-bold text-white font-mono">{batch.batch_number}</span>
            </div>
            <div>
              <span className="text-slate-400 block text-[10px] font-mono">QUANTITY</span>
              <span className="font-bold text-white">{batch.quantity} Packs</span>
            </div>
            <div>
              <span className="text-slate-400 block text-[10px] font-mono">EXPIRY DATE</span>
              <span className="font-bold text-amber-300">{batch.expiry_date}</span>
            </div>
            <div>
              <span className="text-slate-400 block text-[10px] font-mono">CURRENT LOCATION</span>
              <span className="font-bold text-slate-200 truncate block">{batch.current_location}</span>
            </div>
            <div>
              <span className="text-slate-400 block text-[10px] font-mono">RETURN STATUS</span>
              <span className="font-bold text-sky-300 font-mono">{data.return_status}</span>
            </div>
          </div>

          {/* Derived Next Action Banner */}
          <div className="bg-blue-950/60 border border-blue-800/60 rounded-xl p-3 text-xs flex items-center gap-2.5">
            <span className="bg-blue-600 text-white text-[10px] font-extrabold px-2 py-0.5 rounded uppercase tracking-wider shrink-0">
              NEXT ACTION
            </span>
            <span className="text-blue-100 font-medium">{data.next_action}</span>
          </div>

          {/* Progress Tracker */}
          <div className="pt-2 border-t border-slate-800">
            <ProgressTracker currentStatus={batch.current_status} />
          </div>
        </div>
      )}

      {/* Grid: Barcode Scanner & Return Initiation Form */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Scanner Card */}
        <div className="enterprise-card space-y-4">
          <div className="flex items-center gap-2 border-b border-slate-100 pb-3">
            <QrCode className="w-5 h-5 text-blue-800" />
            <div>
              <h3 className="font-bold text-slate-900 text-base">Barcode / RFID Batch Scanner</h3>
              <p className="text-[11px] text-slate-500">Scan batch verification on intake or shelf check</p>
            </div>
          </div>

          <form onSubmit={handleScan} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Batch ID</label>
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

          {/* Camera Scanner Button */}
          <div className="pt-2 border-t border-slate-100 flex items-center justify-between">
            <button
              type="button"
              onClick={() => setShowScanner(!showScanner)}
              className="btn-secondary text-xs flex items-center gap-2"
            >
              <Camera className="w-4 h-4 text-blue-800" />
              <span>{showScanner ? 'Close Camera' : '📷 Scan Barcode'}</span>
            </button>
          </div>

          {showScanner && (
            <BarcodeScanner
              onScanSuccess={handleBarcodeDetected}
              onClose={() => setShowScanner(false)}
            />
          )}

          {/* Scan Results */}
          {scanResult && (
            <div className="space-y-3 pt-2">
              {scanResult.error ? (
                <div className="p-4 rounded-xl border border-rose-200 bg-rose-50 text-rose-900 text-xs">
                  <div className="font-bold flex items-center gap-1.5 mb-1 text-rose-800">
                    <AlertTriangle className="w-4 h-4" />
                    <span>Scan Error</span>
                  </div>
                  <p>{scanResult.message}</p>
                </div>
              ) : scanResult.fraud_detected ? (
                <div className="p-4 rounded-xl border-2 border-rose-400 bg-rose-50 text-rose-950 text-xs leading-relaxed space-y-2">
                  <div className="font-extrabold flex items-center gap-1.5 text-rose-700">
                    <ShieldAlert className="w-5 h-5 text-rose-600 shrink-0" />
                    <span>CRITICAL RE-ENTRY FRAUD DETECTED</span>
                  </div>
                  <p className="font-medium">{scanResult.alert || scanResult.message}</p>
                  <div className="text-[11px] font-mono text-rose-800 bg-white/80 p-2 rounded border border-rose-200">
                    Status: {scanResult.batch?.current_status} • Destruction: {scanResult.batch?.destruction_status || 'DESTROYED'}
                  </div>
                </div>
              ) : (
                <div className="p-4 rounded-xl border border-slate-200 bg-slate-50 text-slate-800 text-xs space-y-2">
                  <div className="flex items-center justify-between border-b border-slate-200 pb-2">
                    <div className="flex items-center gap-1.5 text-emerald-700 font-bold">
                      <CheckCircle2 className="w-4 h-4" />
                      <span>Legitimate Batch Scanned</span>
                    </div>
                    <StatusBadge status={scanResult.batch?.current_status} />
                  </div>
                  <div className="grid grid-cols-2 gap-2 font-mono text-[11px]">
                    <div>Batch: <span className="font-bold">{scanResult.batch?.batch_number}</span></div>
                    <div>Quantity: <span className="font-bold">{scanResult.batch?.quantity}</span></div>
                    <div className="col-span-2">Location: <span className="font-bold">{scanResult.batch?.current_location}</span></div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Return Initiation Card */}
        <div className="enterprise-card space-y-4">
          <div className="flex items-center gap-2 border-b border-slate-100 pb-3">
            <ArrowUpRight className="w-5 h-5 text-blue-800" />
            <div>
              <h3 className="font-bold text-slate-900 text-base">Initiate Reverse Chain Return</h3>
              <p className="text-[11px] text-slate-500">Dispatch expired inventory to BlueDart Logistics</p>
            </div>
          </div>

          <form onSubmit={handleTriggerReturn} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Target Batch</label>
              <input
                type="text"
                disabled
                className="input-field bg-slate-100 text-xs font-mono"
                value={`${batch?.batch_number || 'BATCH-001'} — Augmentin Duo 625mg (${batch?.quantity || 100} packs)`}
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Declared Quantity (Packs)</label>
              <input
                type="number"
                className="input-field text-xs font-mono"
                value={returnQty}
                onChange={(e) => setReturnQty(e.target.value)}
                min="1"
                max={batch?.quantity || 100}
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Designated Logistics Partner</label>
              <select
                className="input-field text-xs"
                value={distributorId}
                onChange={(e) => setDistributorId(e.target.value)}
              >
                <option value={3}>BlueDart Pharma Logistics</option>
              </select>
            </div>

            <button
              type="submit"
              disabled={loading || currentStatus !== 'EXPIRED'}
              className="btn-primary w-full text-xs"
            >
              {loading
                ? 'Submitting...'
                : currentStatus === 'EXPIRED'
                ? 'Submit Reverse Chain Return Request'
                : `Return Request Already Submitted [${currentStatus}]`}
            </button>
          </form>
        </div>
      </div>

      {/* Evidence Capture & AI Moderator Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <EvidenceCapture
          batchNumber={batch?.batch_number || 'PCM-2026-00124'}
          organizationName={data?.organization_name}
        />
        <ModeratorInsightCard insight={data?.moderator_insight} />
      </div>

      {/* Recent Activity Feed */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <RecentActivityFeed events={data?.recent_activity} title="Recent Activity (BATCH-001)" />
      </div>

      {/* Critical Re-Entry Fraud Modal */}
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
              The CDSCO Regulator and Gemini Compliance Moderator have been notified. Quarantine this package immediately.
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

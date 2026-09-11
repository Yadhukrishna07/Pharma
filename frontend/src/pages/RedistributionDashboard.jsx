import React, { useState, useEffect } from 'react';
import {
  TrendingUp,
  AlertTriangle,
  ArrowRight,
  RefreshCw,
  Sparkles,
  ShieldCheck,
  CheckCircle2,
  Package,
  Clock,
  Zap,
  Building2,
  Layers,
} from 'lucide-react';
import { reallocationAPI } from '../services/api';

const URGENCY_BADGES = {
  CRITICAL: 'bg-rose-600 text-white border-rose-500',
  HIGH: 'bg-amber-500 text-white border-amber-400',
  MEDIUM: 'bg-yellow-500 text-slate-900 border-yellow-400',
  LOW: 'bg-blue-600 text-white border-blue-500',
};

export default function RedistributionDashboard() {
  const [data, setData] = useState(null);
  const [rawData, setRawData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [approvedTransfers, setApprovedTransfers] = useState({});
  const [activeTab, setActiveTab] = useState('recommendations'); // 'recommendations' | 'demand' | 'surplus'

  useEffect(() => {
    fetchReallocationData();
  }, []);

  const fetchReallocationData = async () => {
    setLoading(true);
    try {
      const [recRes, rawRes] = await Promise.all([
        reallocationAPI.getRecommendations(),
        reallocationAPI.getRawData(),
      ]);
      setData(recRes.data);
      setRawData(rawRes.data);
    } catch (err) {
      console.error('Failed to fetch reallocation data:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = (recId) => {
    setApprovedTransfers((prev) => ({ ...prev, [recId]: true }));
  };

  const recommendations = data?.recommendations || [];
  const totalValueSaved = recommendations.reduce(
    (acc, r) => acc + (r.estimated_waste_saved_value || 0),
    0
  );

  return (
    <div className="max-w-7xl mx-auto space-y-8">
      {/* ── Page Header ─────────────────────────────────────────── */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-gradient-to-r from-slate-900 via-slate-800 to-blue-950 text-white p-6 rounded-2xl shadow-xl border border-slate-700">
        <div className="space-y-1.5">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-500/20 border border-blue-400/30 text-blue-300 text-xs font-semibold">
            <Sparkles className="w-3.5 h-3.5 text-blue-400" />
            Gemini AI Optimization Engine
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight">
            Smart Supply-Demand Redistribution
          </h1>
          <p className="text-xs text-slate-300 max-w-2xl leading-relaxed">
            Prevents drug expiry returns by reallocating near-expiry surplus stock from low-velocity locations to pharmacies experiencing high sales demand.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={fetchReallocationData}
            disabled={loading}
            className="px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-600 text-xs font-semibold flex items-center gap-2 transition-all shadow-sm disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Re-Analyze</span>
          </button>
        </div>
      </div>

      {/* ── Metric Cards ────────────────────────────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <div className="enterprise-card flex items-center justify-between">
          <div>
            <div className="text-2xl font-black text-slate-900">{data?.demand_count ?? 0}</div>
            <div className="text-xs font-medium text-slate-500">Stock-out Risk Bottlenecks</div>
          </div>
          <div className="w-11 h-11 rounded-xl bg-rose-50 border border-rose-200 flex items-center justify-center text-rose-600">
            <AlertTriangle className="w-5 h-5" />
          </div>
        </div>

        <div className="enterprise-card flex items-center justify-between">
          <div>
            <div className="text-2xl font-black text-slate-900">{data?.surplus_count ?? 0}</div>
            <div className="text-xs font-medium text-slate-500">Near-Expiry Surplus Batches</div>
          </div>
          <div className="w-11 h-11 rounded-xl bg-amber-50 border border-amber-200 flex items-center justify-center text-amber-600">
            <Clock className="w-5 h-5" />
          </div>
        </div>

        <div className="enterprise-card flex items-center justify-between">
          <div>
            <div className="text-2xl font-black text-blue-700">{recommendations.length}</div>
            <div className="text-xs font-medium text-slate-500">Transfer Proposals</div>
          </div>
          <div className="w-11 h-11 rounded-xl bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-700">
            <Zap className="w-5 h-5" />
          </div>
        </div>

        <div className="enterprise-card flex items-center justify-between">
          <div>
            <div className="text-2xl font-black text-emerald-700">
              ₹{totalValueSaved.toLocaleString('en-IN')}
            </div>
            <div className="text-xs font-medium text-slate-500">Estimated Waste Value Saved</div>
          </div>
          <div className="w-11 h-11 rounded-xl bg-emerald-50 border border-emerald-200 flex items-center justify-center text-emerald-600">
            <TrendingUp className="w-5 h-5" />
          </div>
        </div>
      </div>

      {/* ── Engine Banner ───────────────────────────────────────── */}
      <div className="flex items-center justify-between bg-slate-900 text-slate-200 px-5 py-3.5 rounded-xl border border-slate-800 text-xs">
        <div className="flex items-center gap-3">
          <div className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse" />
          <span className="font-mono font-semibold text-slate-300">
            ENGINE STATUS: {data?.mode === 'GEMINI_AI' ? 'GEMINI 3.6 FLASH (OPTIMIZER ONLINE)' : 'DETERMINISTIC RULE-BASED FALLBACK'}
          </span>
        </div>
        <span className="text-[11px] font-mono text-slate-400">
          {data?.summary || 'Analyzing supply & demand imbalances across pharmacy networks...'}
        </span>
      </div>

      {/* ── Main Navigation Tabs ─────────────────────────────────── */}
      <div className="flex border-b border-slate-200 gap-6 text-sm font-semibold">
        <button
          onClick={() => setActiveTab('recommendations')}
          className={`pb-3 transition-colors flex items-center gap-2 border-b-2 ${
            activeTab === 'recommendations'
              ? 'border-blue-700 text-blue-700'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Zap className="w-4 h-4" />
          Transfer Recommendations ({recommendations.length})
        </button>
        <button
          onClick={() => setActiveTab('demand')}
          className={`pb-3 transition-colors flex items-center gap-2 border-b-2 ${
            activeTab === 'demand'
              ? 'border-blue-700 text-blue-700'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <TrendingUp className="w-4 h-4" />
          Demand Bottlenecks ({rawData?.demand_data?.length || 0})
        </button>
        <button
          onClick={() => setActiveTab('surplus')}
          className={`pb-3 transition-colors flex items-center gap-2 border-b-2 ${
            activeTab === 'surplus'
              ? 'border-blue-700 text-blue-700'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Package className="w-4 h-4" />
          Surplus Near-Expiry Batches ({rawData?.surplus_data?.length || 0})
        </button>
      </div>

      {/* ── TAB 1: Transfer Recommendations ─────────────────────── */}
      {activeTab === 'recommendations' && (
        <div className="space-y-4">
          {loading ? (
            <div className="py-16 text-center text-slate-400 space-y-3">
              <RefreshCw className="w-8 h-8 animate-spin mx-auto text-blue-700" />
              <p className="text-xs font-semibold">Evaluating inventory velocity and match algorithms...</p>
            </div>
          ) : recommendations.length === 0 ? (
            <div className="enterprise-card py-12 text-center text-slate-500 space-y-2">
              <CheckCircle2 className="w-10 h-10 text-emerald-500 mx-auto" />
              <p className="font-bold text-slate-800 text-sm">Inventory Balanced</p>
              <p className="text-xs">No critical supply-demand mismatches require inter-pharmacy transfer right now.</p>
            </div>
          ) : (
            recommendations.map((rec) => {
              const isApproved = approvedTransfers[rec.id];
              return (
                <div
                  key={rec.id}
                  className="enterprise-card space-y-4 border-slate-200 hover:border-blue-300 transition-all shadow-sm hover:shadow-md"
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-3">
                    <div className="flex items-center gap-3">
                      <span className={`px-2.5 py-1 rounded-md text-[10px] font-black uppercase border ${URGENCY_BADGES[rec.urgency] || URGENCY_BADGES.MEDIUM}`}>
                        {rec.urgency} URGENCY
                      </span>
                      <h3 className="font-bold text-base text-slate-900 flex items-center gap-2">
                        {rec.medicine_name}
                        <span className="text-xs font-mono font-medium text-slate-400 bg-slate-100 px-2 py-0.5 rounded-md">
                          {rec.batch_number}
                        </span>
                      </h3>
                    </div>

                    <div className="text-xs font-semibold text-emerald-700 bg-emerald-50 px-3 py-1 rounded-full border border-emerald-200 self-start sm:self-auto">
                      Est. Value Saved: ₹{rec.estimated_waste_saved_value?.toLocaleString('en-IN')}
                    </div>
                  </div>

                  {/* Flow Route */}
                  <div className="grid grid-cols-1 md:grid-cols-11 gap-3 items-center bg-slate-50 p-4 rounded-xl border border-slate-200/80">
                    <div className="md:col-span-5 space-y-1">
                      <span className="text-[10px] font-bold text-amber-700 uppercase tracking-wider block">
                        Source (Surplus / Near-Expiry)
                      </span>
                      <div className="font-bold text-slate-800 text-sm flex items-center gap-1.5">
                        <Building2 className="w-4 h-4 text-amber-600 shrink-0" />
                        {rec.source_pharmacy}
                      </div>
                      <div className="text-xs text-slate-500 font-mono">
                        Expires in <span className="font-bold text-amber-600">{rec.days_to_expiry} days</span>
                      </div>
                    </div>

                    <div className="md:col-span-1 flex items-center justify-center py-2 md:py-0">
                      <div className="w-9 h-9 rounded-full bg-blue-100 text-blue-700 border border-blue-200 flex items-center justify-center shadow-sm">
                        <ArrowRight className="w-4 h-4" />
                      </div>
                    </div>

                    <div className="md:col-span-5 space-y-1">
                      <span className="text-[10px] font-bold text-rose-700 uppercase tracking-wider block">
                        Destination (Fast-Selling / Low-Stock)
                      </span>
                      <div className="font-bold text-slate-800 text-sm flex items-center gap-1.5">
                        <Building2 className="w-4 h-4 text-rose-600 shrink-0" />
                        {rec.target_pharmacy}
                      </div>
                      <div className="text-xs text-slate-500 font-mono">
                        Transfer Quantity: <span className="font-extrabold text-blue-800">{rec.quantity_to_transfer} units</span>
                      </div>
                    </div>
                  </div>

                  {/* Reasoning & Actions */}
                  <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pt-1">
                    <p className="text-xs text-slate-600 italic bg-slate-50 p-3 rounded-lg border border-slate-200 flex-1 leading-relaxed">
                      "{rec.reasoning}"
                    </p>

                    <button
                      onClick={() => handleApprove(rec.id)}
                      disabled={isApproved}
                      className={`px-5 py-2.5 rounded-xl font-bold text-xs flex items-center gap-2 shrink-0 transition-all ${
                        isApproved
                          ? 'bg-emerald-100 text-emerald-800 border border-emerald-300 cursor-default'
                          : 'bg-blue-800 hover:bg-blue-900 text-white shadow-sm'
                      }`}
                    >
                      {isApproved ? (
                        <>
                          <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                          <span>Reallocation Initiated</span>
                        </>
                      ) : (
                        <>
                          <Zap className="w-4 h-4" />
                          <span>Approve Reallocation Transfer</span>
                        </>
                      )}
                    </button>
                  </div>
                </div>
              );
            })
          )}
        </div>
      )}

      {/* ── TAB 2: Demand Bottlenecks ───────────────────────────── */}
      {activeTab === 'demand' && (
        <div className="enterprise-card p-0 overflow-hidden">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-100 border-b border-slate-200 text-slate-600 font-bold uppercase tracking-wider text-[10px]">
              <tr>
                <th className="p-4">Pharmacy Location</th>
                <th className="p-4">Medicine Name</th>
                <th className="p-4">Current Stock</th>
                <th className="p-4">Daily Sales Velocity</th>
                <th className="p-4">Days Stock Remaining</th>
                <th className="p-4">Risk Level</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-slate-700 font-medium">
              {rawData?.demand_data?.map((d, idx) => (
                <tr key={idx} className="hover:bg-slate-50">
                  <td className="p-4 font-bold text-slate-900">{d.pharmacy_name}</td>
                  <td className="p-4">{d.medicine_name}</td>
                  <td className="p-4 font-mono font-bold text-slate-800">{d.current_stock} units</td>
                  <td className="p-4 font-mono text-slate-600">{d.daily_sales_rate} units/day</td>
                  <td className="p-4 font-mono font-extrabold text-rose-600">{d.days_of_stock} days</td>
                  <td className="p-4">
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-100 text-rose-800 border border-rose-200">
                      HIGH STOCK-OUT RISK
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* ── TAB 3: Surplus Near-Expiry Batches ──────────────────── */}
      {activeTab === 'surplus' && (
        <div className="enterprise-card p-0 overflow-hidden">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-100 border-b border-slate-200 text-slate-600 font-bold uppercase tracking-wider text-[10px]">
              <tr>
                <th className="p-4">Holding Pharmacy</th>
                <th className="p-4">Batch Number</th>
                <th className="p-4">Medicine</th>
                <th className="p-4">Surplus Qty</th>
                <th className="p-4">Expiry Date</th>
                <th className="p-4">Days to Expiry</th>
                <th className="p-4">Unit MRP</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-slate-700 font-medium">
              {rawData?.surplus_data?.map((s, idx) => (
                <tr key={idx} className="hover:bg-slate-50">
                  <td className="p-4 font-bold text-slate-900">{s.pharmacy_name}</td>
                  <td className="p-4 font-mono text-blue-700 font-bold">{s.batch_number}</td>
                  <td className="p-4">{s.medicine_name}</td>
                  <td className="p-4 font-mono font-bold text-slate-800">{s.quantity} units</td>
                  <td className="p-4 font-mono text-slate-600">{s.expiry_date}</td>
                  <td className="p-4 font-mono font-extrabold text-amber-600">{s.days_to_expiry} days</td>
                  <td className="p-4 font-mono text-slate-700">₹{s.mrp}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

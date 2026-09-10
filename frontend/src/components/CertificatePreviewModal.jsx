import React from 'react';
import { Award, ShieldCheck, Printer, X, FileText, CheckCircle2, Building2 } from 'lucide-react';

export default function CertificatePreviewModal({ certificate, batch, onClose }) {
  if (!certificate) return null;

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="fixed inset-0 bg-slate-950/75 backdrop-blur-md flex items-center justify-center p-4 z-50 overflow-y-auto">
      <div className="bg-white border-2 border-slate-300 rounded-3xl max-w-2xl w-full p-8 shadow-2xl space-y-6 relative my-8 print:shadow-none print:border-0 print:m-0 print:p-4">
        {/* Close & Print Buttons */}
        <div className="flex justify-between items-center border-b border-slate-200 pb-4 print:hidden">
          <div className="flex items-center gap-2 text-xs font-bold text-slate-500 uppercase tracking-wider">
            <FileText className="w-4 h-4 text-blue-700" />
            Official Compliance Certificate Preview
          </div>
          <div className="flex items-center gap-2">
            <button onClick={handlePrint} className="btn-secondary text-xs py-1.5 px-3">
              <Printer className="w-4 h-4" /> Print / Save PDF
            </button>
            <button
              onClick={onClose}
              className="p-1.5 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Certificate Document Content */}
        <div className="border-4 border-double border-slate-800 p-8 rounded-xl bg-gradient-to-b from-amber-50/30 via-white to-amber-50/20 text-slate-900 space-y-6 relative overflow-hidden">
          {/* Background Watermark Seal */}
          <div className="absolute inset-0 flex items-center justify-center opacity-[0.03] pointer-events-none">
            <Award className="w-96 h-96 text-slate-900" />
          </div>

          {/* Document Header */}
          <div className="text-center space-y-2 border-b-2 border-slate-800 pb-4">
            <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-blue-900 text-white mb-1 shadow-md">
              <Award className="w-7 h-7" />
            </div>
            <h2 className="text-xl font-serif font-extrabold uppercase tracking-wider text-slate-900">
              Certificate of High-Temperature Destruction
            </h2>
            <p className="text-[11px] font-mono text-slate-600 uppercase tracking-widest">
              Biomedical Waste Incineration & Disposal Compliance • Form C-4
            </p>
          </div>

          {/* Certificate Metadata Bar */}
          <div className="grid grid-cols-2 gap-4 text-xs font-mono bg-slate-100/80 p-3 rounded-lg border border-slate-300">
            <div>
              <span className="text-slate-500 block text-[10px]">CERTIFICATE NUMBER</span>
              <span className="font-extrabold text-blue-900 text-sm">{certificate.certificate_number}</span>
            </div>
            <div>
              <span className="text-slate-500 block text-[10px]">ISSUED DATE</span>
              <span className="font-bold text-slate-800">{certificate.issued_date}</span>
            </div>
          </div>

          {/* Certificate Body Paragraph */}
          <p className="text-xs text-slate-700 leading-relaxed text-justify">
            This is to officially certify that the pharmaceutical batch detailed below has been received,
            verified, and destroyed via high-temperature controlled thermal incineration in compliance with
            national biomedical waste management regulations and CDSCO reverse supply chain safety guidelines.
          </p>

          {/* Batch Details Table */}
          <div className="border border-slate-300 rounded-lg overflow-hidden text-xs">
            <div className="bg-slate-800 text-white font-mono font-bold p-2 text-[11px] uppercase tracking-wider">
              Verified Batch Specifications
            </div>
            <div className="divide-y divide-slate-200 font-sans">
              <div className="p-2.5 flex justify-between">
                <span className="text-slate-600 font-medium">Batch Serial ID:</span>
                <span className="font-mono font-bold text-slate-900">{batch?.batch_number || 'BATCH-001'}</span>
              </div>
              <div className="p-2.5 flex justify-between bg-slate-50/60">
                <span className="text-slate-600 font-medium">Medicine Name:</span>
                <span className="font-bold text-slate-900">{batch?.medicine_name || 'Augmentin Duo 625mg'}</span>
              </div>
              <div className="p-2.5 flex justify-between">
                <span className="text-slate-600 font-medium">Certified Destroyed Quantity:</span>
                <span className="font-mono font-extrabold text-emerald-800">{certificate.quantity} Packs</span>
              </div>
              <div className="p-2.5 flex justify-between bg-slate-50/60">
                <span className="text-slate-600 font-medium">Incineration Facility:</span>
                <span className="font-bold text-slate-900">BioClean Biomedical Waste Facility</span>
              </div>
            </div>
          </div>

          {/* Signatures & Seal Section */}
          <div className="pt-6 border-t-2 border-slate-800 grid grid-cols-2 gap-8 items-end text-xs">
            <div className="space-y-1">
              <div className="font-serif italic text-slate-700 text-sm border-b border-slate-400 pb-1">
                Dr. R. K. Sharma, Compliance Lead
              </div>
              <span className="text-[10px] text-slate-500 font-mono block">Authorized Facility Director</span>
              <span className="text-[9px] text-slate-400 font-mono block">BioClean Bio-Waste Solutions</span>
            </div>

            <div className="text-right space-y-2">
              <div className="inline-flex items-center gap-1.5 bg-emerald-50 border border-emerald-300 text-emerald-800 text-[10px] font-bold px-3 py-1 rounded-full">
                <ShieldCheck className="w-4 h-4 text-emerald-600" />
                {certificate.is_verified ? 'CDSCO REGULATOR VERIFIED' : 'PENDING REGULATORY SIGNATURE'}
              </div>
              <div className="text-[9px] text-slate-400 font-mono">
                SHA-256 Hash Verification Linked
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

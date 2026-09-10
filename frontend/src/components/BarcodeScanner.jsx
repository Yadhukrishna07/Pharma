import React, { useEffect, useRef, useState } from 'react';
import { Html5Qrcode, Html5QrcodeSupportedFormats } from 'html5-qrcode';
import { Camera, X, AlertTriangle, LoaderCircle, ScanLine } from 'lucide-react';

export default function BarcodeScanner({ onScanSuccess, onClose }) {
  const [scannerState, setScannerState] = useState('starting'); // 'starting' | 'scanning' | 'error'
  const [errorMessage, setErrorMessage] = useState('');
  const html5QrcodeInstanceRef = useRef(null);
  const isStoppingRef = useRef(false);

  useEffect(() => {
    let isMounted = true;
    const elementId = "html5qr-code-full-region";

    const stopActiveCamera = async () => {
      if (html5QrcodeInstanceRef.current && !isStoppingRef.current) {
        isStoppingRef.current = true;
        try {
          if (html5QrcodeInstanceRef.current.isScanning) {
            await html5QrcodeInstanceRef.current.stop();
          }
          html5QrcodeInstanceRef.current.clear();
        } catch (err) {
          console.warn("Camera cleanup warning:", err);
        } finally {
          html5QrcodeInstanceRef.current = null;
          isStoppingRef.current = false;
        }
      }
    };

    const startCamera = async () => {
      try {
        setScannerState('starting');
        setErrorMessage('');

        const html5Qrcode = new Html5Qrcode(elementId);
        html5QrcodeInstanceRef.current = html5Qrcode;

        const formatsToSupport = [
          Html5QrcodeSupportedFormats.CODE_128,
          Html5QrcodeSupportedFormats.CODE_39,
          Html5QrcodeSupportedFormats.EAN_13,
          Html5QrcodeSupportedFormats.EAN_8,
          Html5QrcodeSupportedFormats.UPC_A,
          Html5QrcodeSupportedFormats.UPC_E,
          Html5QrcodeSupportedFormats.QR_CODE,
        ];

        const config = {
          fps: 10,
          qrbox: { width: 260, height: 160 },
          formatsToSupport: formatsToSupport,
        };

        const onCodeDetected = async (decodedText) => {
          if (!isMounted) return;
          // Immediately stop camera upon detection
          await stopActiveCamera();
          if (onScanSuccess) {
            onScanSuccess(decodedText);
          }
        };

        const cameras = await Html5Qrcode.getCameras().catch((e) => {
          console.warn("getCameras exception:", e);
          return [];
        });

        if (!isMounted) return;

        if (cameras && cameras.length > 0) {
          // Prefer environment / rear / back camera
          const backCamera = cameras.find((c) =>
            /back|rear|environment|main/i.test(c.label)
          ) || cameras[0];

          await html5Qrcode.start(
            backCamera.id,
            config,
            onCodeDetected,
            () => {} // frame detection error callback (silent)
          );
        } else {
          // Fallback: request default environment camera facing mode
          await html5Qrcode.start(
            { facingMode: "environment" },
            config,
            onCodeDetected,
            () => {}
          );
        }

        if (isMounted) {
          setScannerState('scanning');
        }
      } catch (err) {
        if (!isMounted) return;
        console.error("Camera startup error:", err);
        setScannerState('error');

        const errString = String(err).toLowerCase();
        if (errString.includes('permission') || errString.includes('notallowederror')) {
          setErrorMessage("Camera permission was denied. Please allow camera access in your browser settings or enter the Batch ID manually.");
        } else if (errString.includes('notfounderror') || errString.includes('no camera') || errString.includes('requested device not found')) {
          setErrorMessage("No camera was detected on this device.");
        } else {
          setErrorMessage("Unable to access camera. Please ensure camera permissions are granted or enter the Batch ID manually.");
        }
      }
    };

    startCamera();

    return () => {
      isMounted = false;
      stopActiveCamera();
    };
  }, [onScanSuccess]);

  const handleStop = async () => {
    if (html5QrcodeInstanceRef.current && !isStoppingRef.current) {
      isStoppingRef.current = true;
      try {
        if (html5QrcodeInstanceRef.current.isScanning) {
          await html5QrcodeInstanceRef.current.stop();
        }
        html5QrcodeInstanceRef.current.clear();
      } catch (e) {
        console.warn("Stop scanner error:", e);
      } finally {
        html5QrcodeInstanceRef.current = null;
        isStoppingRef.current = false;
      }
    }
    if (onClose) onClose();
  };

  return (
    <div className="mt-4 border border-slate-200 bg-slate-50/80 rounded-xl p-4 space-y-3">
      <div className="flex items-center justify-between border-b border-slate-200 pb-2">
        <div className="flex items-center gap-2 font-bold text-slate-800 text-xs">
          <Camera className="w-4 h-4 text-blue-800" />
          <span>Camera Barcode Scanner</span>
        </div>
        <button
          type="button"
          onClick={handleStop}
          className="text-slate-400 hover:text-slate-600 p-1 rounded-lg hover:bg-slate-200 transition-colors"
          title="Close Scanner"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {scannerState === 'starting' && (
        <div className="flex flex-col items-center justify-center py-10 text-slate-600 space-y-2">
          <LoaderCircle className="w-6 h-6 animate-spin text-blue-800" />
          <p className="text-xs font-medium text-slate-700">Starting camera...</p>
        </div>
      )}

      {scannerState === 'error' && (
        <div className="p-3.5 bg-amber-50 border border-amber-200 rounded-xl text-amber-900 text-xs space-y-2">
          <div className="flex items-center gap-2 font-bold text-amber-800">
            <AlertTriangle className="w-4 h-4 shrink-0 text-amber-600" />
            <span>Camera Access Notice</span>
          </div>
          <p className="leading-relaxed">{errorMessage}</p>
        </div>
      )}

      <div className={`relative overflow-hidden rounded-xl bg-slate-900 shadow-inner ${scannerState === 'error' ? 'hidden' : ''}`}>
        <div id="html5qr-code-full-region" className="w-full min-h-[260px]"></div>
      </div>

      <div className="flex items-center justify-between pt-1">
        <div className="flex items-center gap-1.5 text-[11px] text-slate-500">
          <ScanLine className="w-3.5 h-3.5 text-blue-700" />
          <span>Point camera at a medicine barcode inside the scanning frame.</span>
        </div>
        <button
          type="button"
          onClick={handleStop}
          className="btn-secondary text-xs px-3 py-1.5 shrink-0"
        >
          Stop Camera
        </button>
      </div>
    </div>
  );
}

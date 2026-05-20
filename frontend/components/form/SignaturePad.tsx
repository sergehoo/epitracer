'use client';

import { useEffect, useRef, useState } from 'react';
import SignatureCanvas from 'react-signature-canvas';
import { Eraser } from 'lucide-react';

export function SignaturePad({
  value, onChange,
}: {
  value?: string;
  onChange: (dataUrl: string) => void;
}) {
  const ref = useRef<SignatureCanvas>(null);
  const [empty, setEmpty] = useState(true);

  useEffect(() => {
    if (value && ref.current && ref.current.isEmpty()) {
      ref.current.fromDataURL(value);
      setEmpty(false);
    }
  }, [value]);

  const handleEnd = () => {
    const c = ref.current;
    if (!c) return;
    const isEmpty = c.isEmpty();
    setEmpty(isEmpty);
    onChange(isEmpty ? '' : c.toDataURL('image/png'));
  };

  const clear = () => {
    ref.current?.clear();
    setEmpty(true);
    onChange('');
  };

  return (
    <div>
      <div className="signature-pad-wrapper">
        <SignatureCanvas
          ref={ref}
          penColor="#0f172a"
          canvasProps={{ className: 'w-full h-44 rounded-lg' }}
          onEnd={handleEnd}
        />
      </div>
      <div className="mt-2 flex items-center justify-between">
        <span className="text-xs text-slate-500">Signez à l'intérieur du cadre avec la souris ou le doigt.</span>
        <button type="button" onClick={clear} className="btn-ghost text-xs">
          <Eraser className="h-3.5 w-3.5" /> Effacer
        </button>
      </div>
      {empty && <p className="field-error mt-1">Signature obligatoire.</p>}
    </div>
  );
}

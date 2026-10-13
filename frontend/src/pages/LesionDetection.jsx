import { useEffect, useState } from 'react';
import { ArrowLeft, Download, LoaderCircle } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useAnalysis } from '../context/AnalysisContext';
import { detectLesions } from '../services/api';

const lesionMeta = {
  0: { label: 'Microaneurysm', color: '#dc2626' },
  1: { label: 'Haemorrhage', color: '#2563eb' },
  2: { label: 'Hard Exudate', color: '#16a34a' },
  3: { label: 'Soft Exudate', color: '#eab308' },
};

export default function LesionDetection() {
  const { uploadedImage, setLesionResult } = useAnalysis();
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (!uploadedImage) {
      return undefined;
    }

    let isCurrent = true;
    setIsLoading(true);
    setError('');
    detectLesions(uploadedImage)
      .then((response) => {
        if (isCurrent) {
          setResult(response.result);
          setLesionResult(response.result);
        }
      })
      .catch((requestError) => {
        if (isCurrent) setError(requestError.message || 'Lesion detection could not be completed.');
      })
      .finally(() => {
        if (isCurrent) setIsLoading(false);
      });

    return () => {
      isCurrent = false;
    };
  }, [uploadedImage, setLesionResult]);

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="mb-6 flex items-center justify-between gap-4">
        <div>
          <p className="section-label">Analysis</p>
          <h1 className="mt-2 text-3xl font-semibold text-slate-900">Lesion Detection</h1>
          <p className="mt-2 text-sm text-slate-600">YOLO26 retinal lesion detection</p>
        </div>
        <Link to="/home" className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-medium text-slate-700">
          <ArrowLeft className="h-4 w-4" aria-hidden="true" />
          Back to Dashboard
        </Link>
      </div>

      {!uploadedImage && (
        <div className="medical-card p-6 text-sm text-slate-600">Upload a fundus image from the dashboard before opening lesion detection.</div>
      )}
      {isLoading && (
        <div className="medical-card flex items-center gap-3 p-6 text-sm text-slate-600">
          <LoaderCircle className="h-5 w-5 animate-spin text-sky-600" aria-hidden="true" />
          Detecting retinal lesions...
        </div>
      )}
      {error && <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</div>}
      {result && (
        <div className="space-y-6">
          <section className="medical-card overflow-hidden p-4 sm:p-6">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="section-label">Detection result</p>
                <h2 className="mt-1 text-xl font-semibold text-slate-900">{result.total} lesions detected</h2>
              </div>
              <a href={result.download_url} download className="inline-flex items-center gap-2 rounded-xl bg-sky-600 px-4 py-2.5 text-sm font-medium text-white">
                <Download className="h-4 w-4" aria-hidden="true" />
                Download Result
              </a>
            </div>
            <img src={result.image_url} alt="Retinal lesion detection result" className="mt-5 max-h-[680px] w-full object-contain" />
          </section>

          <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {Object.entries(result.summary).map(([classId, values]) => (
              <div key={classId} className="medical-card p-5">
                <p className="flex items-center gap-2 text-sm text-slate-500"><span className="inline-block h-3 w-3 rounded-full ring-2 ring-white shadow-sm" style={{ backgroundColor: lesionMeta[classId].color }} aria-hidden="true" />{lesionMeta[classId].label}</p>
                <p className="mt-2 text-2xl font-semibold text-slate-900">{values.count}</p>
                <p className="mt-1 text-xs text-slate-500">Highest confidence: {(values.highest * 100).toFixed(1)}%</p>
              </div>
            ))}
          </section>
          <p className="text-sm leading-6 text-slate-500">These AI-generated results are intended for research and educational purposes only and should not be considered a medical diagnosis.</p>
        </div>
      )}
    </div>
  );
}

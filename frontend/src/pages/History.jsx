import { ArrowRight, FileClock, ScanLine } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAnalysis } from '../context/AnalysisContext';

export default function History() {
  const navigate = useNavigate();
  const { analysisHistory, historyError } = useAnalysis();

  return (
    <div className="mx-auto max-w-[1380px] px-4 py-8 sm:px-6 lg:px-8">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div><p className="section-label">Workspace</p><h1 className="mt-2 text-3xl font-bold tracking-tight text-[#0F2747]">Recent analyses</h1><p className="mt-2 max-w-xl text-sm leading-6 text-slate-500">Your uploaded fundus images, organized for quick review.</p></div>
        <button type="button" onClick={() => navigate('/home#upload-section')} className="primary-button"><ScanLine className="h-4 w-4" aria-hidden="true" /> Analyze an image</button>
      </div>
      {historyError && <p className="mt-6 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">{historyError}</p>}
      {analysisHistory.length ? <div className="mt-8 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-[0_12px_34px_rgba(15,39,71,0.06)]"><div className="hidden grid-cols-[1fr_180px_140px] gap-4 border-b border-slate-100 bg-slate-50 px-6 py-3 text-[11px] font-bold uppercase tracking-[0.14em] text-slate-400 sm:grid"><span>Image</span><span>Uploaded</span><span>Status</span></div>{analysisHistory.map((analysis) => <div key={analysis.id} className="grid gap-3 border-b border-slate-100 px-5 py-5 last:border-0 sm:grid-cols-[1fr_180px_140px] sm:items-center sm:px-6"><div className="flex items-center gap-3"><div className="flex h-10 w-10 items-center justify-center rounded-xl bg-sky-50 text-[#1677FF]"><FileClock className="h-5 w-5" aria-hidden="true" /></div><div><p className="truncate text-sm font-bold text-[#0F2747]">{analysis.image?.name || 'Retinal image'}</p><p className="mt-1 text-xs text-slate-400">{analysis.image?.type || 'Fundus image'}</p></div></div><time className="text-xs text-slate-500" dateTime={analysis.createdAt}>{new Date(analysis.createdAt).toLocaleString()}</time><span className="inline-flex w-fit items-center gap-1.5 rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-bold text-emerald-700"><span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />Saved</span></div>)}</div> : <div className="mt-8 rounded-2xl border border-dashed border-slate-300 bg-white px-6 py-14 text-center"><FileClock className="mx-auto h-10 w-10 text-slate-300" aria-hidden="true" /><h2 className="mt-4 text-lg font-bold text-[#0F2747]">No analyses yet</h2><p className="mx-auto mt-2 max-w-sm text-sm leading-6 text-slate-500">Upload a fundus image to begin your first AI-assisted analysis.</p><button type="button" onClick={() => navigate('/home#upload-section')} className="secondary-button mt-6">Analyze fundus image <ArrowRight className="h-4 w-4" aria-hidden="true" /></button></div>}
    </div>
  );
}

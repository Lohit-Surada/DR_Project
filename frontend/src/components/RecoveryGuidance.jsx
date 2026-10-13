import { AlertTriangle, BookOpen, CheckCircle2, LoaderCircle, Stethoscope } from 'lucide-react';
import { useAnalysis } from '../context/AnalysisContext';

export default function RecoveryGuidance({ classification }) {
  const isNoDr = classification?.label === 'No DR'
    || classification?.title === 'No diabetic retinopathy'
    || classification?.severity === 'No DR';
  const { guidanceResult: guidance, guidanceStatus, guidanceError } = useAnalysis();
  const isLoading = guidanceStatus === 'loading';

  if (isLoading) {
    return <section className="medical-card mt-6 flex items-center gap-3 p-6 text-sm text-slate-600"><LoaderCircle className="h-5 w-5 animate-spin text-[#1677FF]" aria-hidden="true" />Preparing educational care guidance...</section>;
  }

  if (isNoDr) {
    return <section className="medical-card mt-6 overflow-hidden"><div className="flex items-start gap-3 bg-emerald-50 p-6 sm:p-7"><div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-white text-emerald-600"><CheckCircle2 className="h-5 w-5" aria-hidden="true" /></div><div><p className="section-label text-emerald-700">Classification result</p><h2 className="mt-1 text-xl font-bold text-[#0F2747]">No recovery guidance required</h2><p className="mt-2 text-sm leading-6 text-slate-600">The AI-assisted classification did not identify diabetic retinopathy. Continue routine eye examinations and follow your healthcare professional's general prevention advice.</p></div></div></section>;
  }

  return (
    <section className="medical-card mt-6 overflow-hidden">
      <div className="border-b border-slate-100 bg-[#F8FBFE] px-5 py-5 sm:px-7"><div className="flex items-start gap-3"><div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-sky-50 text-[#1677FF]"><BookOpen className="h-5 w-5" aria-hidden="true" /></div><div><p className="section-label">Personalized education</p><h2 className="mt-1 text-xl font-bold text-[#0F2747]">Recovery & prevention priorities</h2><p className="mt-2 text-sm leading-6 text-slate-500">Three educational next steps based on the AI-assisted classification result.</p></div></div></div>
      {guidanceError ? <div className="m-5 flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm leading-6 text-amber-800"><AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />{guidanceError}</div> : guidance && <div className="p-5 sm:p-7"><ol className="space-y-4">{guidance.tips.map((tip, index) => <li key={tip} className="flex gap-3"><span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[#0F2747] text-xs font-bold text-white">{index + 1}</span><p className="text-sm leading-6 text-slate-700">{tip}</p></li>)}</ol><div className="mt-7 border-t border-slate-100 pt-6"><div className="flex items-center gap-2 text-sm font-bold text-[#0F2747]"><Stethoscope className="h-4 w-4 text-teal-600" aria-hidden="true" />Medicine names for clinician discussion</div><p className="mt-2 text-xs leading-5 text-slate-500">These are reference names used in ophthalmology care, not personalized recommendations. Only a qualified clinician can decide whether any treatment is appropriate.</p><div className="mt-4 grid gap-2 sm:grid-cols-3">{guidance.medications.slice(0, 3).map((medication) => <div key={medication.name} className="rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-xs"><span className="block font-semibold text-slate-700">{medication.name}</span><span className="mt-1 block text-slate-400">{medication.category}</span></div>)}</div></div><div className="mt-6 flex items-start gap-2 rounded-xl bg-emerald-50 p-3 text-xs leading-5 text-emerald-800"><CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />Educational information only. AI results do not diagnose, prescribe, or establish a cure.</div></div>}
    </section>
  );
}

import { ArrowRight, BrainCircuit, FileText, ImageUp, ScanLine, Sparkles } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const stages = [
  ['01', 'Fundus image', 'Upload a clear retinal photograph. The original file is retained for comparison with generated outputs.', ImageUp],
  ['02', 'DR classification', 'The trained CNN estimates one of five diabetic retinopathy severity categories from the image.', BrainCircuit],
  ['03', 'Lesion detection', 'The YOLO26 pipeline identifies visual patterns such as microaneurysms, haemorrhages, and exudates.', ScanLine],
  ['04', 'Explainable AI', 'Grad-CAM, retinal attention, and feature visualizations show model contributions without claiming a diagnosis.', Sparkles],
  ['05', 'Structured report', 'Review the combined findings and prepare a downloadable research-oriented PDF report.', FileText],
];

export default function HowItWorks() {
  const navigate = useNavigate();
  return <div className="mx-auto max-w-[1100px] px-4 py-8 sm:px-6 lg:px-8"><div className="max-w-2xl"><p className="section-label">Method overview</p><h1 className="mt-2 text-3xl font-bold tracking-tight text-[#0F2747] sm:text-4xl">How RetinalAI analyzes an image</h1><p className="mt-4 text-base leading-7 text-slate-600">A transparent, multi-stage workflow for reviewing AI-assisted retinal findings.</p></div><div className="mt-10 space-y-4">{stages.map(([number, title, description, Icon]) => <article key={number} className="flex gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-[0_8px_24px_rgba(15,39,71,0.04)] sm:gap-6 sm:p-7"><span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[#0F2747] text-xs font-bold text-white">{number}</span><div className="flex-1"><div className="flex items-center gap-2"><Icon className="h-5 w-5 text-[#1677FF]" aria-hidden="true" /><h2 className="text-lg font-bold text-[#0F2747]">{title}</h2></div><p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">{description}</p></div></article>)}</div><div className="mt-10 rounded-2xl bg-[#EAF7F7] p-6 sm:p-8"><p className="text-sm font-bold text-[#0F2747]">Important context</p><p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">AI-generated results are intended for research and educational purposes only. Grad-CAM highlights model contribution; it does not independently confirm a lesion or establish a medical diagnosis.</p><button type="button" onClick={() => navigate('/home#upload-section')} className="primary-button mt-5">Upload a fundus image <ArrowRight className="h-4 w-4" aria-hidden="true" /></button></div></div>;
}

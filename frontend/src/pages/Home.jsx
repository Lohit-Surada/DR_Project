import { useState } from 'react';
import { ArrowRight, BarChart3, Check, FileText, History, ScanLine, ShieldCheck, Sparkles, UploadCloud } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import ReportDownload from '../components/ReportDownload';
import UploadRequiredModal from '../components/UploadRequiredModal';
import UploadSection from '../components/UploadSection';
import { useAnalysis } from '../context/AnalysisContext';
import { useAuth } from '../context/AuthContext';
import { createReport } from '../services/reportApi';
import { requireImageUpload } from '../utils/requireImageUpload';

const capabilities = [
  ['DR Classification', 'Assess diabetic retinopathy severity with the trained CNN model.', BarChart3, '/analysis/classification'],
  ['Lesion Detection', 'Identify microaneurysms, haemorrhages, hard and soft exudates.', ScanLine, '/analysis/lesions'],
  ['Explainable AI', 'See which retinal regions contributed to the model prediction.', Sparkles, '/analysis/gradcam'],
  ['Medical Report', 'Create a structured PDF with findings and visualizations.', FileText, null],
];
const workflow = [['01', 'Upload', 'Add a clear fundus image'], ['02', 'Classify', 'Estimate DR severity'], ['03', 'Detect', 'Locate retinal lesions'], ['04', 'Explain', 'Review model attention'], ['05', 'Report', 'Export your findings']];
const defaultHeroStorageKey = 'retinaiq-default-hero-image';

export default function Home() {
  const navigate = useNavigate();
  const { currentUser } = useAuth();
  const { uploadedImage, imagePreview, imageName, setImageFile, clearImage, classificationResult, lesionResult, guidanceResult, gradCamResults, gradCamCombined, gradCamStatus, analysisHistory, historyError } = useAnalysis();
  const [modalOpen, setModalOpen] = useState(false);
  const [modalFeature, setModalFeature] = useState('');
  const [uploadError, setUploadError] = useState('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const [savedHeroImage, setSavedHeroImage] = useState(() => window.localStorage.getItem(defaultHeroStorageKey) || '');
  const heroImage = imagePreview || savedHeroImage || '/fundus-hero.jpg';
  const reportReady = Boolean(uploadedImage && classificationResult && lesionResult && gradCamStatus === 'ready' && gradCamCombined && gradCamResults.length === 4);
  const focusUploadSection = () => document.getElementById('upload-section')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  const handleUploadImage = async (file) => {
    setUploadError('');
    setIsAnalyzing(true);
    try {
      const reader = new FileReader();
      reader.onload = () => {
        const dataUrl = String(reader.result || '');
        if (dataUrl) {
          try {
            window.localStorage.setItem(defaultHeroStorageKey, dataUrl);
            setSavedHeroImage(dataUrl);
          } catch {
            // Large uploads can exceed browser storage limits; analysis still continues.
          }
        }
      };
      reader.readAsDataURL(file);
      await setImageFile(file);
    } catch (error) { setUploadError(error.message || 'Unable to process this image. Please try again.'); } finally { setIsAnalyzing(false); }
  };
  const handleViewReport = async () => {
    if (!reportReady) { setUploadError('Complete the full retinal analysis before preparing a report.'); focusUploadSection(); return; }
    try { setIsDownloading(true); const report = await createReport({ image: uploadedImage, classification: classificationResult, lesions: lesionResult, guidance: guidanceResult, gradcam: { combined: gradCamCombined, panels: gradCamResults }, profile: currentUser }); navigate(`/report/${report.analysis_id}`); } catch (error) { setUploadError(error.message || 'Unable to prepare the medical report.'); } finally { setIsDownloading(false); }
  };
  const openCapability = (title, path) => {
    if (!path) { handleViewReport(); return; }
    requireImageUpload({ uploadedImage, featureName: title, onOpenModal: (featureName) => { setModalFeature(featureName); setModalOpen(true); }, navigate, path });
  };

  return (
    <div className="overflow-hidden">
      <div className="mx-auto max-w-[1380px] px-4 pb-14 pt-7 sm:px-6 lg:px-8">
        <section className="relative overflow-hidden rounded-2xl bg-[#0F2747] px-6 py-9 text-white shadow-[0_20px_50px_rgba(15,39,71,0.18)] sm:px-10 sm:py-12 lg:px-14 lg:py-14">
          <div className="pointer-events-none absolute -right-24 -top-24 h-72 w-72 rounded-full border border-white/10" aria-hidden="true" />
          <div className="relative grid items-center gap-10 lg:grid-cols-[1.1fr_0.9fr]">
            <div><span className="inline-flex items-center gap-2 text-[11px] font-bold uppercase tracking-[0.16em] text-teal-200"><span className="h-2 w-2 rounded-full bg-teal-300" />AI-powered retinal health platform</span><h1 className="mt-5 max-w-2xl text-4xl font-bold leading-[1.08] tracking-tight sm:text-5xl lg:text-[58px]">Diabetic Retinopathy<br /><span className="text-sky-300">Detection, Explained.</span></h1><p className="mt-5 max-w-xl text-base leading-7 text-slate-300 sm:text-lg">Analyze retinal fundus images with deep learning, lesion detection, and explainable AI in one focused workspace.</p><div className="mt-7 flex flex-col gap-3 sm:flex-row"><button type="button" onClick={focusUploadSection} className="primary-button bg-white text-[#0F2747] shadow-none hover:bg-sky-50"><UploadCloud className="h-4 w-4" aria-hidden="true" /> Upload Fundus Image <ArrowRight className="h-4 w-4" aria-hidden="true" /></button><button type="button" onClick={() => navigate('/how-it-works')} className="inline-flex items-center justify-center gap-2 rounded-xl border border-white/20 px-5 py-3 text-sm font-semibold text-white transition hover:bg-white/10">How It Works <ArrowRight className="h-4 w-4" aria-hidden="true" /></button></div><div className="mt-8 flex flex-wrap gap-x-5 gap-y-2 text-xs font-medium text-slate-300">{['DR Classification', 'Lesion Detection', 'Explainable AI', 'Medical Reports'].map((item) => <span key={item} className="inline-flex items-center gap-1.5"><Check className="h-3.5 w-3.5 text-teal-300" aria-hidden="true" />{item}</span>)}</div></div>
            <div className="relative mx-auto w-full max-w-[390px]"><div className="absolute inset-4 rounded-full border border-sky-300/20" aria-hidden="true" /><div className="relative flex aspect-square items-center justify-center overflow-hidden rounded-full border-8 border-white/10 bg-[#173d64] shadow-[0_0_0_16px_rgba(22,119,255,0.08)]"><img src={heroImage} alt={imagePreview ? 'Uploaded fundus image' : 'Example retinal fundus image'} className="h-full w-full object-cover" /></div><div className="absolute -right-2 top-8 rounded-xl border border-white/10 bg-white px-3 py-2 text-xs font-semibold text-[#0F2747] shadow-xl"><span className="mb-1 block text-[10px] uppercase tracking-wider text-slate-400">Pipeline status</span><span className="flex items-center gap-1.5"><span className={`h-2 w-2 rounded-full ${isAnalyzing ? 'animate-pulse bg-amber-400' : imagePreview ? 'bg-emerald-500' : 'bg-slate-300'}`} />{isAnalyzing ? 'Analyzing' : imagePreview ? 'Image ready' : 'Example image'}</span></div></div>
          </div>
        </section>

        <div className="mt-7"><UploadSection imagePreview={imagePreview} imageName={imageName} error={uploadError} onImageSelect={handleUploadImage} onRemove={clearImage} onValidationError={setUploadError} isAnalyzing={isAnalyzing} isComplete={reportReady} /></div>
        <section className="mt-12"><div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-end"><div><p className="section-label">One clinical workspace</p><h2 className="mt-2 text-2xl font-bold tracking-tight text-[#0F2747] sm:text-3xl">AI capabilities, clearly presented</h2></div><p className="max-w-md text-sm leading-6 text-slate-500">Review an image, understand the model output, and prepare a structured report.</p></div><div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">{capabilities.map(([title, description, Icon, path]) => <button key={title} type="button" onClick={() => openCapability(title, path)} className="group rounded-2xl border border-slate-200 bg-white p-5 text-left shadow-[0_8px_24px_rgba(15,39,71,0.04)] transition duration-200 hover:-translate-y-1 hover:border-sky-200 hover:shadow-[0_16px_32px_rgba(15,39,71,0.09)] focus:outline-none focus:ring-2 focus:ring-sky-500 focus:ring-offset-2"><div className="flex h-10 w-10 items-center justify-center rounded-xl bg-sky-50 text-[#1677FF] ring-1 ring-sky-100"><Icon className="h-5 w-5" aria-hidden="true" /></div><div className="mt-5 flex items-start justify-between gap-3"><h3 className="font-bold text-[#0F2747]">{title}</h3><ArrowRight className="h-4 w-4 shrink-0 text-slate-300 transition group-hover:translate-x-1 group-hover:text-[#1677FF]" aria-hidden="true" /></div><p className="mt-2 text-sm leading-6 text-slate-500">{description}</p><p className="mt-5 text-xs font-bold text-emerald-600">{title === 'Medical Report' && !reportReady ? 'Complete analysis to prepare' : uploadedImage ? 'Available to view' : 'Upload a fundus image to begin'}</p></button>)}</div></section>
        <section className="mt-12 rounded-2xl border border-slate-200 bg-white p-6 sm:p-8"><div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-end"><div><p className="section-label">Analysis pipeline</p><h2 className="mt-2 text-2xl font-bold text-[#0F2747]">How analysis works</h2></div><button type="button" onClick={() => navigate('/how-it-works')} className="inline-flex items-center gap-1.5 text-sm font-bold text-[#1677FF]">Explore the workflow <ArrowRight className="h-4 w-4" aria-hidden="true" /></button></div><div className="mt-8 grid gap-5 md:grid-cols-5">{workflow.map(([number, title, description], index) => <div key={number} className="relative flex gap-3 md:block md:text-center">{index < 4 && <span className="absolute left-4 top-9 hidden h-px w-[calc(100%-1rem)] bg-slate-200 md:block" aria-hidden="true" />}<span className="relative z-10 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[#0F2747] text-[10px] font-bold text-white ring-4 ring-white">{number}</span><div className="relative z-10 bg-white md:mt-3"><p className="text-sm font-bold text-[#0F2747]">{title}</p><p className="mt-1 text-xs leading-5 text-slate-500">{description}</p></div></div>)}</div></section>
        <section className="mt-12 grid gap-5 lg:grid-cols-[1.1fr_0.9fr]"><div className="rounded-2xl bg-[#EAF7F7] p-6 sm:p-8"><div className="flex h-10 w-10 items-center justify-center rounded-xl bg-white text-teal-700 shadow-sm"><ShieldCheck className="h-5 w-5" aria-hidden="true" /></div><h2 className="mt-6 text-2xl font-bold text-[#0F2747]">Designed for AI-assisted retinal analysis</h2><p className="mt-3 max-w-xl text-sm leading-6 text-slate-600">Classification, lesion findings, and explainability are presented together so your research workflow stays transparent.</p><div className="mt-6 grid gap-4 sm:grid-cols-3"><div><p className="font-bold text-[#0F2747]">AI-assisted</p><p className="mt-1 text-xs leading-5 text-slate-500">Deep learning based analysis</p></div><div><p className="font-bold text-[#0F2747]">Explainable</p><p className="mt-1 text-xs leading-5 text-slate-500">Understand model contributions</p></div><div><p className="font-bold text-[#0F2747]">Research ready</p><p className="mt-1 text-xs leading-5 text-slate-500">Exportable PDF reports</p></div></div></div><div className="rounded-2xl border border-slate-200 bg-white p-6 sm:p-8"><div className="flex items-center gap-3"><div className="flex h-10 w-10 items-center justify-center rounded-xl bg-sky-50 text-[#1677FF]"><History className="h-5 w-5" aria-hidden="true" /></div><div><p className="section-label">Your workspace</p><h2 className="mt-1 text-xl font-bold text-[#0F2747]">Recent analyses</h2></div></div>{historyError ? <p className="mt-5 rounded-xl bg-amber-50 px-3 py-3 text-sm text-amber-800">{historyError}</p> : analysisHistory.length ? <div className="mt-5 space-y-3">{analysisHistory.slice(0, 3).map((analysis) => <div key={analysis.id} className="flex items-center justify-between gap-3 border-b border-slate-100 pb-3 text-sm"><span className="truncate font-semibold text-slate-700">{analysis.image?.name || 'Retinal image'}</span><time className="shrink-0 text-xs text-slate-400">{new Date(analysis.createdAt).toLocaleDateString()}</time></div>)}</div> : <div className="mt-5 rounded-xl bg-slate-50 p-4 text-sm text-slate-500">No analyses yet. Upload a fundus image to begin.</div>}<button type="button" onClick={() => navigate('/history')} className="mt-5 inline-flex items-center gap-1.5 text-sm font-bold text-[#1677FF]">View history <ArrowRight className="h-4 w-4" aria-hidden="true" /></button></div></section>
        <div className="mt-8"><ReportDownload onView={handleViewReport} isLoading={isDownloading} isReady={reportReady} /></div><p className="mx-auto mt-8 max-w-3xl text-center text-xs leading-5 text-slate-500">AI-generated results are intended for research and educational purposes only. This system does not provide a medical diagnosis and should not replace evaluation by a qualified healthcare professional.</p>
      </div>
      <UploadRequiredModal isOpen={modalOpen} onClose={() => { setModalOpen(false); setModalFeature(''); }} onUploadImage={() => { setModalOpen(false); setModalFeature(''); focusUploadSection(); }} featureName={modalFeature} />
    </div>
  );
}

import { ArrowLeft } from 'lucide-react';
import { Link } from 'react-router-dom';
import ClassificationResult from '../components/ClassificationResult';
import ImagePreview from '../components/ImagePreview';
import RecoveryGuidance from '../components/RecoveryGuidance';
import { useAnalysis } from '../context/AnalysisContext';

export default function Classification() {
  const { imagePreview, imageName, classificationResult } = useAnalysis();

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="mb-6 flex items-center justify-between gap-4">
        <div>
          <p className="section-label">Analysis</p>
          <h1 className="mt-2 text-3xl font-semibold text-slate-900">DR Classification</h1>
        </div>
        <Link
          to="/home"
          className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
        >
          <ArrowLeft className="h-4 w-4" aria-hidden="true" />
          Back to Dashboard
        </Link>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
        <div className="medical-card p-4 sm:p-5">
          <h2 className="mb-4 text-xl font-semibold text-slate-900">Original Fundus Image</h2>
          <ImagePreview src={imagePreview} alt="Uploaded retinal fundus image" name={imageName} />
        </div>

        <ClassificationResult result={classificationResult} />
      </div>
      <RecoveryGuidance classification={classificationResult} />
    </div>
  );
}

import { useEffect, useState } from 'react';
import { ArrowLeft, Download, FileText, LoaderCircle } from 'lucide-react';
import { Link, useParams } from 'react-router-dom';
import { downloadReportPdf, getReportViewBlob } from '../services/reportApi';

export default function MedicalReportPreview() {
  const { analysisId } = useParams();
  const [viewUrl, setViewUrl] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isDownloading, setIsDownloading] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    let objectUrl = '';
    getReportViewBlob(analysisId)
      .then((blob) => {
        objectUrl = URL.createObjectURL(blob);
        setViewUrl(objectUrl);
      })
      .catch((error) => setMessage(error.message || 'Unable to load the medical report.'))
      .finally(() => setIsLoading(false));
    return () => {
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [analysisId]);

  const handleDownload = async () => {
    setIsDownloading(true);
    setMessage('');
    try {
      const blob = await downloadReportPdf(analysisId);
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `Diabetic_Retinopathy_Report_${analysisId}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      setMessage('Report downloaded successfully.');
    } catch (error) {
      setMessage(error.message || 'Unable to download the medical report.');
    } finally {
      setIsDownloading(false);
    }
  };

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <Link to="/home" className="inline-flex items-center gap-2 text-sm font-medium text-slate-600 hover:text-sky-700"><ArrowLeft className="h-4 w-4" />Back to Analysis</Link>
          <p className="section-label mt-6">Medical Report</p>
          <h1 className="mt-2 text-3xl font-semibold text-slate-900">Diabetic Retinopathy AI Analysis</h1>
          <p className="mt-2 text-sm text-slate-600">Review the generated PDF before downloading it.</p>
        </div>
        <button type="button" onClick={handleDownload} disabled={isLoading || isDownloading || !viewUrl} className="inline-flex items-center justify-center gap-2 rounded-xl bg-sky-700 px-5 py-3 text-sm font-medium text-white hover:bg-sky-800 disabled:cursor-not-allowed disabled:bg-slate-300">
          <Download className="h-4 w-4" aria-hidden="true" />
          {isDownloading ? 'Downloading report...' : 'Download Report'}
        </button>
      </div>

      {message && <div className="mb-5 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">{message}</div>}
      {isLoading && <div className="medical-card flex items-center gap-3 p-8 text-sm text-slate-600"><LoaderCircle className="h-5 w-5 animate-spin text-sky-600" />Preparing your medical report...</div>}
      {!isLoading && viewUrl && <section className="medical-card overflow-hidden p-3 sm:p-5"><div className="mb-3 flex items-center justify-between gap-3 px-1"><div className="flex items-center gap-2 text-sm font-medium text-slate-700"><FileText className="h-4 w-4 text-sky-700" />PDF Preview</div><a href={viewUrl} target="_blank" rel="noreferrer" className="text-xs font-semibold text-sky-700 hover:text-sky-900">Open in a new tab</a></div><object data={viewUrl} type="application/pdf" aria-label="Medical Report PDF" className="h-[75vh] min-h-[560px] w-full rounded-xl border border-slate-200"><div className="flex h-full min-h-[560px] flex-col items-center justify-center bg-slate-50 p-6 text-center"><FileText className="h-10 w-10 text-slate-300" aria-hidden="true" /><p className="mt-3 text-sm font-semibold text-slate-700">Your browser could not embed the PDF preview.</p><a href={viewUrl} target="_blank" rel="noreferrer" className="primary-button mt-4">Open PDF</a></div></object></section>}
    </div>
  );
}
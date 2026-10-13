import { useRef, useState } from 'react';
import { CheckCircle2, FileImage, ImagePlus, LoaderCircle, RefreshCw, UploadCloud, X } from 'lucide-react';

export default function UploadSection({
  imagePreview,
  imageName,
  error,
  onImageSelect,
  onRemove,
  onValidationError,
  isAnalyzing,
  isComplete = false,
}) {
  const inputRef = useRef(null);
  const [isDragging, setIsDragging] = useState(false);

  const validateAndSelect = (file) => {

    if (!file) {
      return;
    }

    const isAllowedType =
      file.type === 'image/jpeg' ||
      file.type === 'image/png' ||
      file.type === 'image/webp' ||
      file.type === 'image/jpg' ||
      /\.(jpg|jpeg|png|webp)$/i.test(file.name);

    if (!isAllowedType) {
      onValidationError('Please upload a JPG, JPEG, PNG, or WEBP retinal image.');
      return;
    }

    if (file.size > 12 * 1024 * 1024) {
      onValidationError('Image size must be less than 12 MB.');
      return;
    }

    onImageSelect(file);
  };

  const handleFileChange = (event) => {
    validateAndSelect(event.target.files?.[0]);
    event.target.value = '';
  };

  const handleDrop = (event) => {
    event.preventDefault();
    setIsDragging(false);
    validateAndSelect(event.dataTransfer.files?.[0]);
  };

  return (
    <section id="upload-section" className="medical-card overflow-hidden">
      <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4 sm:px-7">
        <div>
          <p className="section-label">Analysis input</p>
          <h2 className="mt-1 text-lg font-bold text-[#0F2747]">Upload a fundus image</h2>
        </div>
        <span className="hidden items-center gap-1.5 text-xs font-semibold text-slate-400 sm:flex"><span className="h-2 w-2 rounded-full bg-emerald-500" />Secure local processing</span>
      </div>

      <div className="grid gap-5 p-5 sm:p-7 lg:grid-cols-[1fr_0.9fr]">
        <div
          onDragOver={(event) => { event.preventDefault(); setIsDragging(true); }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
          className={`flex min-h-[220px] flex-col items-center justify-center rounded-xl border border-dashed px-6 py-8 text-center transition ${isDragging ? 'border-[#1677FF] bg-sky-50' : 'border-slate-300 bg-[#F8FBFE]'}`}
        >
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-white text-[#1677FF] shadow-sm ring-1 ring-sky-100"><ImagePlus className="h-6 w-6" aria-hidden="true" /></div>
          <p className="mt-4 text-sm font-bold text-[#0F2747]">Drag and drop your retinal image</p>
          <p className="mt-1 text-sm text-slate-500">or click to browse files</p>
          <button type="button" onClick={() => inputRef.current?.click()} disabled={isAnalyzing} className="primary-button mt-5 px-4 py-2.5 text-xs">
            <UploadCloud className="h-4 w-4" aria-hidden="true" /> Select Fundus Image
          </button>
          <p className="mt-4 text-[11px] font-medium text-slate-400">JPG · JPEG · PNG · WEBP · Maximum 12 MB</p>
          <input ref={inputRef} type="file" accept=".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp" className="hidden" onChange={handleFileChange} aria-label="Upload retinal fundus image" />
        </div>

      {error && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700 lg:col-span-2">
          {error}
        </div>
      )}

      {imagePreview && (
        <div className="flex flex-col justify-center rounded-xl border border-slate-200 bg-white p-4">
          <div className="relative overflow-hidden rounded-lg bg-slate-950"><img src={imagePreview} alt="Uploaded retinal fundus preview" className="h-44 w-full object-contain" />{isAnalyzing && <div className="absolute inset-0 flex items-center justify-center bg-[#0F2747]/65 text-white"><LoaderCircle className="h-6 w-6 animate-spin" aria-hidden="true" /></div>}</div>
          <div className="mt-4 flex items-start justify-between gap-3"><div className="min-w-0"><div className="flex items-center gap-2 text-sm font-bold text-[#0F2747]"><FileImage className="h-4 w-4 shrink-0 text-[#1677FF]" aria-hidden="true" /><span className="truncate">{imageName}</span></div><p className="mt-1 text-xs text-slate-500">{isAnalyzing ? 'Analyzing image with the clinical AI pipeline...' : isComplete ? 'Analysis complete. Results are ready.' : 'Image ready for analysis.'}</p></div>{isComplete && <CheckCircle2 className="h-5 w-5 shrink-0 text-emerald-500" aria-label="Analysis complete" />}</div>
          <div className="mt-4 flex gap-2"><button type="button" onClick={() => inputRef.current?.click()} disabled={isAnalyzing} className="secondary-button flex-1 px-3 py-2 text-xs"><RefreshCw className="h-3.5 w-3.5" aria-hidden="true" /> Replace</button><button type="button" onClick={onRemove} className="inline-flex items-center justify-center gap-1.5 rounded-xl border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-600 transition hover:border-rose-200 hover:bg-rose-50 hover:text-rose-700"><X className="h-3.5 w-3.5" aria-hidden="true" /> Remove</button></div>
        </div>
      )}
      </div>
    </section>
  );
}

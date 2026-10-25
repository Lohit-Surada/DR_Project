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

      <div className={`grid gap-5 p-4 sm:p-6 lg:p-7 ${imagePreview ? 'lg:grid-cols-2 lg:items-stretch' : 'grid-cols-1'}`}>
        <div
          onDragOver={(event) => { event.preventDefault(); setIsDragging(true); }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
          className={`flex min-h-[200px] w-full flex-col items-center justify-center rounded-xl border border-dashed px-4 py-6 text-center transition sm:min-h-[220px] sm:px-6 sm:py-8 ${isDragging ? 'border-[#1677FF] bg-sky-50' : 'border-slate-300 bg-[#F8FBFE]'}`}
        >
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-white text-[#1677FF] shadow-sm ring-1 ring-sky-100 sm:h-12 sm:w-12">
            <ImagePlus className="h-5 w-5 sm:h-6 sm:w-6" aria-hidden="true" />
          </div>
          <p className="mt-3.5 text-sm font-bold text-[#0F2747] sm:text-base">Drag and drop your retinal image</p>
          <p className="mt-1 text-xs text-slate-500 sm:text-sm">or click to browse files from your device</p>
          <button type="button" onClick={() => inputRef.current?.click()} disabled={isAnalyzing} className="primary-button mt-4 px-4 py-2.5 text-xs sm:mt-5 sm:px-5 sm:py-2.5 sm:text-sm">
            <UploadCloud className="h-4 w-4" aria-hidden="true" /> Select Fundus Image
          </button>
          <p className="mt-3 text-[11px] font-medium text-slate-400 sm:mt-4">JPG · JPEG · PNG · WEBP · Maximum 12 MB</p>
          <input ref={inputRef} type="file" accept=".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp" className="hidden" onChange={handleFileChange} aria-label="Upload retinal fundus image" />
        </div>

      {error && (
        <div className="col-span-full rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {error}
        </div>
      )}

      {imagePreview && (
        <div className="flex flex-col justify-between rounded-xl border border-slate-200 bg-white p-4 sm:p-5">
          <div className="relative flex aspect-video max-h-48 w-full items-center justify-center overflow-hidden rounded-lg bg-slate-950 sm:max-h-52">
            <img src={imagePreview} alt="Uploaded retinal fundus preview" className="h-full w-full object-contain" />
            {isAnalyzing && (
              <div className="absolute inset-0 flex items-center justify-center bg-[#0F2747]/65 text-white">
                <LoaderCircle className="h-6 w-6 animate-spin" aria-hidden="true" />
              </div>
            )}
          </div>
          <div className="mt-4 flex items-start justify-between gap-3">
            <div className="min-w-0">
              <div className="flex items-center gap-2 text-sm font-bold text-[#0F2747]">
                <FileImage className="h-4 w-4 shrink-0 text-[#1677FF]" aria-hidden="true" />
                <span className="truncate">{imageName}</span>
              </div>
              <p className="mt-1 text-xs text-slate-500">
                {isAnalyzing ? 'Analyzing image with the clinical AI pipeline...' : isComplete ? 'Analysis complete. Results are ready.' : 'Image ready for analysis.'}
              </p>
            </div>
            {isComplete && <CheckCircle2 className="h-5 w-5 shrink-0 text-emerald-500" aria-label="Analysis complete" />}
          </div>
          <div className="mt-4 flex gap-2">
            <button type="button" onClick={() => inputRef.current?.click()} disabled={isAnalyzing} className="secondary-button flex-1 px-3 py-2 text-xs">
              <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" /> Replace
            </button>
            <button type="button" onClick={onRemove} className="inline-flex items-center justify-center gap-1.5 rounded-xl border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-600 transition hover:border-rose-200 hover:bg-rose-50 hover:text-rose-700">
              <X className="h-3.5 w-3.5" aria-hidden="true" /> Remove
            </button>
          </div>
        </div>
      )}
      </div>
    </section>
  );
}

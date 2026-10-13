export default function ImagePreview({ src, alt, name }) {
  if (!src) {
    return null;
  }

  return (
    <div className="overflow-hidden rounded-2xl border border-slate-200 bg-slate-950">
      <div className="flex min-h-[280px] items-center justify-center sm:min-h-[360px] lg:min-h-[520px]">
        <img src={src} alt={alt} className="max-h-[70vh] w-full object-contain" />
      </div>
      {name && (
        <div className="border-t border-slate-200 bg-white px-4 py-3 text-sm text-slate-600">
          {name}
        </div>
      )}
    </div>
  );
}

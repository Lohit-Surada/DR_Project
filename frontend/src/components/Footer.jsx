export default function Footer() {
  return (
    <footer className="border-t border-slate-200 bg-white">
      <div className="mx-auto flex max-w-[1380px] flex-col gap-5 px-4 py-8 text-sm text-slate-600 sm:px-6 md:flex-row md:items-center md:justify-between lg:px-8">
        <div>
          <p className="font-bold text-[#0F2747]">RetinalAI</p>
          <p className="mt-1 text-xs text-slate-500">AI-powered retinal analysis for research and education.</p>
        </div>
        <p className="max-w-xl text-xs leading-5 text-slate-500 md:text-right">AI-generated results are intended for research and educational purposes only. This system does not provide a medical diagnosis or replace evaluation by a qualified healthcare professional.</p>
      </div>
    </footer>
  );
}

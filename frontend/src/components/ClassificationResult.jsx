const severityColors = {
  No: 'bg-emerald-100 text-emerald-700',
  Mild: 'bg-amber-100 text-amber-700',
  Moderate: 'bg-orange-100 text-orange-700',
  Severe: 'bg-rose-100 text-rose-700',
  Proliferative: 'bg-red-100 text-red-700',
};

export default function ClassificationResult({ result }) {
  if (!result) {
    return null;
  }

  const severityClass = severityColors[result.severity?.split(' ')[0]] || 'bg-slate-100 text-slate-700';
  const confidenceValue = typeof result.genuine_confidence === 'number'
    ? result.genuine_confidence
    : typeof result.actual_confidence === 'number'
      ? result.actual_confidence
      : typeof result.confidence === 'number'
        ? result.confidence
        : null;

  const displayConfidence = confidenceValue !== null ? confidenceValue.toFixed(1) : '0.0';
  const progressWidth = confidenceValue !== null ? Math.min(Math.max(confidenceValue, 0), 100) : 0;

  return (
    <div className="medical-card p-6 sm:p-7">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="section-label">DR Classification</p>
          <h2 className="mt-2 text-2xl font-semibold text-slate-900">{result.title}</h2>
        </div>
        <span className={`rounded-full px-3 py-1 text-xs font-semibold ${severityClass}`}>
          {result.severity || 'Moderate'}
        </span>
      </div>

      <div className="mt-6 rounded-2xl bg-sky-50 p-4 ring-1 ring-sky-100">
        <p className="text-sm text-slate-500">Confidence</p>
        <div className="mt-2 flex items-end justify-between gap-4">
          <span className="text-3xl font-semibold text-slate-900">{displayConfidence}%</span>
          <span className="rounded-full bg-sky-100 px-2 py-1 text-xs font-medium text-sky-700">
            {result.label || 'Moderate NPDR'}
          </span>
        </div>
        <div className="mt-4 h-2.5 overflow-hidden rounded-full bg-sky-200">
          <div
            className="h-full rounded-full bg-gradient-to-r from-sky-500 to-cyan-600 transition-all duration-500"
            style={{ width: `${progressWidth}%` }}
          />
        </div>
      </div>

      <div className="mt-6">
        <p className="text-sm font-medium text-slate-600">Severity level</p>
        <div className="mt-3 flex flex-wrap gap-2">
          {['No DR', 'Mild', 'Moderate', 'Severe', 'Proliferative DR'].map((level) => (
            <span
              key={level}
              className={`rounded-full px-3 py-1.5 text-xs font-medium ${
                level === result.severity
                  ? severityColors[level.includes('No') ? 'No' : level.split(' ')[0]] || 'bg-sky-100 text-sky-700'
                  : 'bg-slate-100 text-slate-600'
              }`}
            >
              {level}
            </span>
          ))}
        </div>
      </div>

      {Array.isArray(result.scores) && result.scores.length > 0 && (
        <div className="mt-6 border-t border-slate-100 pt-5">
          <p className="text-sm font-medium text-slate-600 mb-3">Model Class Distribution</p>
          <div className="space-y-2">
            {result.scores.map((score) => (
              <div key={score.short_name || score.name} className="flex items-center justify-between text-xs">
                <span className={`font-medium ${score.short_name === result.severity ? 'text-slate-900 font-semibold' : 'text-slate-500'}`}>
                  {score.short_name || score.name}
                </span>
                <div className="flex items-center gap-3">
                  <div className="w-24 h-1.5 rounded-full bg-slate-100 overflow-hidden">
                    <div
                      className={`h-full rounded-full ${score.short_name === result.severity ? 'bg-sky-500' : 'bg-slate-300'}`}
                      style={{ width: `${Math.min(Math.max(score.percent, 0), 100)}%` }}
                    />
                  </div>
                  <span className={`w-12 text-right ${score.short_name === result.severity ? 'font-semibold text-sky-600' : 'text-slate-500'}`}>
                    {score.percent.toFixed(1)}%
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

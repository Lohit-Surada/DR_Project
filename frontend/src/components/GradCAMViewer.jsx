import { useState, useEffect } from 'react';
import {
  CheckCircle2,
  ChevronRight,
  Download,
  Eye,
  Grid,
  Info,
  Layers,
  List,
  Maximize2,
  Sparkles,
  X,
  ZoomIn,
} from 'lucide-react';

const panelExplanations = {
  input: {
    badge: 'STAGE 01 / BASELINE INPUT',
    badgeColor: 'bg-sky-50 text-sky-700 border-sky-200',
    accentColor: 'border-sky-500 text-sky-600',
    title: 'Input Fundus Image',
    subtitle: 'High-Resolution Color Fundus Photography',
    primarySummary: 'Unaltered digital retinal fundus photograph submitted for diagnostic analysis.',
    purpose: 'Provides the anatomical reference standard, capturing posterior pole vascular networks, optic disc, macula, and vessel geometry before algorithmic evaluation.',
    keyInsights: [
      { label: 'Anatomical Field', text: 'Depicts posterior pole vascular networks, foveal center, and background retinal pigment.' },
      { label: 'Diagnostic Reference', text: 'Serves as ground truth for clinical verification against AI-generated heatmap activations.' },
      { label: 'Lesion Baseline', text: 'Unaltered canvas to evaluate natural appearance of microaneurysms, hemorrhages, and lipid exudates.' },
    ],
    technicalSpec: {
      type: 'RGB Digital Fundus Capture',
      pipelineRole: 'Input Pipeline Entry',
      normalization: 'Standardized Preprocessing',
    },
  },
  gradcam: {
    badge: 'STAGE 02 / MODEL SALIENCY',
    badgeColor: 'bg-rose-50 text-rose-700 border-rose-200',
    accentColor: 'border-rose-500 text-rose-600',
    title: 'True YOLO26 Grad-CAM Saliency',
    subtitle: 'Gradient-Weighted Class Activation Map',
    primarySummary: 'Highlights retinal regions that directly exerted the highest neural weight on the prediction.',
    purpose: 'Flows gradients backward from the classification head to layer 16 feature maps to reveal decision-critical lesion clusters.',
    keyInsights: [
      { label: 'Warm Spectrum (Red / Yellow)', text: 'Denotes intense neural activation corresponding to prominent pathological lesions.' },
      { label: 'Cool Spectrum (Blue / Navy)', text: 'Represents non-contributory background or healthy retinal parenchymal regions.' },
      { label: 'Clinical Explainability', text: 'Verifies that neural decisions stem from actual diabetic retinopathy pathology rather than imaging artifacts.' },
      { label: 'Scope Clarification', text: 'Specific to YOLO26 lesion detection; does not independently explain separate CNN severity classification.' },
    ],
    technicalSpec: {
      type: 'Target Layer 16 Gradients',
      pipelineRole: 'Explainability & Saliency',
      normalization: 'Alpha Overlay Blending',
    },
  },
  attention: {
    badge: 'STAGE 03 / CONTRAST ENHANCEMENT',
    badgeColor: 'bg-amber-50 text-amber-700 border-amber-200',
    accentColor: 'border-amber-500 text-amber-600',
    title: 'Retinal Attention & Contrast Map',
    subtitle: 'CLAHE & Local Difference Visualization',
    primarySummary: 'Adaptive histogram equalization emphasizing vascular micro-textures and subtle lesion boundaries.',
    purpose: 'Amplifies localized contrast differentials to make faint microvascular lesions distinguishable from uneven retinal illumination.',
    keyInsights: [
      { label: 'Microvascular Contours', text: 'Heightens visibility of fine capillary networks and subtle microaneurysm silhouettes.' },
      { label: 'Illumination Equalization', text: 'Compensates for uneven flash illumination and peripheral illumination drop-off.' },
      { label: 'Border Sharpness', text: 'Differentiates sharp lipid borders of hard exudates from fluffy cotton-wool patches.' },
    ],
    technicalSpec: {
      type: 'CLAHE + Contrast Filtering',
      pipelineRole: 'Structural Texture Map',
      normalization: 'Adaptive Histogram Clip',
    },
  },
  feature: {
    badge: 'STAGE 04 / DEEP REPRESENTATIONS',
    badgeColor: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    accentColor: 'border-emerald-500 text-emerald-600',
    title: 'YOLO26 Latent Feature Map',
    subtitle: 'Deep Layer Latent Spatial Embeddings',
    primarySummary: 'Direct visualization of intermediate neural activations extracted from the detection backbone.',
    purpose: 'Demonstrates how the deep convolutional backbone abstracts raw pixel intensities into high-level spatial representations.',
    keyInsights: [
      { label: 'Feature Abstraction', text: 'Traces the transition from primitive low-level edges to composite lesion representations.' },
      { label: 'Spatial Preservation', text: 'Confirms that spatial coordinates of pathology remain preserved prior to regression heads.' },
      { label: 'Clustering Health', text: 'Validates activation focus around localized abnormalities before bounding box output.' },
    ],
    technicalSpec: {
      type: 'Intermediate Backbone Activations',
      pipelineRole: 'Internal Representation Map',
      normalization: 'Multi-Channel Tensor Projection',
    },
  },
};

function defaultExplanation(panel, idx) {
  return {
    badge: `STAGE 0${idx + 1} / VISUALIZATION`,
    badgeColor: 'bg-slate-100 text-slate-700 border-slate-200',
    accentColor: 'border-slate-500 text-slate-600',
    title: panel.title || `Stage ${idx + 1} Visualization`,
    subtitle: 'Model Feature Visualization',
    primarySummary: panel.description || 'Visual representation of model processing stage.',
    purpose: 'Provides visual insight into retinal image analysis.',
    keyInsights: [
      { label: 'Visual Analysis', text: 'Assists in understanding neural network behavior.' },
      { label: 'Clinical Review', text: 'Supplementary visual aid for ophthalmic research.' },
    ],
    technicalSpec: {
      type: 'Feature Map Output',
      pipelineRole: 'Neural Processing Stage',
    },
  };
}

export default function GradCAMViewer({ panels, combined }) {
  const [activeModal, setActiveModal] = useState(null);
  const [hoveredIndex, setHoveredIndex] = useState(null);
  const [activeFilter, setActiveFilter] = useState('all'); // 'all' or panel key
  const [viewLayout, setViewLayout] = useState('rows'); // 'rows' or 'grid'

  useEffect(() => {
    function handleKeyDown(event) {
      if (event.key === 'Escape') {
        setActiveModal(null);
      }
    }
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  if (!panels || !panels.length) {
    return null;
  }

  const displayedPanels =
    activeFilter === 'all' ? panels : panels.filter((p) => p.key === activeFilter);

  return (
    <div className="space-y-8">
      {/* Optional Top 4-Panel Combined Strip */}
      {combined && (
        <section className="medical-card overflow-hidden p-4 sm:p-5">
          <div className="flex flex-wrap items-center justify-between gap-3 px-1 pb-3">
            <div>
              <p className="section-label">Combined Overview</p>
              <h2 className="mt-1 text-lg font-semibold text-slate-900">
                Full 4-Panel Explainability Strip
              </h2>
            </div>
            <a
              href={combined}
              download="gradcam-4panel-visualization.jpg"
              className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3.5 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 hover:border-slate-300 transition shadow-sm"
            >
              <Download className="h-3.5 w-3.5 text-sky-600" />
              Download Full Strip
            </a>
          </div>
          <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-slate-950">
            <img
              src={combined}
              alt="Four-panel Grad-CAM visualization"
              className="block min-w-[900px] w-full"
            />
          </div>
        </section>
      )}

      {/* Main Section */}
      <section className="medical-card overflow-hidden p-5 sm:p-7 lg:p-8 bg-white border border-slate-200/90 shadow-sm">
        {/* Section Header with Controls */}
        <div className="mb-6 border-b border-slate-100 pb-5">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <p className="section-label">Explainability Pipeline</p>
              <h2 className="mt-1.5 text-2xl font-bold text-slate-900 tracking-tight">
                Picture-Wise Visual & Clinical Analysis
              </h2>
              <p className="mt-1 text-sm text-slate-600">
                Row-wise breakdown: analytical visualization on the left paired with point-wise clinical interpretation on the right.
              </p>
            </div>

            {/* View Mode Switcher */}
            <div className="flex items-center gap-2">
              <div className="inline-flex rounded-xl border border-slate-200 bg-slate-100/80 p-1">
                <button
                  type="button"
                  onClick={() => setViewLayout('rows')}
                  className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                    viewLayout === 'rows'
                      ? 'bg-white text-slate-900 shadow-sm'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                  title="Row-wise detailed view"
                >
                  <List className="h-3.5 w-3.5" />
                  Row View
                </button>
                <button
                  type="button"
                  onClick={() => setViewLayout('grid')}
                  className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                    viewLayout === 'grid'
                      ? 'bg-white text-slate-900 shadow-sm'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                  title="Side-by-side comparison grid"
                >
                  <Grid className="h-3.5 w-3.5" />
                  Grid View
                </button>
              </div>
            </div>
          </div>

          {/* Quick Filter Navigation Tabs */}
          <div className="mt-5 flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={() => setActiveFilter('all')}
              className={`rounded-xl px-3.5 py-1.5 text-xs font-semibold transition border ${
                activeFilter === 'all'
                  ? 'bg-sky-600 text-white border-sky-600 shadow-sm'
                  : 'bg-slate-50 text-slate-700 border-slate-200 hover:bg-slate-100'
              }`}
            >
              All Stages (4)
            </button>
            {panels.map((p, idx) => {
              const meta = panelExplanations[p.key] || defaultExplanation(p, idx);
              const isActive = activeFilter === p.key;
              return (
                <button
                  key={p.key}
                  type="button"
                  onClick={() => setActiveFilter(p.key)}
                  className={`rounded-xl px-3 py-1.5 text-xs font-semibold transition border ${
                    isActive
                      ? 'bg-slate-900 text-white border-slate-900 shadow-sm'
                      : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50 hover:text-slate-900'
                  }`}
                >
                  {p.title || `Stage ${idx + 1}`}
                </button>
              );
            })}
          </div>
        </div>

        {/* Content Presentation */}
        {viewLayout === 'rows' ? (
          /* ── Row-Wise 2-Column Layout ── */
          <div className="space-y-6">
            {displayedPanels.map((panel, idx) => {
              const meta = panelExplanations[panel.key] || defaultExplanation(panel, idx);
              const isHovered = hoveredIndex === idx;

              return (
                <div
                  key={panel.key}
                  className={`rounded-2xl border transition-all duration-300 p-5 sm:p-6 ${
                    isHovered
                      ? 'border-sky-400 bg-sky-50/20 ring-2 ring-sky-100 shadow-md'
                      : 'border-slate-200/90 bg-slate-50/40 hover:border-slate-300 hover:bg-slate-50/70'
                  }`}
                  onMouseEnter={() => setHoveredIndex(idx)}
                  onMouseLeave={() => setHoveredIndex(null)}
                >
                  <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
                    {/* Left Column: Title + Square Image Box */}
                    <div className="lg:col-span-5 flex flex-col justify-between">
                      {/* Title & Stage Header */}
                      <div className="mb-3">
                        <div className="flex items-center gap-2">
                          <span
                            className={`inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider border ${meta.badgeColor}`}
                          >
                            {meta.badge}
                          </span>
                        </div>
                        <h3 className="mt-1 text-lg font-bold text-slate-900 tracking-tight">
                          {meta.title}
                        </h3>
                        <p className="text-xs text-slate-500">{meta.subtitle}</p>
                      </div>

                      {/* Image Box */}
                      <div className="relative w-full aspect-square rounded-2xl border border-slate-800 bg-slate-950 overflow-hidden shadow-inner flex items-center justify-center group">
                        <img
                          src={panel.image}
                          alt={panel.title}
                          className="w-full h-full object-contain p-2 transition-transform duration-300 group-hover:scale-105"
                          loading="lazy"
                        />

                        {/* Top Right Expand Button */}
                        <div className="absolute top-3 right-3 flex items-center gap-1.5">
                          <button
                            type="button"
                            onClick={() => setActiveModal({ ...panel, meta, idx })}
                            className="p-2 rounded-xl bg-slate-900/85 hover:bg-sky-600 text-white backdrop-blur-md border border-white/10 shadow-sm transition"
                            title="Expand in high resolution"
                            aria-label={`Expand ${panel.title}`}
                          >
                            <Maximize2 className="h-4 w-4" />
                          </button>
                        </div>

                        {/* Bottom Info Pill */}
                        <div className="absolute bottom-3 inset-x-3 flex items-center justify-between pointer-events-none">
                          <span className="inline-flex items-center gap-1.5 rounded-lg bg-slate-950/85 backdrop-blur-md px-2.5 py-1 text-xs font-medium text-slate-200 border border-white/10 truncate max-w-[70%]">
                            <Eye className="h-3.5 w-3.5 text-sky-400 shrink-0" />
                            <span className="truncate">{panel.title}</span>
                          </span>
                          <span className="text-[10px] text-slate-400 bg-slate-950/85 px-2 py-1 rounded-lg backdrop-blur-md border border-white/5 shrink-0">
                            Click to zoom
                          </span>
                        </div>

                        {/* Hover Overlay */}
                        <button
                          type="button"
                          onClick={() => setActiveModal({ ...panel, meta, idx })}
                          className="absolute inset-0 bg-sky-950/20 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center cursor-pointer"
                          aria-label={`Inspect ${panel.title}`}
                        >
                          <span className="inline-flex items-center gap-1.5 rounded-xl bg-sky-600 text-white text-xs font-semibold px-3 py-1.5 shadow-lg transform -translate-y-1 group-hover:translate-y-0 transition">
                            <ZoomIn className="h-4 w-4" />
                            Inspect High-Res
                          </span>
                        </button>
                      </div>
                    </div>

                    {/* Right Column: Points-Wise Clinical & Technical Information */}
                    <div className="lg:col-span-7 flex flex-col justify-between rounded-2xl border border-slate-200/80 bg-white p-5 sm:p-6 shadow-sm">
                      <div className="space-y-4">
                        {/* Section Header */}
                        <div className="flex items-center justify-between border-b border-slate-100 pb-2.5">
                          <p className="text-xs font-bold uppercase tracking-wider text-slate-500">
                            Key Clinical & Model Information
                          </p>
                          <span className="rounded-md bg-slate-100 px-2 py-0.5 text-[11px] font-semibold text-slate-600">
                            {meta.technicalSpec.type}
                          </span>
                        </div>

                        {/* Point 1: Primary Role & Summary */}
                        <div className="flex items-start gap-3">
                          <span className="mt-1 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-sky-100 text-sky-700 font-bold text-xs">
                            1
                          </span>
                          <div>
                            <p className="text-xs font-bold uppercase tracking-wider text-slate-500">
                              Primary Clinical Role
                            </p>
                            <p className="mt-0.5 text-sm font-medium leading-relaxed text-slate-800">
                              {meta.primarySummary}
                            </p>
                          </div>
                        </div>

                        {/* Point 2: Diagnostic Purpose */}
                        <div className="flex items-start gap-3">
                          <span className="mt-1 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-indigo-100 text-indigo-700 font-bold text-xs">
                            2
                          </span>
                          <div>
                            <p className="text-xs font-bold uppercase tracking-wider text-slate-500">
                              Diagnostic & Architectural Value
                            </p>
                            <p className="mt-0.5 text-sm leading-relaxed text-slate-600">
                              {meta.purpose}
                            </p>
                          </div>
                        </div>

                        {/* Point 3: Key Clinical Observations */}
                        <div className="flex items-start gap-3">
                          <span className="mt-1 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-emerald-100 text-emerald-700 font-bold text-xs">
                            3
                          </span>
                          <div className="flex-1">
                            <p className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-1">
                              Key Clinical Observations
                            </p>
                            <ul className="space-y-1.5">
                              {meta.keyInsights.map((insight, iIdx) => (
                                <li
                                  key={iIdx}
                                  className="flex items-start gap-2 text-xs sm:text-sm text-slate-700"
                                >
                                  <span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-sky-500 shrink-0" />
                                  <span>
                                    <strong className="font-semibold text-slate-900">
                                      {insight.label}:{' '}
                                    </strong>
                                    <span className="text-slate-600">{insight.text}</span>
                                  </span>
                                </li>
                              ))}
                            </ul>
                          </div>
                        </div>
                      </div>

                      {/* Point 4: Technical Specification Bar */}
                      <div className="mt-5 pt-3.5 border-t border-slate-100 flex flex-wrap items-center justify-between gap-3 text-xs">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="rounded-lg bg-slate-50 border border-slate-200/80 px-2.5 py-1 text-slate-600">
                            Role: <strong className="text-slate-800">{meta.technicalSpec.pipelineRole}</strong>
                          </span>
                          {meta.technicalSpec.normalization && (
                            <span className="rounded-lg bg-slate-50 border border-slate-200/80 px-2.5 py-1 text-slate-600">
                              Spec: <strong className="text-slate-800">{meta.technicalSpec.normalization}</strong>
                            </span>
                          )}
                        </div>

                        <a
                          href={panel.image}
                          download={`${panel.key}-visualization.jpg`}
                          className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3.5 py-1.5 font-semibold text-slate-700 hover:bg-slate-50 hover:border-slate-300 transition shadow-sm"
                        >
                          <Download className="h-3.5 w-3.5 text-sky-600" />
                          Save Image
                        </a>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          /* ── Comparison Grid Layout ── */
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
            {displayedPanels.map((panel, idx) => {
              const meta = panelExplanations[panel.key] || defaultExplanation(panel, idx);
              return (
                <div
                  key={panel.key}
                  className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm hover:border-sky-300 transition flex flex-col justify-between"
                >
                  <div>
                    <div className="flex items-center justify-between gap-2 mb-2">
                      <span className={`rounded-md px-2 py-0.5 text-[10px] font-bold border ${meta.badgeColor}`}>
                        {meta.badge}
                      </span>
                      <button
                        type="button"
                        onClick={() => setActiveModal({ ...panel, meta, idx })}
                        className="text-xs text-sky-600 font-semibold hover:underline inline-flex items-center gap-1"
                      >
                        <Maximize2 className="h-3 w-3" />
                        Expand
                      </button>
                    </div>

                    <h4 className="text-base font-bold text-slate-900">{meta.title}</h4>
                    <p className="text-xs text-slate-500 mb-3">{meta.subtitle}</p>

                    <div
                      className="relative w-full aspect-square rounded-xl bg-slate-950 overflow-hidden cursor-pointer group"
                      onClick={() => setActiveModal({ ...panel, meta, idx })}
                    >
                      <img
                        src={panel.image}
                        alt={panel.title}
                        className="w-full h-full object-contain p-1 group-hover:scale-105 transition"
                      />
                    </div>

                    <div className="mt-3 space-y-1.5 text-xs text-slate-600">
                      <p>
                        <strong className="text-slate-800">Summary: </strong>
                        {meta.primarySummary}
                      </p>
                      <p>
                        <strong className="text-slate-800">Diagnostic Role: </strong>
                        {meta.purpose}
                      </p>
                    </div>
                  </div>

                  <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs">
                    <span className="text-slate-500">{meta.technicalSpec.type}</span>
                    <a
                      href={panel.image}
                      download={`${panel.key}-visualization.jpg`}
                      className="text-sky-600 font-semibold hover:underline inline-flex items-center gap-1"
                    >
                      <Download className="h-3 w-3" />
                      Save
                    </a>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>

      {/* Lightbox / Modal for High-Res Inspection */}
      {activeModal && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 bg-slate-950/80 backdrop-blur-sm"
          onClick={() => setActiveModal(null)}
        >
          <div
            className="relative max-w-4xl w-full bg-white rounded-2xl border border-slate-200 shadow-2xl overflow-hidden"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
              <div>
                <span className="text-xs font-bold text-sky-600 uppercase tracking-wider">
                  Box {activeModal.idx + 1} of {panels.length} · High-Resolution Inspection
                </span>
                <h3 className="text-lg font-bold text-slate-900">{activeModal.title}</h3>
              </div>
              <div className="flex items-center gap-2">
                <a
                  href={activeModal.image}
                  download={`${activeModal.key}-full.jpg`}
                  className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 transition"
                >
                  <Download className="h-4 w-4 text-sky-600" />
                  Download
                </a>
                <button
                  type="button"
                  onClick={() => setActiveModal(null)}
                  className="p-1.5 rounded-xl text-slate-500 hover:text-slate-900 hover:bg-slate-100 transition"
                  aria-label="Close modal"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>
            </div>

            <div className="p-4 sm:p-6 bg-slate-950 flex items-center justify-center max-h-[70vh]">
              <img
                src={activeModal.image}
                alt={activeModal.title}
                className="max-h-[65vh] w-auto object-contain rounded-lg shadow-lg"
              />
            </div>

            <div className="px-6 py-4 bg-slate-50 border-t border-slate-100 text-sm text-slate-600 flex items-center justify-between">
              <p className="text-xs sm:text-sm text-slate-700">{activeModal.meta.primarySummary}</p>
              <button
                type="button"
                onClick={() => setActiveModal(null)}
                className="ml-4 shrink-0 px-3 py-1 text-xs font-semibold rounded-lg bg-white border border-slate-200 text-slate-700 hover:bg-slate-100 transition"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

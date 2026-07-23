// Asynchronous Modular Slide Component Loader (18 Atomic Slides)
const SLIDE_FILES = [
  'slides/slide-01-cover.html',
  'slides/slide-02-background.html',
  'slides/slide-03-problem.html',
  'slides/slide-04-current-state.html',
  'slides/slide-05-targets.html',
  'slides/slide-06-fishbone.html',
  'slides/slide-07-root-cause.html',
  'slides/slide-08-solutions.html',
  'slides/slide-09-architecture.html',
  'slides/slide-10-dual-mode.html',
  'slides/slide-11-overall-accuracy.html',
  'slides/slide-12-camera-angles.html',
  'slides/slide-13-partial-gating.html',
  'slides/slide-14-distance.html',
  'slides/slide-15-lighting.html',
  'slides/slide-16-sop.html',
  'slides/slide-17-future-work.html',
  'slides/slide-18-conclusion.html'
];

async function loadModularSlides() {
  const container = document.getElementById('slides-container');
  if (!container) return;

  try {
    for (const file of SLIDE_FILES) {
      const response = await fetch(file);
      if (response.ok) {
        const html = await response.text();
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = html.trim();
        const section = tempDiv.firstElementChild;
        if (section) {
          container.appendChild(section);
        }
      } else {
        console.warn(`Failed to load slide component: ${file}`);
      }
    }
  } catch (err) {
    console.error('Error loading modular slides:', err);
  }

  // Dispatch custom event when all modular slides are loaded
  document.dispatchEvent(new Event('slidesLoaded'));
}

document.addEventListener('DOMContentLoaded', () => {
  loadModularSlides();
});

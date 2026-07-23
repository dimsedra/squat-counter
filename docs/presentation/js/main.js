// Initialize Reveal.js after all modular slides are loaded
document.addEventListener('slidesLoaded', () => {
  // Initialize Reveal.js
  Reveal.initialize({
    controls: true,
    progress: true,
    center: true,
    hash: true,
    transition: 'fade',
    transitionSpeed: 'normal',
    slideNumber: 'c/t',
    autoPlayMedia: false,
  });

  // Initialize Lucide Icons
  if (window.lucide) {
    lucide.createIcons();
  }

  // Initialize Mermaid.js
  if (window.mermaid) {
    mermaid.initialize({
      startOnLoad: true,
      theme: 'dark',
      themeVariables: {
        darkMode: true,
        background: '#1a2024',
        primaryColor: '#2dd4bf',
        primaryTextColor: '#e8ecef',
        primaryBorderColor: '#30363d',
        lineColor: '#94a3b8',
        secondaryColor: '#222a30',
        tertiaryColor: '#121619'
      }
    });
  }

  // Initialize Chart.js Graphs
  initCharts();

  // Initialize Right Slide-In Sidebar Navigation System
  initRightSidebarNav();
});

// Right Slide-In Sidebar Navigation System Logic
function initRightSidebarNav() {
  const sidebar = document.getElementById('sidebar-drawer');
  const backdrop = document.getElementById('sidebar-backdrop');
  const toggleBtn = document.getElementById('sidebar-toggle-btn');
  const closeBtn = document.getElementById('sidebar-close-btn');
  const slideList = document.getElementById('sidebar-slide-list');

  if (!sidebar || !slideList) return;

  // Build 17 Slide Items inside Sidebar
  const slides = document.querySelectorAll('.reveal .slides > section');
  slideList.innerHTML = '';

  slides.forEach((slide, index) => {
    // Extract Title & Step Badge
    const titleEl = slide.querySelector('h1, h2');
    const badgeEl = slide.querySelector('.badge');

    const titleText = titleEl ? titleEl.innerText.replace(/[\n\r]+/g, ' ').trim() : `Slide ${index + 1}`;
    const badgeText = badgeEl ? badgeEl.innerText.replace(/[\n\r]+/g, ' ').trim() : 'QCC Slide';

    const item = document.createElement('div');
    item.className = `sidebar-slide-item ${index === 0 ? 'active-slide' : ''}`;
    item.dataset.slideIndex = index;

    item.innerHTML = `
      <div class="sidebar-slide-num">${String(index + 1).padStart(2, '0')}</div>
      <div class="sidebar-slide-info">
        <div class="sidebar-slide-title">${titleText}</div>
        <div class="sidebar-slide-step">${badgeText}</div>
      </div>
    `;

    item.addEventListener('click', () => {
      Reveal.slide(index);
      closeSidebar();
    });

    slideList.appendChild(item);
  });

  // Open Sidebar
  function openSidebar() {
    sidebar.classList.add('active');
    if (backdrop) backdrop.classList.add('active');
    updateActiveSlideHighlight();
  }

  // Close Sidebar
  function closeSidebar() {
    sidebar.classList.remove('active');
    if (backdrop) backdrop.classList.remove('active');
  }

  // Toggle Sidebar
  function toggleSidebar() {
    if (sidebar.classList.contains('active')) {
      closeSidebar();
    } else {
      openSidebar();
    }
  }

  // Highlight Current Active Slide
  function updateActiveSlideHighlight() {
    const indices = Reveal.getIndices();
    const activeIndex = indices.h;
    const items = slideList.querySelectorAll('.sidebar-slide-item');
    
    items.forEach((item, idx) => {
      if (idx === activeIndex) {
        item.classList.add('active-slide');
        item.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
      } else {
        item.classList.remove('active-slide');
      }
    });
  }

  // Event Listeners
  if (toggleBtn) toggleBtn.addEventListener('click', toggleSidebar);
  if (closeBtn) closeBtn.addEventListener('click', closeSidebar);
  if (backdrop) backdrop.addEventListener('click', closeSidebar);

  // Keyboard Shortcuts: Press 'M' or 'm' to toggle right sidebar
  document.addEventListener('keydown', (e) => {
    if (e.key === 'm' || e.key === 'M') {
      if (['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName)) return;
      toggleSidebar();
    } else if (e.key === 'Escape' && sidebar.classList.contains('active')) {
      closeSidebar();
      e.stopPropagation();
    }
  });

  // Update Highlight on Slide Change
  Reveal.on('slidechanged', () => {
    updateActiveSlideHighlight();
  });
}

function initCharts() {
  if (typeof Chart === 'undefined') return;

  // Chart Global Defaults for Proposal 3 Dark Graphite & Sage Theme
  Chart.defaults.color = '#94a3b8';
  Chart.defaults.font.family = "'Plus Jakarta Sans', system-ui, sans-serif";

  // 1. Slide 11: Accuracy Distribution Pie Chart
  const pieCtx = document.getElementById('accuracyPieChart');
  if (pieCtx) {
    new Chart(pieCtx, {
      type: 'doughnut',
      data: {
        labels: ['Exact Match (100% Akurat)', 'Mendekati (Eror = 1 Rep)', 'Terdistorsi (Eror > 1 Rep)'],
        datasets: [{
          data: [36, 8, 12],
          backgroundColor: ['#2dd4bf', '#38bdf8', '#f85149'],
          borderColor: '#1a2024',
          borderWidth: 3,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'right',
            labels: { boxWidth: 14, padding: 12, font: { size: 12 } }
          }
        }
      }
    });
  }

  // 2. Slide 12: Camera Viewpoint MAE Bar Chart
  const viewCtx = document.getElementById('cameraViewChart');
  if (viewCtx) {
    new Chart(viewCtx, {
      type: 'bar',
      data: {
        labels: ['Kamera Samping (90°)', 'Kamera Serong (45°)', 'Kamera Depan (0°)'],
        datasets: [{
          label: 'Mean Absolute Error (MAE Repetisi)',
          data: [0.250, 1.725, 2.625],
          backgroundColor: ['#2dd4bf', '#38bdf8', '#f85149'],
          borderRadius: 8,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          y: {
            beginAtZero: true,
            grid: { color: '#2a3238' },
            title: { display: true, text: 'MAE (Repetisi)', color: '#94a3b8' }
          },
          x: { grid: { display: false } }
        }
      }
    });
  }

  // 3. Slide 14: Athlete MAE Bar Chart (Loose Clothing Analysis)
  const athleteCtx = document.getElementById('athleteMaeChart');
  if (athleteCtx) {
    new Chart(athleteCtx, {
      type: 'bar',
      data: {
        labels: ['Atlet A1 (Fitted)', 'Atlet A2 (Fitted)', 'Atlet A3 (Fitted)', 'Atlet A4 (Loose Clothing)'],
        datasets: [{
          label: 'Mean Absolute Error (MAE)',
          data: [1.000, 0.500, 1.214, 3.857],
          backgroundColor: ['#38bdf8', '#2dd4bf', '#38bdf8', '#f85149'],
          borderRadius: 8,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          y: {
            beginAtZero: true,
            grid: { color: '#2a3238' },
            title: { display: true, text: 'MAE (Repetisi)', color: '#94a3b8' }
          },
          x: { grid: { display: false } }
        }
      }
    });
  }
}

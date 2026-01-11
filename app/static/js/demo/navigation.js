// Navigation, routing, and state management for demo pages

const DemoNavigation = {
  init() {
    this.highlightActiveNav();
    this.setupBreadcrumbs();
    this.setupMobileMenu();
  },
  
  highlightActiveNav() {
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.demo-nav .nav-link');
    
    navLinks.forEach(link => {
      const href = link.getAttribute('href');
      if (href) {
        const normalizedHref = href.endsWith('/') ? href.slice(0, -1) : href;
        const normalizedPath = currentPath.endsWith('/') && currentPath !== '/' 
          ? currentPath.slice(0, -1) 
          : currentPath;
        
        if (normalizedPath === normalizedHref || 
            (normalizedHref !== '/demo/' && normalizedPath.startsWith(normalizedHref + '/'))) {
          link.classList.add('active');
        } else {
          link.classList.remove('active');
        }
      } else {
        link.classList.remove('active');
      }
    });
  },
  
  setupBreadcrumbs() {
    const path = window.location.pathname;
    const parts = path.split('/').filter(p => p);
    
    if (parts.length > 1 && parts[0] === 'demo') {
      const breadcrumbContainer = document.getElementById('breadcrumbs');
      if (breadcrumbContainer) {
        let breadcrumbHTML = '<nav aria-label="breadcrumb"><ol class="breadcrumb">';
        breadcrumbHTML += '<li class="breadcrumb-item"><a href="/demo/">Home</a></li>';
        
        for (let i = 1; i < parts.length; i++) {
          const part = parts[i];
          const isLast = i === parts.length - 1;
          const label = this.formatBreadcrumbLabel(part);
          
          if (isLast) {
            breadcrumbHTML += `<li class="breadcrumb-item active" aria-current="page">${label}</li>`;
          } else {
            const href = '/' + parts.slice(0, i + 1).join('/');
            breadcrumbHTML += `<li class="breadcrumb-item"><a href="${href}">${label}</a></li>`;
          }
        }
        
        breadcrumbHTML += '</ol></nav>';
        breadcrumbContainer.innerHTML = breadcrumbHTML;
      }
    }
  },
  
  formatBreadcrumbLabel(part) {
    return part
      .split('-')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  },
  
  setupMobileMenu() {
    const toggle = document.getElementById('mobile-menu-toggle');
    const menu = document.getElementById('mobile-menu');
    
    if (toggle && menu) {
      toggle.addEventListener('click', () => {
        menu.classList.toggle('show');
      });
    }
  },
  
  navigateTo(url) {
    window.location.href = url;
  },
  
  goBack() {
    window.history.back();
  },
  
  goForward() {
    window.history.forward();
  },
};

// Initialize on DOM ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    DemoNavigation.init();
  });
} else {
  DemoNavigation.init();
}

// Export to window
window.DemoNavigation = DemoNavigation;


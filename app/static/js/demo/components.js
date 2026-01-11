// Reusable UI components for demo pages

const DemoComponents = {
  // Copy to clipboard button
  initCopyButtons() {
    document.querySelectorAll('.copy-btn').forEach(button => {
      button.addEventListener('click', async (e) => {
        e.preventDefault();
        const text = button.getAttribute('data-copy') || button.textContent;
        
        try {
          await DemoUtils.copyToClipboard(text);
          DemoToast.success('Copied to clipboard!');
          
          const originalText = button.textContent;
          button.textContent = 'Copied!';
          setTimeout(() => {
            button.textContent = originalText;
          }, 2000);
        } catch (error) {
          DemoToast.error('Failed to copy to clipboard');
        }
      });
    });
  },
  
  // Form validation
  validateForm(form) {
    const inputs = form.querySelectorAll('input[required], textarea[required], select[required]');
    let isValid = true;
    
    inputs.forEach(input => {
      if (!input.value.trim()) {
        isValid = false;
        input.classList.add('is-invalid');
      } else {
        input.classList.remove('is-invalid');
      }
    });
    
    return isValid;
  },
  
  // Initialize form validation
  initFormValidation() {
    document.querySelectorAll('form').forEach(form => {
      form.addEventListener('submit', (e) => {
        if (!this.validateForm(form)) {
          e.preventDefault();
          DemoToast.error('Please fill in all required fields');
        }
      });
    });
  },
  
  // Loading button
  setLoading(button, loading) {
    if (loading) {
      button.disabled = true;
      button.dataset.originalText = button.textContent;
      button.innerHTML = '<span class="loading"></span> Loading...';
    } else {
      button.disabled = false;
      button.textContent = button.dataset.originalText || button.textContent;
    }
  },
  
  // Modal helper
  showModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
      modal.style.display = 'block';
      document.body.style.overflow = 'hidden';
    }
  },
  
  hideModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
      modal.style.display = 'none';
      document.body.style.overflow = '';
    }
  },
  
  // Initialize modals
  initModals() {
    document.querySelectorAll('[data-modal]').forEach(trigger => {
      trigger.addEventListener('click', (e) => {
        e.preventDefault();
        const modalId = trigger.getAttribute('data-modal');
        this.showModal(modalId);
      });
    });
    
    document.querySelectorAll('.modal-close').forEach(closeBtn => {
      closeBtn.addEventListener('click', (e) => {
        e.preventDefault();
        const modal = closeBtn.closest('.modal');
        if (modal) {
          this.hideModal(modal.id);
        }
      });
    });
    
    // Close on backdrop click
    document.querySelectorAll('.modal').forEach(modal => {
      modal.addEventListener('click', (e) => {
        if (e.target === modal) {
          this.hideModal(modal.id);
        }
      });
    });
  },
  
  // Initialize all components
  init() {
    this.initCopyButtons();
    this.initFormValidation();
    this.initModals();
  },
};

// Initialize on DOM ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    DemoComponents.init();
  });
} else {
  DemoComponents.init();
}

// Export to window
window.DemoComponents = DemoComponents;


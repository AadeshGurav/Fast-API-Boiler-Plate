// Feature-specific functionality for demo pages

const DemoFeatures = {
  // Library feature helpers
  library: {
    async loadBooks() {
      try {
        const response = await fetch('/demo/library/books');
        const data = await response.json();
        return data.books || [];
      } catch (error) {
        console.error('Failed to load books:', error);
        DemoToast.error('Failed to load books');
        return [];
      }
    },
    
    async searchBooks(query) {
      try {
        const response = await fetch(`/demo/library/search?q=${encodeURIComponent(query)}`);
        const data = await response.json();
        return data.books || [];
      } catch (error) {
        console.error('Failed to search books:', error);
        DemoToast.error('Failed to search books');
        return [];
      }
    },
    
    async checkoutBook(bookId) {
      try {
        const response = await fetch(`/demo/library/books/${bookId}/checkout`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
        });
        
        if (response.ok) {
          DemoToast.success('Book checked out successfully!');
          return true;
        } else {
          const error = await response.json();
          DemoToast.error(error.detail || 'Failed to checkout book');
          return false;
        }
      } catch (error) {
        console.error('Failed to checkout book:', error);
        DemoToast.error('Failed to checkout book');
        return false;
      }
    },
    
    async returnBook(bookId) {
      try {
        const response = await fetch(`/demo/library/books/${bookId}/return`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
        });
        
        if (response.ok) {
          DemoToast.success('Book returned successfully!');
          return true;
        } else {
          const error = await response.json();
          DemoToast.error(error.detail || 'Failed to return book');
          return false;
        }
      } catch (error) {
        console.error('Failed to return book:', error);
        DemoToast.error('Failed to return book');
        return false;
      }
    },
  },
  
  // Stats helpers
  async loadStats() {
    try {
      const [health, books] = await Promise.all([
        fetch('/api/v1/health').then(r => r.json()).catch(() => null),
        fetch('/demo/library/books').then(r => r.json()).catch(() => null),
      ]);
      
      return {
        health: health?.status === 'healthy' ? 'healthy' : 'unhealthy',
        totalBooks: books?.books?.length || 0,
        availableBooks: books?.books?.filter(b => b.available).length || 0,
        checkedOutBooks: books?.books?.filter(b => !b.available).length || 0,
      };
    } catch (error) {
      console.error('Failed to load stats:', error);
      return null;
    }
  },
  
  // Initialize feature-specific functionality
  init() {
    // Library feature initialization is handled in library.js
    // This can be extended for other features
  },
};

// Export to window
window.DemoFeatures = DemoFeatures;


// Library-specific functionality for demo pages

const DemoLibrary = {
  API_BASE: '/demo/library',
  
  async loadBooks() {
    try {
      const response = await fetch(`${this.API_BASE}/books`);
      const data = await response.json();
      return data.books || [];
    } catch (error) {
      console.error('Failed to load books:', error);
      DemoToast.error('Failed to load books');
      return [];
    }
  },
  
  displayBooks(books, container) {
    if (!container) return;
    
    if (books.length === 0) {
      container.innerHTML = '<p class="text-muted">No books found</p>';
      return;
    }
    
    container.innerHTML = books.map(book => `
      <div class="card book-card ${book.available ? 'book-available' : 'book-checked-out'}">
        <div class="card-body">
          <div class="row align-items-center">
            <div class="col-md-8">
              <h5 class="card-title">${DemoUtils.escapeHtml(book.title)}</h5>
              <p class="card-text">
                <strong>Author:</strong> ${DemoUtils.escapeHtml(book.author || 'Unknown')}<br>
                <strong>ISBN:</strong> ${DemoUtils.escapeHtml(book.isbn || 'N/A')}<br>
                <span class="badge ${book.available ? 'badge-success' : 'badge-danger'}">
                  ${book.available ? 'Available' : 'Checked Out'}
                </span>
              </p>
            </div>
            <div class="col-md-4 text-end action-buttons">
              ${this.getActionButtons(book)}
            </div>
          </div>
        </div>
      </div>
    `).join('');
  },
  
  getActionButtons(book) {
    const userId = window.DEMO_USER?.id;
    
    if (!userId) {
      return '<p class="text-muted">Login to checkout books</p>';
    }
    
    if (book.available) {
      return `
        <button class="btn btn-primary btn-sm" onclick="DemoLibrary.checkoutBook('${book.id}')">
          <i class="fas fa-book-reader me-1"></i>Check Out
        </button>
      `;
    } else {
      return `
        <button class="btn btn-success btn-sm" onclick="DemoLibrary.returnBook('${book.id}')">
          <i class="fas fa-undo me-1"></i>Return
        </button>
      `;
    }
  },
  
  async checkoutBook(bookId) {
    try {
      const response = await fetch(`${this.API_BASE}/books/${bookId}/checkout`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
      
      if (response.ok) {
        DemoToast.success('Book checked out successfully!');
        this.refreshBooks();
        if (window.loadMyBooks) {
          window.loadMyBooks();
        }
      } else {
        const error = await response.json();
        DemoToast.error(error.detail || 'Failed to checkout book');
      }
    } catch (error) {
      console.error('Failed to checkout book:', error);
      DemoToast.error('Failed to checkout book');
    }
  },
  
  async returnBook(bookId) {
    try {
      const response = await fetch(`${this.API_BASE}/books/${bookId}/return`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
      
      if (response.ok) {
        DemoToast.success('Book returned successfully!');
        this.refreshBooks();
        if (window.loadMyBooks) {
          window.loadMyBooks();
        }
      } else {
        const error = await response.json();
        DemoToast.error(error.detail || 'Failed to return book');
      }
    } catch (error) {
      console.error('Failed to return book:', error);
      DemoToast.error('Failed to return book');
    }
  },
  
  async loadMyBooks(userId) {
    try {
      const response = await fetch(`${this.API_BASE}/users/${userId}/books`);
      const data = await response.json();
      return data.books || [];
    } catch (error) {
      console.error('Failed to load my books:', error);
      DemoToast.error('Failed to load your books');
      return [];
    }
  },
  
  displayMyBooks(books, container) {
    if (!container) return;
    
    if (books.length === 0) {
      container.innerHTML = '<p class="text-muted">You have no borrowed books</p>';
      return;
    }
    
    container.innerHTML = books.map(book => `
      <div class="card mb-2">
        <div class="card-body p-2">
          <div class="d-flex justify-content-between align-items-center">
            <div>
              <strong>${DemoUtils.escapeHtml(book.title)}</strong><br>
              <small class="text-muted">${DemoUtils.escapeHtml(book.author || 'Unknown')}</small>
            </div>
            <button class="btn btn-sm btn-success" onclick="DemoLibrary.returnBook('${book.id}')">
              <i class="fas fa-undo me-1"></i>Return
            </button>
          </div>
        </div>
      </div>
    `).join('');
  },
  
  async searchBooks(query) {
    try {
      const response = await fetch(`${this.API_BASE}/search?q=${encodeURIComponent(query)}`);
      const data = await response.json();
      return data.books || [];
    } catch (error) {
      console.error('Failed to search books:', error);
      DemoToast.error('Failed to search books');
      return [];
    }
  },
  
  async addBook(bookData) {
    try {
      const response = await fetch(`${this.API_BASE}/books`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(bookData),
      });
      
      if (response.ok) {
        DemoToast.success('Book added successfully!');
        return true;
      } else {
        const error = await response.json();
        DemoToast.error(error.detail || 'Failed to add book');
        return false;
      }
    } catch (error) {
      console.error('Failed to add book:', error);
      DemoToast.error('Failed to add book');
      return false;
    }
  },
  
  refreshBooks() {
    if (window.loadBooks) {
      window.loadBooks();
    }
  },
  
  init() {
    // Initialize library-specific functionality
    const searchBtn = document.getElementById('search-btn');
    const searchQuery = document.getElementById('search-query');
    
    if (searchBtn && searchQuery) {
      searchBtn.addEventListener('click', async () => {
        const query = searchQuery.value.trim();
        if (!query) {
          this.refreshBooks();
          return;
        }
        
        const books = await this.searchBooks(query);
        const container = document.getElementById('books-list');
        this.displayBooks(books, container);
      });
      
      searchQuery.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
          searchBtn.click();
        }
      });
    }
  },
};

// Export to window
window.DemoLibrary = DemoLibrary;

// Initialize on DOM ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    DemoLibrary.init();
  });
} else {
  DemoLibrary.init();
}


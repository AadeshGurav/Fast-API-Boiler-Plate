// File processing and manipulation functionality for demo pages

const DemoFilesPlay = {
  API_BASE: '/api/v1/files',
  PLAY_API_BASE: '/demo/files/play/api',
  
  getAuthHeaders() {
    // Cookies are automatically sent by browser
    // Optionally add Authorization header as fallback for API clients
    const token = (window.DemoAuth && window.DemoAuth.getAccessToken()) || null;
    if (token) {
      return {
        'Authorization': `Bearer ${token}`,
      };
    }
    return {};
  },
  
  getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
    return null;
  },
  
  async loadAndProcessFile(fileId) {
    try {
      const infoDiv = document.getElementById('file-info');
      const contentDiv = document.getElementById('file-content');
      
      infoDiv.innerHTML = '<div class="text-center"><i class="fas fa-spinner fa-spin"></i> Loading...</div>';
      contentDiv.innerHTML = '<div class="text-center"><i class="fas fa-spinner fa-spin"></i> Loading...</div>';
      
      const response = await fetch(`${this.PLAY_API_BASE}/${fileId}/read`, {
        headers: this.getAuthHeaders(),
      });
      
      if (!response.ok) {
        throw new Error('Failed to load file');
      }
      
      const data = await response.json();
      
      this.displayFileInfo(data);
      this.displayFileContent(data);
      
    } catch (error) {
      console.error('Failed to load file:', error);
      if (window.DemoToast) {
        DemoToast.error('Failed to load file');
      }
      document.getElementById('file-info').innerHTML = 
        '<div class="alert alert-danger">Failed to load file</div>';
      document.getElementById('file-content').innerHTML = 
        '<div class="alert alert-danger">Failed to load file</div>';
    }
  },
  
  displayFileInfo(data) {
    const infoDiv = document.getElementById('file-info');
    
    let infoHtml = `
      <table class="table table-sm">
        <tr><th>Filename:</th><td>${this.escapeHtml(data.filename)}</td></tr>
        <tr><th>Type:</th><td>${this.escapeHtml(data.content_type)}</td></tr>
        <tr><th>Size:</th><td>${this.formatFileSize(data.size)}</td></tr>
    `;
    
    if (data.is_text) {
      infoHtml += `
        <tr><th>Lines:</th><td>${data.line_count || 0}</td></tr>
        <tr><th>Words:</th><td>${data.word_count || 0}</td></tr>
        <tr><th>Characters:</th><td>${data.char_count || 0}</td></tr>
      `;
    }
    
    if (data.is_image) {
      infoHtml += `
        <tr><th>Dimensions:</th><td>${data.image_width || 'N/A'} x ${data.image_height || 'N/A'}</td></tr>
        <tr><th>Format:</th><td>${data.image_format || 'N/A'}</td></tr>
        <tr><th>Mode:</th><td>${data.image_mode || 'N/A'}</td></tr>
      `;
    }
    
    if (data.is_json && data.json_keys) {
      infoHtml += `
        <tr><th>JSON Keys:</th><td>${data.json_keys.join(', ')}</td></tr>
      `;
    }
    
    infoHtml += '</table>';
    
    infoDiv.innerHTML = infoHtml;
  },
  
  displayFileContent(data) {
    const contentDiv = document.getElementById('file-content');
    
    if (data.error) {
      contentDiv.innerHTML = `<div class="alert alert-warning">${this.escapeHtml(data.error)}</div>`;
      return;
    }
    
    if (data.is_text && data.text_content) {
      contentDiv.innerHTML = `
        <pre class="bg-light p-3 rounded" style="max-height: 500px; overflow-y: auto;"><code>${this.escapeHtml(data.text_content)}</code></pre>
      `;
    } else if (data.is_image && data.image_base64) {
      contentDiv.innerHTML = `
        <img src="${data.image_base64}" class="img-fluid" alt="${this.escapeHtml(data.filename)}">
      `;
    } else if (data.is_json && data.json_content) {
      contentDiv.innerHTML = `
        <pre class="bg-light p-3 rounded" style="max-height: 500px; overflow-y: auto;"><code>${JSON.stringify(data.json_content, null, 2)}</code></pre>
      `;
    } else {
      contentDiv.innerHTML = `
        <div class="alert alert-info">
          <i class="fas fa-info-circle me-2"></i>
          Content preview not available for this file type. 
          <a href="${this.API_BASE}/${data.file_id}" class="alert-link" download>Download file</a> to view.
        </div>
      `;
    }
  },
  
  async transformFile(fileId, transformType) {
    try {
      const resultDiv = document.getElementById('transformation-result');
      resultDiv.innerHTML = '<div class="text-center"><i class="fas fa-spinner fa-spin"></i> Processing...</div>';
      
      const response = await fetch(`${this.PLAY_API_BASE}/${fileId}/transform`, {
        method: 'POST',
        headers: {
          ...this.getAuthHeaders(),
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ transform_type: transformType }),
      });
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Transformation failed');
      }
      
      const data = await response.json();
      
      resultDiv.innerHTML = `
        <div class="alert alert-success">
          <h6>Transformation: ${this.escapeHtml(transformType)}</h6>
          <p><strong>Original length:</strong> ${data.original_length} characters</p>
          <p><strong>Transformed length:</strong> ${data.transformed_length} characters</p>
          <hr>
          <pre class="bg-light p-3 rounded mt-2" style="max-height: 300px; overflow-y: auto;">${this.escapeHtml(data.transformed_content)}</pre>
        </div>
      `;
      
    } catch (error) {
      console.error('Failed to transform file:', error);
      const resultDiv = document.getElementById('transformation-result');
      resultDiv.innerHTML = `<div class="alert alert-danger">${this.escapeHtml(error.message)}</div>`;
      if (window.DemoToast) {
        DemoToast.error('Transformation failed');
      }
    }
  },
  
  formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  },
  
  escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  },
};

// Export to window
window.DemoFilesPlay = DemoFilesPlay;


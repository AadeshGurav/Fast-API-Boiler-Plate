// File upload and management functionality for demo pages

const DemoFiles = {
  API_BASE: '/api/v1/files',
  CHUNK_SIZE: 5 * 1024 * 1024, // 5MB chunks
  
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
  
  async loadFiles() {
    try {
      const response = await fetch(`${this.API_BASE}/?page=1&page_size=100`, {
        headers: this.getAuthHeaders(),
      });
      
      if (!response.ok) {
        throw new Error('Failed to load files');
      }
      
      const data = await response.json();
      return data.files || [];
    } catch (error) {
      console.error('Failed to load files:', error);
      if (window.DemoToast) {
        DemoToast.error('Failed to load files');
      }
      return [];
    }
  },
  
  async uploadFile(file) {
    try {
      this.showUploadProgress(0, `Uploading ${file.name}...`);
      
      if (file.size > this.CHUNK_SIZE) {
        return await this.uploadChunked(file);
      }
      
      const formData = new FormData();
      formData.append('file', file);
      formData.append('filename', file.name);
      formData.append('content_type', file.type || 'application/octet-stream');
      
      const xhr = new XMLHttpRequest();
      
      return new Promise((resolve, reject) => {
        xhr.upload.addEventListener('progress', (e) => {
          if (e.lengthComputable) {
            const percentComplete = (e.loaded / e.total) * 100;
            this.updateUploadProgress(percentComplete, `Uploading ${file.name}...`);
          }
        });
        
        xhr.addEventListener('load', () => {
          if (xhr.status === 200) {
            this.hideUploadProgress();
            if (window.DemoToast) {
              DemoToast.success(`File ${file.name} uploaded successfully!`);
            }
            resolve(JSON.parse(xhr.responseText));
          } else {
            this.hideUploadProgress();
            const error = JSON.parse(xhr.responseText);
            if (window.DemoToast) {
              DemoToast.error(error.detail || 'Upload failed');
            }
            reject(new Error(error.detail || 'Upload failed'));
          }
        });
        
        xhr.addEventListener('error', () => {
          this.hideUploadProgress();
          if (window.DemoToast) {
            DemoToast.error('Upload failed');
          }
          reject(new Error('Upload failed'));
        });
        
        xhr.open('POST', `${this.API_BASE}/upload`);
        const headers = this.getAuthHeaders();
        Object.keys(headers).forEach(key => {
          xhr.setRequestHeader(key, headers[key]);
        });
        xhr.send(formData);
      });
    } catch (error) {
      console.error('Failed to upload file:', error);
      this.hideUploadProgress();
      if (window.DemoToast) {
        DemoToast.error('Failed to upload file');
      }
      throw error;
    }
  },
  
  async uploadChunked(file) {
    try {
      const uploadId = this.generateUploadId();
      const totalChunks = Math.ceil(file.size / this.CHUNK_SIZE);
      
      this.showUploadProgress(0, `Uploading ${file.name} (chunked)...`);
      
      for (let chunkNumber = 1; chunkNumber <= totalChunks; chunkNumber++) {
        const start = (chunkNumber - 1) * this.CHUNK_SIZE;
        const end = Math.min(start + this.CHUNK_SIZE, file.size);
        const chunk = file.slice(start, end);
        
        const formData = new FormData();
        formData.append('chunk', chunk);
        formData.append('upload_id', uploadId);
        formData.append('chunk_number', chunkNumber);
        formData.append('total_chunks', totalChunks);
        formData.append('chunk_size', chunk.size);
        formData.append('total_size', file.size);
        formData.append('filename', file.name);
        formData.append('content_type', file.type || 'application/octet-stream');
        
        const response = await fetch(`${this.API_BASE}/upload/chunk`, {
          method: 'POST',
          headers: this.getAuthHeaders(),
          body: formData,
        });
        
        if (!response.ok) {
          throw new Error(`Failed to upload chunk ${chunkNumber}`);
        }
        
        const percentComplete = (chunkNumber / totalChunks) * 100;
        this.updateUploadProgress(percentComplete, `Uploading chunk ${chunkNumber}/${totalChunks}...`);
      }
      
      const completeResponse = await fetch(
        `${this.API_BASE}/upload/chunk/complete?upload_id=${uploadId}`,
        {
          method: 'POST',
          headers: this.getAuthHeaders(),
        }
      );
      
      if (!completeResponse.ok) {
        throw new Error('Failed to complete upload');
      }
      
      this.hideUploadProgress();
      const result = await completeResponse.json();
      
      if (window.DemoToast) {
        DemoToast.success(`File ${file.name} uploaded successfully!`);
      }
      
      return result;
    } catch (error) {
      console.error('Failed to upload chunked file:', error);
      this.hideUploadProgress();
      if (window.DemoToast) {
        DemoToast.error('Failed to upload file');
      }
      throw error;
    }
  },
  
  generateUploadId() {
    return 'upload_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
  },
  
  showUploadProgress(percent, status) {
    const progressDiv = document.getElementById('upload-progress');
    if (!progressDiv) {
      return;
    }
    
    const progressBar = progressDiv.querySelector('.progress-bar');
    const statusSpan = document.getElementById('upload-status');
    
    progressDiv.style.display = 'block';
    if (progressBar) {
      progressBar.style.width = percent + '%';
    }
    if (statusSpan) {
      statusSpan.textContent = status;
    }
  },
  
  updateUploadProgress(percent, status) {
    const progressDiv = document.getElementById('upload-progress');
    if (!progressDiv) {
      return;
    }
    
    const progressBar = progressDiv.querySelector('.progress-bar');
    const statusSpan = document.getElementById('upload-status');
    
    if (progressBar) {
      progressBar.style.width = percent + '%';
    }
    if (statusSpan) {
      statusSpan.textContent = status;
    }
  },
  
  hideUploadProgress() {
    const progressDiv = document.getElementById('upload-progress');
    if (progressDiv) {
      progressDiv.style.display = 'none';
    }
  },
  
  renderFileList(files) {
    const container = document.getElementById('files-container');
    if (!container) return;
    
    if (files.length === 0) {
      container.innerHTML = '<div class="text-center py-5"><p class="text-muted">No files uploaded yet</p></div>';
      return;
    }
    
    container.innerHTML = `
      <div class="table-responsive">
        <table class="table table-hover">
          <thead>
            <tr>
              <th>Preview</th>
              <th>Name</th>
              <th>Size</th>
              <th>Type</th>
              <th>Tags</th>
              <th>Uploaded</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            ${files.map(file => this.renderFileRow(file)).join('')}
          </tbody>
        </table>
      </div>
    `;
  },
  
  renderFileGrid(files) {
    const container = document.getElementById('files-container');
    if (!container) return;
    
    if (files.length === 0) {
      container.innerHTML = '<div class="text-center py-5"><p class="text-muted">No files uploaded yet</p></div>';
      return;
    }
    
    container.innerHTML = `
      <div class="row g-3">
        ${files.map(file => this.renderFileCard(file)).join('')}
      </div>
    `;
  },
  
  renderFileRow(file) {
    const thumbnail = this.getFileThumbnail(file);
    const icon = this.getFileIcon(file);
    
    return `
      <tr>
        <td>${thumbnail || icon}</td>
        <td>
          <strong>${this.escapeHtml(file.filename)}</strong>
          ${file.version > 1 ? `<span class="badge bg-info ms-2">v${file.version}</span>` : ''}
        </td>
        <td>${this.formatFileSize(file.size)}</td>
        <td><span class="badge bg-secondary">${this.escapeHtml(file.content_type)}</span></td>
        <td>${file.tags && file.tags.length > 0 ? file.tags.map(tag => `<span class="badge bg-primary me-1">${this.escapeHtml(tag)}</span>`).join('') : '-'}</td>
        <td>${this.formatDate(file.created_at)}</td>
        <td>
          <div class="btn-group btn-group-sm">
            <button class="btn btn-outline-primary" onclick="DemoFiles.previewFile('${file.file_id}')" title="Preview">
              <i class="fas fa-eye"></i>
            </button>
            <button class="btn btn-outline-info" onclick="DemoFiles.showFileDetails('${file.file_id}')" title="Details">
              <i class="fas fa-info-circle"></i>
            </button>
            <a href="${this.API_BASE}/${file.file_id}" class="btn btn-outline-success" title="Download" download>
              <i class="fas fa-download"></i>
            </a>
            <button class="btn btn-outline-danger" onclick="DemoFiles.deleteFile('${file.file_id}')" title="Delete">
              <i class="fas fa-trash"></i>
            </button>
          </div>
        </td>
      </tr>
    `;
  },
  
  renderFileCard(file) {
    const thumbnail = this.getFileThumbnail(file);
    const icon = this.getFileIcon(file);
    
    return `
      <div class="col-md-3 col-sm-6">
        <div class="card file-card h-100">
          <div class="card-img-top file-thumbnail">
            ${thumbnail || `<div class="file-icon-placeholder">${icon}</div>`}
          </div>
          <div class="card-body">
            <h6 class="card-title">${this.escapeHtml(file.filename)}</h6>
            <p class="card-text small text-muted">
              ${this.formatFileSize(file.size)}<br>
              ${this.escapeHtml(file.content_type)}<br>
              ${this.formatDate(file.created_at)}
            </p>
            ${file.tags && file.tags.length > 0 ? `<div class="mb-2">${file.tags.map(tag => `<span class="badge bg-primary me-1">${this.escapeHtml(tag)}</span>`).join('')}</div>` : ''}
            ${file.version > 1 ? `<span class="badge bg-info">v${file.version}</span>` : ''}
          </div>
          <div class="card-footer">
            <div class="btn-group btn-group-sm w-100">
              <button class="btn btn-outline-primary" onclick="DemoFiles.previewFile('${file.file_id}')" title="Preview">
                <i class="fas fa-eye"></i>
              </button>
              <button class="btn btn-outline-info" onclick="DemoFiles.showFileDetails('${file.file_id}')" title="Details">
                <i class="fas fa-info-circle"></i>
              </button>
              <a href="${this.API_BASE}/${file.file_id}" class="btn btn-outline-success" title="Download" download>
                <i class="fas fa-download"></i>
              </a>
              <button class="btn btn-outline-danger" onclick="DemoFiles.deleteFile('${file.file_id}')" title="Delete">
                <i class="fas fa-trash"></i>
              </button>
            </div>
          </div>
        </div>
      </div>
    `;
  },
  
  getFileThumbnail(file) {
    if (file.thumbnail_urls && Object.keys(file.thumbnail_urls).length > 0) {
      const firstThumb = Object.values(file.thumbnail_urls)[0];
      return `<img src="${firstThumb}" alt="${this.escapeHtml(file.filename)}" class="img-thumbnail" style="max-width: 100px; max-height: 100px;">`;
    }
    if (file.content_type && file.content_type.startsWith('image/')) {
      return `<img src="${file.download_url}" alt="${this.escapeHtml(file.filename)}" class="img-thumbnail" style="max-width: 100px; max-height: 100px;">`;
    }
    return null;
  },
  
  getFileIcon(file) {
    const contentType = file.content_type || '';
    if (contentType.startsWith('image/')) {
      return '<i class="fas fa-image fa-2x text-primary"></i>';
    } else if (contentType.startsWith('video/')) {
      return '<i class="fas fa-video fa-2x text-danger"></i>';
    } else if (contentType.startsWith('audio/')) {
      return '<i class="fas fa-music fa-2x text-warning"></i>';
    } else if (contentType.includes('pdf')) {
      return '<i class="fas fa-file-pdf fa-2x text-danger"></i>';
    } else if (contentType.startsWith('text/')) {
      return '<i class="fas fa-file-alt fa-2x text-info"></i>';
    } else {
      return '<i class="fas fa-file fa-2x text-secondary"></i>';
    }
  },
  
  async previewFile(fileId) {
    try {
      const modal = new bootstrap.Modal(document.getElementById('preview-modal'));
      const title = document.getElementById('preview-title');
      const body = document.getElementById('preview-body');
      const downloadLink = document.getElementById('download-link');
      
      title.textContent = 'Loading preview...';
      body.innerHTML = '<div class="text-center"><i class="fas fa-spinner fa-spin fa-2x"></i><p>Loading...</p></div>';
      
      modal.show();
      
      const metadataResponse = await fetch(`${this.API_BASE}/${fileId}/metadata`, {
        headers: this.getAuthHeaders(),
      });
      
      if (!metadataResponse.ok) {
        throw new Error('Failed to load file metadata');
      }
      
      const fileData = await metadataResponse.json();
      title.textContent = this.escapeHtml(fileData.filename);
      downloadLink.href = `${this.API_BASE}/${fileId}`;
      
      if (fileData.content_type && fileData.content_type.startsWith('image/')) {
        body.innerHTML = `<img src="${fileData.download_url}" class="img-fluid" alt="${this.escapeHtml(fileData.filename)}">`;
      } else if (fileData.content_type && fileData.content_type.startsWith('text/')) {
        const contentResponse = await fetch(`${this.API_BASE}/${fileId}`, {
          headers: this.getAuthHeaders(),
        });
        if (contentResponse.ok) {
          const textContent = await contentResponse.text();
          body.innerHTML = `<pre class="bg-light p-3 rounded"><code>${this.escapeHtml(textContent)}</code></pre>`;
        } else {
          body.innerHTML = '<div class="alert alert-warning">Could not load text content</div>';
        }
      } else {
        body.innerHTML = `
          <div class="text-center">
            <i class="fas fa-file fa-4x text-muted mb-3"></i>
            <p class="text-muted">Preview not available for this file type</p>
            <p><strong>Type:</strong> ${this.escapeHtml(fileData.content_type)}</p>
            <p><strong>Size:</strong> ${this.formatFileSize(fileData.size)}</p>
          </div>
        `;
      }
    } catch (error) {
      console.error('Failed to preview file:', error);
      const body = document.getElementById('preview-body');
      if (body) {
        body.innerHTML = '<div class="alert alert-danger">Failed to load preview</div>';
      }
      if (window.DemoToast) {
        DemoToast.error('Failed to preview file');
      }
    }
  },
  
  async showFileDetails(fileId) {
    try {
      const modal = new bootstrap.Modal(document.getElementById('details-modal'));
      const body = document.getElementById('details-body');
      
      body.innerHTML = '<div class="text-center"><i class="fas fa-spinner fa-spin fa-2x"></i><p>Loading...</p></div>';
      modal.show();
      
      const response = await fetch(`${this.API_BASE}/${fileId}/metadata`, {
        headers: this.getAuthHeaders(),
      });
      
      if (!response.ok) {
        throw new Error('Failed to load file details');
      }
      
      const file = await response.json();
      
      const versionsResponse = await fetch(`${this.API_BASE}/${fileId}/versions`, {
        headers: this.getAuthHeaders(),
      });
      const versionsData = versionsResponse.ok ? await versionsResponse.json() : [];
      
      body.innerHTML = `
        <div class="file-details">
          <div class="mb-3">
            <strong>Filename:</strong> ${this.escapeHtml(file.filename)}
          </div>
          <div class="mb-3">
            <strong>Size:</strong> ${this.formatFileSize(file.size)}
          </div>
          <div class="mb-3">
            <strong>Type:</strong> ${this.escapeHtml(file.content_type)}
          </div>
          <div class="mb-3">
            <strong>Version:</strong> ${file.version}
          </div>
          <div class="mb-3">
            <strong>Uploaded:</strong> ${this.formatDate(file.created_at)}
          </div>
          <div class="mb-3">
            <strong>Last Updated:</strong> ${this.formatDate(file.updated_at)}
          </div>
          <div class="mb-3">
            <strong>Tags:</strong>
            <div id="tags-display" class="mt-2">
              ${file.tags && file.tags.length > 0 ? 
                file.tags.map(tag => `<span class="badge bg-primary me-1">${this.escapeHtml(tag)}</span>`).join('') :
                '<span class="text-muted">No tags</span>'}
            </div>
            <input type="text" class="form-control mt-2" id="tags-input" 
                   placeholder="Comma-separated tags" value="${file.tags ? file.tags.join(', ') : ''}">
          </div>
          <div class="mb-3">
            <strong>Metadata:</strong>
            <pre class="bg-light p-2 rounded mt-2" style="max-height: 200px; overflow-y: auto;">${JSON.stringify(file.metadata || {}, null, 2)}</pre>
          </div>
          ${versionsData.length > 1 ? `
            <div class="mb-3">
              <strong>Versions (${versionsData.length}):</strong>
              <ul class="list-group mt-2">
                ${versionsData.map(v => `
                  <li class="list-group-item d-flex justify-content-between">
                    <span>Version ${v.version} - ${this.formatFileSize(v.size)}</span>
                    <span class="text-muted">${this.formatDate(v.created_at)}</span>
                  </li>
                `).join('')}
              </ul>
            </div>
          ` : ''}
        </div>
      `;
      
      document.getElementById('update-metadata-btn').onclick = () => {
        this.updateFileMetadata(fileId);
      };
    } catch (error) {
      console.error('Failed to load file details:', error);
      if (body) {
        body.innerHTML = '<div class="alert alert-danger">Failed to load file details</div>';
      }
      if (window.DemoToast) {
        DemoToast.error('Failed to load file details');
      }
    }
  },
  
  async updateFileMetadata(fileId) {
    try {
      const tagsInput = document.getElementById('tags-input');
      const tags = tagsInput ? tagsInput.value.split(',').map(t => t.trim()).filter(t => t) : [];
      
      const response = await fetch(`${this.API_BASE}/${fileId}`, {
        method: 'PUT',
        headers: {
          ...this.getAuthHeaders(),
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ tags }),
      });
      
      if (response.ok) {
        if (window.DemoToast) {
          DemoToast.success('File metadata updated successfully!');
        }
        bootstrap.Modal.getInstance(document.getElementById('details-modal')).hide();
        if (window.loadFiles) {
          window.loadFiles();
        }
      } else {
        const error = await response.json();
        if (window.DemoToast) {
          DemoToast.error(error.detail || 'Failed to update metadata');
        }
      }
    } catch (error) {
      console.error('Failed to update metadata:', error);
      if (window.DemoToast) {
        DemoToast.error('Failed to update metadata');
      }
    }
  },
  
  async deleteFile(fileId) {
    if (!confirm('Are you sure you want to delete this file?')) {
      return;
    }
    
    try {
      const response = await fetch(`${this.API_BASE}/${fileId}?hard_delete=false`, {
        method: 'DELETE',
        headers: this.getAuthHeaders(),
      });
      
      if (response.ok) {
        if (window.DemoToast) {
          DemoToast.success('File deleted successfully!');
        }
        if (window.loadFiles) {
          window.loadFiles();
        }
      } else {
        const error = await response.json();
        if (window.DemoToast) {
          DemoToast.error(error.detail || 'Failed to delete file');
        }
      }
    } catch (error) {
      console.error('Failed to delete file:', error);
      if (window.DemoToast) {
        DemoToast.error('Failed to delete file');
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
  
  formatDate(dateString) {
    if (!dateString) return 'Unknown';
    const date = new Date(dateString);
    return date.toLocaleString();
  },
  
  escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  },
  
};

// Export to window
window.DemoFiles = DemoFiles;


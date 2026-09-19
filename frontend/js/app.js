/**
 * LUMA Frontend Application Logic
 * Distributed AI Image Generation System
 */

// Configure Backend API Base URL
// In production behind Nginx reverse proxy, '/api' routes directly to the backend.
// When testing standalone or direct cross-origin, fallback to backend URL.
const API_BASE = window.LUMA_API_URL || 
  (window.location.protocol === 'file:' ? 'http://localhost:5000/api' : '/api');

// Storage Keys
const TOKEN_KEY = 'luma_jwt_token';
const USER_KEY = 'luma_user_data';

/* ============================================================
   Authentication & Token Management
   ============================================================ */
function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

function getUser() {
  const user = localStorage.getItem(USER_KEY);
  try {
    return user ? JSON.parse(user) : null;
  } catch (e) {
    return null;
  }
}

function setAuth(token, user) {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

function clearAuth() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

function isAuthenticated() {
  return !!getToken();
}

function getAuthHeaders() {
  const token = getToken();
  return {
    'Content-Type': 'application/json',
    ...(token ? { 'Authorization': `Bearer ${token}` } : {})
  };
}

/**
 * Safely parse JSON response and prevent "Unexpected token <" errors
 * when server returns HTML error pages.
 */
async function parseJsonResponse(res, fallbackErrMsg = 'Request failed') {
  const contentType = res.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    return await res.json();
  }
  const rawText = await res.text();
  throw new Error(`Server returned unexpected response (${res.status}): ${rawText.slice(0, 100) || fallbackErrMsg}`);
}

function checkAuthGuard() {
  const currentPage = window.location.pathname.split('/').pop() || 'index.html';
  const isLoginPage = currentPage === 'login.html';

  if (!isAuthenticated() && !isLoginPage) {
    window.location.href = 'login.html';
  } else if (isAuthenticated() && isLoginPage) {
    window.location.href = 'index.html';
  }
}

function updateNavUser() {
  const userDisplay = document.getElementById('navUserDisplay');
  const user = getUser();
  if (userDisplay && user) {
    userDisplay.textContent = user.username || 'User';
  }

  const logoutBtn = document.getElementById('logoutBtn');
  if (logoutBtn) {
    logoutBtn.addEventListener('click', (e) => {
      e.preventDefault();
      clearAuth();
      window.location.href = 'login.html';
    });
  }
}

/* ============================================================
   Toast / Notification Helpers
   ============================================================ */
function showAlert(message, type = 'danger') {
  const alertContainer = document.getElementById('alertContainer');
  if (!alertContainer) return;

  const alertEl = document.createElement('div');
  alertEl.className = `alert alert-${type} alert-dismissible fade show glass-card shadow-sm mb-3`;
  alertEl.role = 'alert';
  alertEl.innerHTML = `
    <div class="d-flex align-items-center">
      <i class="bi ${type === 'success' ? 'bi-check-circle-fill text-success' : 'bi-exclamation-triangle-fill text-danger'} me-2 fs-5"></i>
      <div>${message}</div>
    </div>
    <button type="button" class="btn-close btn-close-white" data-bs-dismiss="alert" aria-label="Close"></button>
  `;
  alertContainer.innerHTML = '';
  alertContainer.appendChild(alertEl);

  setTimeout(() => {
    if (alertEl.parentNode) {
      alertEl.classList.remove('show');
      setTimeout(() => alertEl.remove(), 200);
    }
  }, 6000);
}

/* ============================================================
   Login & Register Page Logic
   ============================================================ */
function initAuthPage() {
  const loginForm = document.getElementById('loginForm');
  const registerForm = document.getElementById('registerForm');
  const loginError = document.getElementById('loginError');
  const registerAlert = document.getElementById('registerAlert');

  if (loginForm) {
    loginForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const username = document.getElementById('loginUsername').value.trim();
      const password = document.getElementById('loginPassword').value;
      const submitBtn = loginForm.querySelector('button[type="submit"]');

      if (!username || !password) {
        if (loginError) loginError.textContent = 'Please enter both username and password';
        return;
      }

      submitBtn.disabled = true;
      submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Logging in...';
      if (loginError) loginError.textContent = '';

      try {
        const res = await fetch(`${API_BASE}/login`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username, password })
        });

        const data = await parseJsonResponse(res, 'Login failed');
        if (!res.ok) {
          throw new Error(data.message || data.error || 'Login failed');
        }

        setAuth(data.token, data.user);
        window.location.href = 'index.html';
      } catch (err) {
        if (loginError) loginError.textContent = err.message;
      } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i class="bi bi-box-arrow-in-right me-2"></i>Sign In';
      }
    });
  }

  if (registerForm) {
    registerForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const username = document.getElementById('regUsername').value.trim();
      const password = document.getElementById('regPassword').value;
      const confirmPassword = document.getElementById('regConfirmPassword').value;
      const submitBtn = registerForm.querySelector('button[type="submit"]');

      if (!username || !password) {
        if (registerAlert) {
          registerAlert.className = 'alert alert-danger py-2';
          registerAlert.textContent = 'All fields are required';
        }
        return;
      }

      if (password !== confirmPassword) {
        if (registerAlert) {
          registerAlert.className = 'alert alert-danger py-2';
          registerAlert.textContent = 'Passwords do not match';
        }
        return;
      }

      submitBtn.disabled = true;
      submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Registering...';
      if (registerAlert) registerAlert.textContent = '';

      try {
        const res = await fetch(`${API_BASE}/register`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username, password })
        });

        const data = await parseJsonResponse(res, 'Registration failed');
        if (!res.ok) {
          throw new Error(data.message || data.error || 'Registration failed');
        }

        if (registerAlert) {
          registerAlert.className = 'alert alert-success py-2';
          registerAlert.textContent = 'Account created successfully! Logging you in...';
        }

        // Auto login with new credentials
        const loginRes = await fetch(`${API_BASE}/login`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username, password })
        });
        const loginData = await loginRes.json();
        if (loginRes.ok && loginData.token) {
          setAuth(loginData.token, loginData.user);
          setTimeout(() => { window.location.href = 'index.html'; }, 1000);
        } else {
          // Switch to login tab
          setTimeout(() => {
            const loginTab = document.getElementById('tab-login-tab');
            if (loginTab) loginTab.click();
          }, 1500);
        }
      } catch (err) {
        if (registerAlert) {
          registerAlert.className = 'alert alert-danger py-2';
          registerAlert.textContent = err.message;
        }
      } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i class="bi bi-person-plus me-2"></i>Create Account';
      }
    });
  }
}

/* ============================================================
   Image Generation Page Logic (index.html)
   ============================================================ */
function initGeneratorPage() {
  let uploadedImageBase64 = null;
  let activeMode = 'txt2img'; // 'txt2img' or 'img2img'

  // Mode switching tabs
  const modeTxt2ImgBtn = document.getElementById('modeTxt2Img');
  const modeImg2ImgBtn = document.getElementById('modeImg2Img');
  const img2imgSection = document.getElementById('img2imgSection');

  if (modeTxt2ImgBtn && modeImg2ImgBtn) {
    modeTxt2ImgBtn.addEventListener('click', () => {
      activeMode = 'txt2img';
      modeTxt2ImgBtn.classList.add('active');
      modeImg2ImgBtn.classList.remove('active');
      if (img2imgSection) img2imgSection.classList.add('d-none');
    });

    modeImg2ImgBtn.addEventListener('click', () => {
      activeMode = 'img2img';
      modeImg2ImgBtn.classList.add('active');
      modeTxt2ImgBtn.classList.remove('active');
      if (img2imgSection) img2imgSection.classList.remove('d-none');
    });
  }

  // Sliders dynamic value display
  const stepsRange = document.getElementById('stepsRange');
  const stepsVal = document.getElementById('stepsVal');
  if (stepsRange && stepsVal) {
    stepsRange.addEventListener('input', () => stepsVal.textContent = stepsRange.value);
  }

  const cfgRange = document.getElementById('cfgRange');
  const cfgVal = document.getElementById('cfgVal');
  if (cfgRange && cfgVal) {
    cfgRange.addEventListener('input', () => cfgVal.textContent = parseFloat(cfgRange.value).toFixed(1));
  }

  const denoiseRange = document.getElementById('denoiseRange');
  const denoiseVal = document.getElementById('denoiseVal');
  if (denoiseRange && denoiseVal) {
    denoiseRange.addEventListener('input', () => denoiseVal.textContent = parseFloat(denoiseRange.value).toFixed(2));
  }

  // Preset Resolution handler
  const resPresets = document.querySelectorAll('.res-preset-btn');
  const widthInput = document.getElementById('widthInput');
  const heightInput = document.getElementById('heightInput');

  resPresets.forEach(btn => {
    btn.addEventListener('click', () => {
      resPresets.forEach(b => b.classList.remove('btn-primary', 'active'));
      resPresets.forEach(b => b.classList.add('btn-glass'));
      btn.classList.remove('btn-glass');
      btn.classList.add('btn-primary', 'active');

      const [w, h] = btn.dataset.res.split('x');
      if (widthInput) widthInput.value = w;
      if (heightInput) heightInput.value = h;
    });
  });

  // Random Seed Button
  const randomSeedBtn = document.getElementById('randomSeedBtn');
  const seedInput = document.getElementById('seedInput');
  if (randomSeedBtn && seedInput) {
    randomSeedBtn.addEventListener('click', () => {
      seedInput.value = -1;
    });
  }

  // Image Upload & Dropzone for img2img
  const dropzone = document.getElementById('dropzone');
  const imageFileInput = document.getElementById('imageFileInput');
  const dropzonePlaceholder = document.getElementById('dropzonePlaceholder');
  const dropzonePreviewWrapper = document.getElementById('dropzonePreviewWrapper');
  const dropzonePreviewImg = document.getElementById('dropzonePreviewImg');
  const removeUploadedImgBtn = document.getElementById('removeUploadedImgBtn');

  function handleImageFile(file) {
    if (!file || !file.type.startsWith('image/')) {
      showAlert('Please upload a valid image file (PNG, JPEG, WebP)', 'warning');
      return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
      uploadedImageBase64 = e.target.result;
      if (dropzonePreviewImg) dropzonePreviewImg.src = uploadedImageBase64;
      if (dropzonePlaceholder) dropzonePlaceholder.classList.add('d-none');
      if (dropzonePreviewWrapper) dropzonePreviewWrapper.classList.remove('d-none');
    };
    reader.readAsDataURL(file);
  }

  if (dropzone && imageFileInput) {
    dropzone.addEventListener('click', (e) => {
      if (e.target !== removeUploadedImgBtn && !removeUploadedImgBtn?.contains(e.target)) {
        imageFileInput.click();
      }
    });

    imageFileInput.addEventListener('change', (e) => {
      if (e.target.files && e.target.files[0]) {
        handleImageFile(e.target.files[0]);
      }
    });

    // Drag and drop events
    ['dragenter', 'dragover'].forEach(eventName => {
      dropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        dropzone.classList.add('dragover');
      });
    });

    ['dragleave', 'drop'].forEach(eventName => {
      dropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        dropzone.classList.remove('dragover');
      });
    });

    dropzone.addEventListener('drop', (e) => {
      if (e.dataTransfer.files && e.dataTransfer.files[0]) {
        handleImageFile(e.dataTransfer.files[0]);
      }
    });
  }

  if (removeUploadedImgBtn) {
    removeUploadedImgBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      uploadedImageBase64 = null;
      if (imageFileInput) imageFileInput.value = '';
      if (dropzonePreviewWrapper) dropzonePreviewWrapper.classList.add('d-none');
      if (dropzonePlaceholder) dropzonePlaceholder.classList.remove('d-none');
    });
  }

  // Generation Submit Form
  const generateForm = document.getElementById('generateForm');
  const generateSubmitBtn = document.getElementById('generateSubmitBtn');
  const resultInitialState = document.getElementById('resultInitialState');
  const resultLoadingState = document.getElementById('resultLoadingState');
  const resultSuccessState = document.getElementById('resultSuccessState');
  const resultImage = document.getElementById('resultImage');
  const downloadResultBtn = document.getElementById('downloadResultBtn');
  const copyPromptBtn = document.getElementById('copyPromptBtn');
  const resultPromptText = document.getElementById('resultPromptText');
  const resultMetaBadge = document.getElementById('resultMetaBadge');

  if (generateForm) {
    generateForm.addEventListener('submit', async (e) => {
      e.preventDefault();

      const prompt = document.getElementById('promptInput').value.trim();
      const negative_prompt = document.getElementById('negPromptInput').value.trim();
      const width = parseInt(document.getElementById('widthInput').value, 10) || 512;
      const height = parseInt(document.getElementById('heightInput').value, 10) || 512;
      const steps = parseInt(document.getElementById('stepsRange').value, 10) || 20;
      const cfg_scale = parseFloat(document.getElementById('cfgRange').value) || 7.0;
      const seed = parseInt(document.getElementById('seedInput').value, 10) || -1;
      const denoising_strength = parseFloat(document.getElementById('denoiseRange')?.value || '0.75');

      if (!prompt) {
        showAlert('Please provide a prompt description', 'warning');
        return;
      }

      if (activeMode === 'img2img' && !uploadedImageBase64) {
        showAlert('Please upload an initial image for Image-to-Image editing', 'warning');
        return;
      }

      // Prepare UI for generation
      generateSubmitBtn.disabled = true;
      generateSubmitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Generating AI Art...';

      if (resultInitialState) resultInitialState.classList.add('d-none');
      if (resultSuccessState) resultSuccessState.classList.add('d-none');
      if (resultLoadingState) resultLoadingState.classList.remove('d-none');

      const payload = {
        mode: activeMode,
        prompt: prompt,
        negative_prompt: negative_prompt,
        width: width,
        height: height,
        steps: steps,
        cfg_scale: cfg_scale,
        seed: seed,
        ...(activeMode === 'img2img' ? {
          init_image: uploadedImageBase64,
          denoising_strength: denoising_strength
        } : {})
      };

      try {
        const response = await fetch(`${API_BASE}/generate`, {
          method: 'POST',
          headers: getAuthHeaders(),
          body: JSON.stringify(payload)
        });

        if (response.status === 401) {
          clearAuth();
          window.location.href = 'login.html';
          return;
        }

        const data = await parseJsonResponse(response, 'Image generation failed');

        if (!response.ok) {
          throw new Error(data.message || data.error || 'Generation failed');
        }

        // Check if response is synchronous image or async job
        if (data.status === 'COMPLETED' || data.image_url || data.image_base64) {
          renderGenerationResult(data, prompt, `${width}x${height} • Steps: ${steps} • Seed: ${data.seed || seed}`);
        } else if (data.job_id && (data.status === 'PENDING' || data.status === 'PROCESSING')) {
          // Poll for completion
          await pollJobStatus(data.job_id, prompt, `${width}x${height} • Steps: ${steps}`);
        } else {
          renderGenerationResult(data, prompt, `${width}x${height}`);
        }

      } catch (err) {
        showAlert(err.message, 'danger');
        if (resultLoadingState) resultLoadingState.classList.add('d-none');
        if (resultInitialState) resultInitialState.classList.remove('d-none');
      } finally {
        generateSubmitBtn.disabled = false;
        generateSubmitBtn.innerHTML = '<i class="bi bi-stars me-2"></i>Generate Image';
      }
    });
  }

  // Polling helper for async jobs
  async function pollJobStatus(jobId, prompt, meta) {
    const maxAttempts = 40; // 40 * 2.5s = 100s timeout
    let attempts = 0;

    const pollInterval = setInterval(async () => {
      attempts++;
      try {
        const res = await fetch(`${API_BASE}/status/${jobId}`, {
          headers: getAuthHeaders()
        });
        const statusData = await parseJsonResponse(res, 'Failed to get job status');

        if (statusData.status === 'COMPLETED') {
          clearInterval(pollInterval);
          renderGenerationResult(statusData, prompt, meta);
        } else if (statusData.status === 'FAILED') {
          clearInterval(pollInterval);
          throw new Error(statusData.error_message || 'Image generation failed on server');
        } else if (attempts >= maxAttempts) {
          clearInterval(pollInterval);
          throw new Error('Image generation timed out. Please check history later.');
        }
      } catch (err) {
        clearInterval(pollInterval);
        showAlert(err.message, 'danger');
        if (resultLoadingState) resultLoadingState.classList.add('d-none');
        if (resultInitialState) resultInitialState.classList.remove('d-none');
      }
    }, 2500);
  }

  // Render completed result into preview container
  function renderGenerationResult(data, prompt, meta) {
    const imageUrl = data.image_url ? 
      (data.image_url.startsWith('http') ? data.image_url : `${API_BASE.replace('/api', '')}${data.image_url}`) : 
      (data.image_base64 ? `data:image/png;base64,${data.image_base64}` : '');

    if (resultImage) {
      resultImage.src = imageUrl;
    }
    if (resultPromptText) {
      resultPromptText.textContent = prompt;
    }
    if (resultMetaBadge) {
      resultMetaBadge.textContent = meta;
    }

    if (downloadResultBtn) {
      downloadResultBtn.onclick = () => {
        const a = document.createElement('a');
        a.href = imageUrl;
        a.download = `luma_${Date.now()}.png`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
      };
    }

    if (copyPromptBtn) {
      copyPromptBtn.onclick = () => {
        navigator.clipboard.writeText(prompt).then(() => {
          showAlert('Prompt copied to clipboard!', 'success');
        });
      };
    }

    if (resultLoadingState) resultLoadingState.classList.add('d-none');
    if (resultSuccessState) resultSuccessState.classList.remove('d-none');
  }
}

/* ============================================================
   History Page Logic (history.html)
   ============================================================ */
function initHistoryPage() {
  let currentPage = 1;
  const limit = 12;

  const historyGrid = document.getElementById('historyGrid');
  const historyLoading = document.getElementById('historyLoading');
  const historyEmpty = document.getElementById('historyEmpty');
  const prevPageBtn = document.getElementById('prevPageBtn');
  const nextPageBtn = document.getElementById('nextPageBtn');
  const pageIndicator = document.getElementById('pageIndicator');

  async function loadHistory(page = 1) {
    if (historyLoading) historyLoading.classList.remove('d-none');
    if (historyGrid) historyGrid.classList.add('d-none');
    if (historyEmpty) historyEmpty.classList.add('d-none');

    try {
      const res = await fetch(`${API_BASE}/history?page=${page}&limit=${limit}`, {
        headers: getAuthHeaders()
      });

      if (res.status === 401) {
        clearAuth();
        window.location.href = 'login.html';
        return;
      }

      const data = await parseJsonResponse(res, 'Failed to load history');
      if (!res.ok) {
        throw new Error(data.message || data.error || 'Failed to load history');
      }

      renderHistoryItems(data.items || data.generations || []);
      updatePagination(data.page || page, data.total_pages || 1, data.total || 0);

    } catch (err) {
      showAlert(err.message, 'danger');
    } finally {
      if (historyLoading) historyLoading.classList.add('d-none');
    }
  }

  function renderHistoryItems(items) {
    if (!historyGrid) return;
    historyGrid.innerHTML = '';

    if (items.length === 0) {
      if (historyEmpty) historyEmpty.classList.remove('d-none');
      return;
    }

    historyGrid.classList.remove('d-none');

    items.forEach(item => {
      const col = document.createElement('div');
      col.className = 'col-6 col-md-4 col-lg-3';

      const imageUrl = item.image_url ? 
        (item.image_url.startsWith('http') ? item.image_url : `${API_BASE.replace('/api', '')}${item.image_url}`) : 
        (item.image_base64 ? `data:image/png;base64,${item.image_base64}` : '');

      const dateStr = item.created_at ? new Date(item.created_at).toLocaleDateString() : '';
      const modeBadge = item.mode === 'img2img' ? 'Image2Image' : 'Text2Image';

      col.innerHTML = `
        <div class="history-card glass-card h-100 cursor-pointer" data-id="${item.id}">
          <div class="history-img-wrapper">
            <img src="${imageUrl}" alt="${item.prompt}" loading="lazy" onerror="this.src='data:image/svg+xml;utf8,<svg xmlns=\\'http://www.w3.org/2000/svg\\' width=\\'200\\' height=\\'200\\' fill=\\'%23334155\\'><rect width=\\'100%\\' height=\\'100%\\'/></svg>'">
            <span class="badge-mode">${modeBadge}</span>
          </div>
          <div class="p-3">
            <p class="text-truncate mb-1 fw-semibold small" title="${item.prompt}">${item.prompt}</p>
            <div class="d-flex justify-content-between align-items-center text-dim small">
              <span>${dateStr}</span>
              <button class="btn btn-sm btn-glass py-0 px-2 view-detail-btn" data-id="${item.id}">
                <i class="bi bi-eye"></i> View
              </button>
            </div>
          </div>
        </div>
      `;

      col.querySelector('.history-card').addEventListener('click', () => {
        openImageDetailModal(item, imageUrl);
      });

      historyGrid.appendChild(col);
    });
  }

  function updatePagination(page, totalPages, totalItems) {
    currentPage = page;
    if (pageIndicator) {
      pageIndicator.textContent = `Page ${page} of ${Math.max(1, totalPages)} (${totalItems} items)`;
    }
    if (prevPageBtn) {
      prevPageBtn.disabled = page <= 1;
    }
    if (nextPageBtn) {
      nextPageBtn.disabled = page >= totalPages;
    }
  }

  if (prevPageBtn) {
    prevPageBtn.addEventListener('click', () => {
      if (currentPage > 1) {
        loadHistory(currentPage - 1);
      }
    });
  }

  if (nextPageBtn) {
    nextPageBtn.addEventListener('click', () => {
      loadHistory(currentPage + 1);
    });
  }

  // Load first page
  loadHistory(1);
}

// Modal Details viewer
function openImageDetailModal(item, imageUrl) {
  let modalEl = document.getElementById('historyDetailModal');
  if (!modalEl) {
    modalEl = document.createElement('div');
    modalEl.className = 'modal fade';
    modalEl.id = 'historyDetailModal';
    modalEl.tabIndex = -1;
    modalEl.innerHTML = `
      <div class="modal-dialog modal-lg modal-dialog-centered">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title fw-bold"><i class="bi bi-image me-2 text-primary"></i>Image Details</h5>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
          </div>
          <div class="modal-body text-center">
            <img id="modalImage" src="" class="img-fluid rounded mb-3 shadow" style="max-height: 500px; object-fit: contain;">
            <div class="text-start glass-panel p-3">
              <h6 class="text-muted small text-uppercase fw-bold mb-1">Prompt</h6>
              <p id="modalPrompt" class="text-main mb-2"></p>
              <div id="modalParams" class="small text-muted"></div>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-glass" id="modalCopyBtn"><i class="bi bi-clipboard me-1"></i> Copy Prompt</button>
            <a href="" id="modalDownloadBtn" class="btn btn-gradient" download><i class="bi bi-download me-1"></i> Download</a>
          </div>
        </div>
      </div>
    `;
    document.body.appendChild(modalEl);
  }

  const modalImg = modalEl.querySelector('#modalImage');
  const modalPrompt = modalEl.querySelector('#modalPrompt');
  const modalParams = modalEl.querySelector('#modalParams');
  const modalDownloadBtn = modalEl.querySelector('#modalDownloadBtn');
  const modalCopyBtn = modalEl.querySelector('#modalCopyBtn');

  modalImg.src = imageUrl;
  modalPrompt.textContent = item.prompt;
  modalParams.innerHTML = `
    <span><strong>Mode:</strong> ${item.mode || 'txt2img'}</span> &bull; 
    <span><strong>Status:</strong> <span class="badge bg-success">${item.status || 'COMPLETED'}</span></span> &bull; 
    <span><strong>Created:</strong> ${new Date(item.created_at).toLocaleString()}</span>
  `;

  modalDownloadBtn.href = imageUrl;
  modalDownloadBtn.download = `luma_${item.id}.png`;
  modalCopyBtn.onclick = () => {
    navigator.clipboard.writeText(item.prompt).then(() => {
      showAlert('Prompt copied to clipboard!', 'success');
    });
  };

  const bsModal = new bootstrap.Modal(modalEl);
  bsModal.show();
}

/* ============================================================
   App Initialization on DOM Ready
   ============================================================ */
document.addEventListener('DOMContentLoaded', () => {
  checkAuthGuard();
  updateNavUser();

  const path = window.location.pathname.split('/').pop() || 'index.html';

  if (path === 'login.html') {
    initAuthPage();
  } else if (path === 'history.html') {
    initHistoryPage();
  } else {
    // index.html (Main Generator)
    initGeneratorPage();
  }
});

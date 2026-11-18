// Isolated from the existing single-image classifier's state and event handlers.
(() => {
  const input = document.querySelector('#batch-input');
  const dropzone = document.querySelector('#batch-dropzone');
  const organize = document.querySelector('#organize-button');
  const download = document.querySelector('#download-organized');
  const clear = document.querySelector('#batch-clear');
  const status = document.querySelector('#batch-status');
  const error = document.querySelector('#batch-error');
  const selection = document.querySelector('#batch-selection');
  const gallery = document.querySelector('#batch-gallery');
  const failures = document.querySelector('#batch-failures');
  const failureList = document.querySelector('#batch-failure-list');
  const percent = new Intl.NumberFormat('en', { style: 'percent', maximumFractionDigits: 1 });
  let files = [];
  let objectUrls = [];
  let busy = false;
  let hasResults = false;

  function showError(message = '') {
    error.textContent = message;
    error.hidden = !message;
  }

  function resetResults() {
    objectUrls.forEach(url => URL.revokeObjectURL(url));
    objectUrls = [];
    hasResults = false;
    failures.hidden = true;
    failureList.replaceChildren();
    gallery.querySelectorAll('.sport-group').forEach(group => {
      group.querySelector('.category-count').textContent = '0';
      const empty = document.createElement('p');
      empty.className = 'category-empty';
      empty.textContent = 'No images yet.';
      group.querySelector('.category-images').replaceChildren(empty);
    });
  }

  function controls() {
    input.disabled = busy;
    organize.disabled = busy || !files.length;
    clear.disabled = busy || !files.length;
    download.disabled = busy || !hasResults;
    gallery.setAttribute('aria-busy', String(busy));
  }

  function selectFiles(selected) {
    if (busy) return;
    const incoming = Array.from(selected);
    showError();
    if (incoming.length > 20) {
      showError('Choose up to 20 images per batch. Your previous selection is unchanged.');
      input.value = '';
      return;
    }
    if (incoming.reduce((sum, file) => sum + file.size, 0) > 50 * 1024 * 1024) {
      showError('The combined image size must be 50 MB or smaller. Your previous selection is unchanged.');
      input.value = '';
      return;
    }
    files = incoming;
    resetResults();
    selection.textContent = files.length ? `${files.length} images selected · ${(files.reduce((sum, file) => sum + file.size, 0) / 1024 / 1024).toFixed(1)} MB` : 'No images selected';
    status.textContent = files.length ? 'Ready to organize. Invalid images will be skipped and listed below.' : 'Select images to get started.';
    controls();
  }

  async function upload(url) {
    const form = new FormData();
    files.forEach(file => form.append('files', file));
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 300000);
    try {
      const response = await fetch(url, { method: 'POST', body: form, signal: controller.signal });
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(typeof payload.detail === 'string' ? payload.detail : 'The batch could not be processed. Please try again.');
      }
      // Read the body before clearing the timeout so stalled downloads are bounded too.
      return url.endsWith('/zip') ? { blob: await response.blob(), count: response.headers.get('X-Organized-Count'), failed: response.headers.get('X-Failed-Count') } : await response.json();
    } finally {
      clearTimeout(timeout);
    }
  }

  function render(data) {
    for (const group of gallery.querySelectorAll('.sport-group')) {
      const sport = group.dataset.sport;
      group.querySelector('.category-count').textContent = String(data.counts[sport]);
      if (data.counts[sport]) group.querySelector('.category-images').replaceChildren();
    }
    for (const result of data.results) {
      if (result.status === 'error') {
        const li = document.createElement('li');
        li.textContent = `${result.filename}: ${result.error}`;
        failureList.append(li);
        continue;
      }
      const sport = result.predicted_sport;
      const group = Array.from(gallery.querySelectorAll('.sport-group')).find(group => group.dataset.sport === sport);
      if (!group) continue;
      const card = document.createElement('figure');
      card.className = 'organized-card';
      const image = document.createElement('img');
      const url = URL.createObjectURL(files[result.index]);
      objectUrls.push(url);
      image.src = url;
      image.alt = result.filename;
      image.loading = 'lazy';
      const caption = document.createElement('figcaption');
      const name = document.createElement('strong');
      name.textContent = result.filename;
      const confidence = document.createElement('span');
      confidence.textContent = `${sport[0].toUpperCase() + sport.slice(1)} · ${percent.format(result.confidence)} confidence`;
      caption.append(name, confidence);
      card.append(image, caption);
      group.querySelector('.category-images').append(card);
    }
    failures.hidden = !data.failed;
    hasResults = data.succeeded > 0;
    status.textContent = `${data.succeeded} of ${data.total} images organized. ${data.failed} skipped.`;
  }

  function reportFailure(err) {
    showError(err.name === 'AbortError' ? 'The request timed out. Try a smaller batch.' : err instanceof TypeError ? 'Cannot reach the server. Check the connection and try again.' : err.message);
  }

  input.addEventListener('change', () => selectFiles(input.files));
  clear.addEventListener('click', () => { input.value = ''; selectFiles([]); });
  dropzone.addEventListener('dragover', event => { event.preventDefault(); if (!busy) dropzone.classList.add('drag-over'); });
  dropzone.addEventListener('dragleave', () => dropzone.classList.remove('drag-over'));
  dropzone.addEventListener('drop', event => { event.preventDefault(); dropzone.classList.remove('drag-over'); selectFiles(event.dataTransfer.files); });
  organize.addEventListener('click', async () => {
    if (busy || !files.length) return;
    resetResults();
    busy = true;
    controls();
    showError();
    status.textContent = 'Organizing your images… This may take a moment.';
    try { render(await upload('/api/organize')); }
    catch (err) { status.textContent = 'Organization did not complete. Please try again.'; reportFailure(err); }
    finally { busy = false; controls(); }
  });
  download.addEventListener('click', async () => {
    if (busy || !hasResults) return;
    busy = true;
    controls();
    showError();
    status.textContent = 'Preparing ZIP… Rechecking the original images without storing them.';
    try {
      const result = await upload('/api/organize/zip');
      const url = URL.createObjectURL(result.blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = 'sportsvision_organized.zip';
      document.body.append(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 60000);
      status.textContent = `ZIP download started: ${result.count} images organized, ${result.failed} skipped.`;
    } catch (err) { status.textContent = 'ZIP download failed. Your gallery is still available.'; reportFailure(err); }
    finally { busy = false; controls(); }
  });
  window.addEventListener('pagehide', () => objectUrls.forEach(url => URL.revokeObjectURL(url)));
})();

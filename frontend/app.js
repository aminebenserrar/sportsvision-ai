const input = document.querySelector('#file-input');
const dropzone = document.querySelector('#dropzone');
const preview = document.querySelector('#preview');
const prompt = document.querySelector('#upload-prompt');
const overlay = document.querySelector('#preview-overlay');
const filename = document.querySelector('#file-name');
const clearButton = document.querySelector('#clear-button');
const analyzeButton = document.querySelector('#analyze-button');
const errorMessage = document.querySelector('#error-message');
const resultsPanel = document.querySelector('#results-panel');
const resultStatus = document.querySelector('#result-status');
const emptyState = document.querySelector('#empty-state');
const prediction = document.querySelector('#prediction');
const percent = new Intl.NumberFormat('en', { style: 'percent', maximumFractionDigits: 1 });
let selectedFile = null;
let previewUrl = null;
let busy = false;
let selectionVersion = 0;

function showError(message) {
  errorMessage.textContent = message;
  errorMessage.hidden = !message;
}

function resetResults() {
  prediction.hidden = true;
  emptyState.hidden = false;
  resultStatus.textContent = 'AWAITING IMAGE';
}

function clearSelection() {
  selectionVersion += 1;
  if (previewUrl) URL.revokeObjectURL(previewUrl);
  previewUrl = null;
  selectedFile = null;
  input.value = '';
  preview.removeAttribute('src');
  preview.hidden = overlay.hidden = clearButton.hidden = true;
  prompt.hidden = false;
  filename.textContent = 'No image selected';
  analyzeButton.disabled = true;
  resetResults();
  showError('');
}

async function selectFile(file) {
  if (busy || !file) return;
  clearSelection();
  if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
    showError('Choose a JPEG, PNG, or WebP image.');
    return;
  }
  if (!file.size || file.size > 10 * 1024 * 1024) {
    showError(file.size ? 'Choose an image of 10 MB or less.' : 'This file is empty.');
    return;
  }
  const version = selectionVersion;
  const url = URL.createObjectURL(file);
  const image = new Image();
  image.src = url;
  try {
    await image.decode();
    if (version !== selectionVersion) { URL.revokeObjectURL(url); return; }
    if (image.naturalWidth * image.naturalHeight > 25_000_000) {
      throw new Error('Choose an image under 25 megapixels.');
    }
    previewUrl = url;
    selectedFile = file;
    preview.src = url;
    preview.hidden = overlay.hidden = clearButton.hidden = false;
    prompt.hidden = true;
    filename.textContent = `${file.name} · ${(file.size / (1024 * 1024)).toFixed(2)} MB`;
    analyzeButton.disabled = false;
    resultStatus.textContent = 'READY TO ANALYZE';
  } catch (error) {
    URL.revokeObjectURL(url);
    if (version === selectionVersion) showError(error.message.startsWith('Choose') ? error.message : 'This image could not be opened. Try another file.');
  }
}

input.addEventListener('change', () => selectFile(input.files[0]));
clearButton.addEventListener('click', clearSelection);
// Prevent the browser from navigating to an image dropped outside the target.
window.addEventListener('dragover', event => event.preventDefault());
window.addEventListener('drop', event => event.preventDefault());
dropzone.addEventListener('dragover', event => {
  event.preventDefault();
  if (!busy) dropzone.classList.add('drag-over');
});
dropzone.addEventListener('dragleave', () => dropzone.classList.remove('drag-over'));
dropzone.addEventListener('drop', event => {
  event.preventDefault();
  dropzone.classList.remove('drag-over');
  if (busy) return;
  if (event.dataTransfer.files.length !== 1) {
    showError('Please drop one image at a time.');
    return;
  }
  selectFile(event.dataTransfer.files[0]);
});

function renderResult(data) {
  document.querySelector('#predicted-sport').textContent = displayName(data.predicted_sport);
  document.querySelector('#confidence').textContent = percent.format(data.confidence);
  const container = document.querySelector('#probabilities');
  container.replaceChildren();
  // Keep the API's labels.json ordering; never sort the classes by confidence.
  for (const item of data.probabilities) {
    const row = document.createElement('div');
    row.className = `probability-row${item.sport === data.predicted_sport ? ' winner' : ''}`;
    const label = document.createElement('div');
    label.className = 'probability-label';
    const name = document.createElement('span');
    name.textContent = displayName(item.sport);
    const value = document.createElement('span');
    value.textContent = percent.format(item.probability);
    label.append(name, value);
    const track = document.createElement('div');
    track.className = 'bar-track';
    track.setAttribute('role', 'progressbar');
    track.setAttribute('aria-label', `${displayName(item.sport)} probability`);
    track.setAttribute('aria-valuemin', '0');
    track.setAttribute('aria-valuemax', '100');
    track.setAttribute('aria-valuenow', (item.probability * 100).toFixed(1));
    const fill = document.createElement('div');
    fill.className = 'bar-fill';
    fill.style.width = `${item.probability * 100}%`;
    track.append(fill);
    row.append(label, track);
    container.append(row);
  }
  emptyState.hidden = true;
  prediction.hidden = false;
  resultStatus.textContent = 'ANALYSIS COMPLETE';
}

function displayName(label) {
  return label.charAt(0).toUpperCase() + label.slice(1);
}

analyzeButton.addEventListener('click', async () => {
  if (!selectedFile || busy) return;
  busy = true;
  showError('');
  resetResults();
  input.disabled = clearButton.disabled = analyzeButton.disabled = true;
  resultsPanel.setAttribute('aria-busy', 'true');
  resultStatus.textContent = 'ANALYZING…';
  analyzeButton.classList.add('is-loading');
  document.querySelector('#button-label').textContent = 'Analyzing image…';
  document.querySelector('#button-icon').textContent = '◌';
  const form = new FormData();
  form.append('file', selectedFile);
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 120000);
  try {
    const response = await fetch('/api/predict', { method: 'POST', body: form, signal: controller.signal });
    const data = await response.json();
    if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'The server could not process this image.');
    renderResult(data);
  } catch (error) {
    resultStatus.textContent = 'TRY AGAIN';
    showError(error.name === 'AbortError' ? 'Analysis timed out. Please try again.' : error instanceof TypeError ? 'Cannot reach the server. Check that FastAPI is running and try again.' : error.message);
  } finally {
    clearTimeout(timer);
    busy = false;
    input.disabled = clearButton.disabled = analyzeButton.disabled = false;
    resultsPanel.setAttribute('aria-busy', 'false');
    analyzeButton.classList.remove('is-loading');
    document.querySelector('#button-label').textContent = 'Analyze Image';
    document.querySelector('#button-icon').textContent = '↗';
  }
});

resultStatus.setAttribute('role', 'status');
resultStatus.setAttribute('aria-live', 'polite');
window.addEventListener('pagehide', () => { if (previewUrl) URL.revokeObjectURL(previewUrl); });

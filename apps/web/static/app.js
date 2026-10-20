const form = document.getElementById('f');
const result = document.getElementById('result');
let poll = null;

const pageBody = document.getElementById('page-body');
const pageOutfit = document.getElementById('page-outfit');

function showPage(name) {
  pageBody.hidden = name !== 'body';
  pageOutfit.hidden = name !== 'outfit';
}

// Polled once on page load (not just assumed client-side) so a mid-flow
// browser refresh lands on whichever page actually matches server state,
// e.g. after a server restart cleared CURRENT_BODY.
async function refreshBodyStatus() {
  const resp = await fetch('/body_status', { cache: 'no-store' });
  const s = await resp.json();
  showPage(s.has_body ? 'outfit' : 'body');
}
refreshBodyStatus().catch(() => {
  document.getElementById('body-status-msg').textContent = '無法連線到伺服器';
});

const bodyForm = document.getElementById('body-form');
const bodyStatusMsg = document.getElementById('body-status-msg');
const bodyPreviewArea = document.getElementById('body-preview-area');
const bodyPreviewImg = document.getElementById('body-preview-img');

bodyForm.onsubmit = async (e) => {
  e.preventDefault();
  // Disable the button for the whole ~20s request -- without this a
  // double-click (or a submit fired while still mid-edit of a field) could
  // send two overlapping /fit_body calls; the server now rejects the second
  // one (409) either way, but this avoids the confusing 409 entirely and is
  // the more important half of the fix (a real 152cm/5kg body was produced
  // this way once, before the server-side guard existed).
  const submitBtn = bodyForm.querySelector('button[type="submit"]');
  submitBtn.disabled = true;
  bodyPreviewArea.hidden = true;
  bodyStatusMsg.textContent = '建立身體模型中，約需 20 秒...';
  try {
    const body = new URLSearchParams(new FormData(bodyForm));
    const resp = await fetch('/fit_body', { method: 'POST', body });
    if (!resp.ok) { bodyStatusMsg.textContent = '失敗：' + await resp.text(); return; }
    const { preview_image } = await resp.json();
    bodyStatusMsg.textContent = '';
    bodyPreviewImg.src = preview_image;
    bodyPreviewArea.hidden = false;
  } catch (error) {
    bodyStatusMsg.textContent = '連線失敗，請稍後重試';
  } finally {
    submitBtn.disabled = false;
  }
};

document.getElementById('body-next-btn').onclick = () => showPage('outfit');

document.getElementById('change-body-btn').onclick = async () => {
  const resp = await fetch('/discard_body', { method: 'POST' });
  if (!resp.ok) { window.alert(await resp.text()); return; }
  if (poll) clearInterval(poll);
  stopTurntable();
  stopTips();
  bodyPreviewArea.hidden = true;
  bodyStatusMsg.textContent = '';
  result.innerHTML = '';
  showPage('body');
};

// Image cards (upper/lower, each its own radio group): clicking anywhere in
// a <label class="combo-card"> already checks its radio natively (no JS
// needed for that) -- this just keeps the ".selected" highlight in sync,
// since that's simpler/more compatible than a CSS-only
// `:has(input:checked)` rule for a page meant to just work anywhere. Scoped
// per input `name` (upper vs. lower) so picking a lower doesn't clear the
// upper's highlight.
document.querySelectorAll('input[name="upper"], input[name="lower"]').forEach((el) => {
  el.addEventListener('change', () => {
    document.querySelectorAll(`input[name="${el.name}"]`).forEach((sibling) =>
      sibling.closest('.combo-card').classList.remove('selected'));
    el.closest('.combo-card').classList.add('selected');
  });
});

// Single overall progress bar: a coarser, more narrative view of
// status.json's own `phase` values than showing that raw phase text.
// Weighted by REAL measured wall-clock seconds (not equal slices) from a
// full default-parameter run through this exact server (the one /generate
// always launches: --preview-steps 5 --full-steps 60 --discard-frames 10
// --turntable-angles 12), read straight from that run's own
// "[status] <phase> (t=<elapsed>s)" log lines:
//   recovering_garments+untangling  0.0s  ->  0.1s   (usually cached, ~instant)
//   fitting_body+rebinding          0.1s  -> 21.6s
//   preview_simulating+rendering   21.6s  -> 73.9s
//   full_simulating                73.9s  -> 284.7s  (by far the biggest slice)
//   full_rendering+stitch         284.7s  -> 363.1s  (stitch itself is a few
//                                                      seconds of that, not
//                                                      separately logged)
// If you change what /generate passes to run_outfit_preview_pipeline.py
// (a different --full-steps etc.), these proportions will drift -- re-time
// a real run and update STEP_WEIGHTS to match.
const STEP_LABELS  = ['準備衣服素材', '量身訂做版型', '產生站姿預覽', '模擬完整動作', '渲染動畫影格', '合成影片'];
const STEP_WEIGHTS = [0.1,           21.5,          52.3,           210.8,         75.4,          3.0];
const STEP_TOTAL = STEP_WEIGHTS.reduce((a, b) => a + b, 0);
// STEP_OFFSETS[i] = cumulative seconds at which step i STARTS (e.g. [0, 0.1,
// 21.6, 73.9, 284.7, 360.1] for the weights above).
const STEP_OFFSETS = [];
for (let i = 0, sum = 0; i < STEP_WEIGHTS.length; i++) {
  STEP_OFFSETS.push(sum);
  sum += STEP_WEIGHTS[i];
}
const PHASE_STEP = {
  starting: 0, recovering_garments: 0, untangling: 0,
  fitting_body: 1, rebinding: 1,
  preview_simulating: 2, preview_rendering: 2, preview_ready: 2,
  full_simulating: 3,
  full_rendering: 4,
  done: STEP_LABELS.length,
};
// ETA: seconds-per-frame is measured from when full_rendering (with a known
// total_frames) is FIRST seen, using the server's own elapsed_seconds (not
// client Date.now()) so it's immune to clock skew -- both numbers come from
// the same status.json.
let renderBaseElapsed = null;

function updateProgress(phase, s) {
  const labelEl = document.getElementById('progress-label');
  const barEl = document.getElementById('overall-bar');
  if (!labelEl || !barEl) return;

  if (phase === 'done') {
    labelEl.textContent = '完成！';
    barEl.value = 100;
    return;
  }

  const idx = PHASE_STEP.hasOwnProperty(phase) ? PHASE_STEP[phase] : 0;
  const stepIdx = Math.min(idx, STEP_WEIGHTS.length - 1);
  const stepStart = STEP_OFFSETS[stepIdx];
  const stepWeight = STEP_WEIGHTS[stepIdx];
  let label = STEP_LABELS[stepIdx];
  let fraction;

  if (phase === 'full_rendering' && s.total_frames) {
    // Real sub-progress available here (actual frame count) -- more
    // accurate than the time-based estimate below, so prefer it.
    const rendered = s.rendered_frames || 0;
    fraction = s.total_frames > 0 ? rendered / s.total_frames : 0;
    label += '（' + rendered + '/' + s.total_frames + ' 影格';
    if (renderBaseElapsed === null) renderBaseElapsed = s.elapsed_seconds;
    const secsIntoRender = s.elapsed_seconds - renderBaseElapsed;
    if (rendered > 0 && secsIntoRender > 0) {
      const remaining = Math.max(0, Math.round((secsIntoRender / rendered) * (s.total_frames - rendered)));
      label += '，預估剩餘 ' + remaining + ' 秒';
    }
    label += '）';
  } else {
    // No direct sub-progress signal for this step -- estimate from how long
    // we've been in it vs. STEP_WEIGHTS' measured typical duration. Capped
    // below 1 so it doesn't visually finish the segment before the phase
    // actually changes if this run happens to be slower than the reference.
    const elapsedInStep = (s.elapsed_seconds || 0) - stepStart;
    fraction = stepWeight > 0 ? Math.max(0, Math.min(0.97, elapsedInStep / stepWeight)) : 0;
  }

  labelEl.textContent = label;
  const pct = ((stepStart + fraction * stepWeight) / STEP_TOTAL) * 100;
  barEl.value = Math.min(100, Math.round(pct));
}

// Turntable state -- lives across checkStatus() calls (its own slow
// setInterval, separate from the 1.5s status poll) so the spin doesn't
// restart/stutter every time a status poll comes back.
let turntableTimer = null;
let turntableUrls = [];
let turntableIdx = 0;
let turntablePauseUntil = 0;

// Rotating loading tips -- purely cosmetic, no backend cost. Own interval,
// independent of the 1.5s status poll, so it doesn't restart every poll.
const TIPS = [
  '小知識：轉盤圖其實是同一個畫面從不同角度拍的，幾乎不用額外算圖時間',
  '小知識：每一個衣服皺褶，都是物理模擬一步一步算出來的',
  '小知識：衣服的材質參數（密度、彈性）會影響它怎麼垂墜',
  '小知識：系統會依照你填的身高體重，重新調整每件衣服合身的樣子',
  '小知識：這台展示機只有一張顯卡，所以同時間只能生成一個結果',
];
let tipTimer = null;
let tipIdx = 0;

function startTips() {
  stopTips();
  tipIdx = 0;
  const el = document.getElementById('tip');
  if (el) el.textContent = TIPS[0];
  tipTimer = setInterval(() => {
    tipIdx = (tipIdx + 1) % TIPS.length;
    const el = document.getElementById('tip');
    if (el) el.textContent = TIPS[tipIdx];
  }, 4000);
}
function stopTips() {
  if (tipTimer) { clearInterval(tipTimer); tipTimer = null; }
}

const opacityScale = document.getElementById('opacity-scale');
const opacityMode = document.getElementById('opacity-mode');
opacityScale.addEventListener('input', () => {
  document.getElementById('opacity-value').textContent = Math.round(opacityScale.value * 100) + '%';
});
function updateOpacityAvailability() {
  const selected = ['upper', 'lower'].map(name => form.querySelector(`input[name="${name}"]:checked`));
  const available = selected.every(input => input && input.dataset.v3 === 'yes');
  document.getElementById('opacity-v3').disabled = !available;
  if (!available && opacityMode.value === 'v3') opacityMode.value = 'direct';
}
form.addEventListener('change', updateOpacityAvailability);
updateOpacityAvailability();

form.onsubmit = async (e) => {
  e.preventDefault();
  if (poll) clearInterval(poll);
  stopTurntable();
  stopTips();
  renderBaseElapsed = null;
  // Everything lives inside #stage so the finished video (or an error) can
  // just replace the whole thing in one go later -- covering the progress
  // bar/label instead of leaving it sitting above the result.
  result.innerHTML =
    '<div id="stage">' +
      '<div id="progress-label"></div>' +
      '<progress id="overall-bar" max="100" value="0"></progress>' +
      '<div id="status-sub"></div>' +
      '<div id="preview-area"></div>' +
    '</div>';
  updateProgress('starting', {});
  const statusSub = document.getElementById('status-sub');
  if (statusSub) statusSub.textContent = '送出中...';
  const body = new URLSearchParams(new FormData(form));
  const resp = await fetch('/generate', { method: 'POST', body });
  if (!resp.ok) { if (statusSub) statusSub.textContent = '送出失敗：' + await resp.text(); return; }
  const { run_id } = await resp.json();
  poll = setInterval(() => checkStatus(run_id), 1500);
};

function stopTurntable() {
  if (turntableTimer) { clearInterval(turntableTimer); turntableTimer = null; }
  turntableUrls = [];
  turntableIdx = 0;
}

function turntableStep(delta, run_id) {
  if (!turntableUrls.length) return;
  turntableIdx = (turntableIdx + delta + turntableUrls.length) % turntableUrls.length;
  const img = document.getElementById('turntable-img');
  if (img) img.src = turntableUrls[turntableIdx];
  turntablePauseUntil = Date.now() + 3000;  // brief pause after manual nav
}

// Builds the turntable + tip layout ONCE per run (preview_ready's first
// poll), inside #preview-area (leaves #progress-label/#overall-bar/
// #status-sub alone -- those persist across the whole run, not just this
// phase; rendering progress folds into that same top bar, see updateProgress).
function setupTurntable(run_id, n) {
  turntableUrls = Array.from({length: n}, (_, i) =>
    '/file/' + run_id + '/turntable/angle_' + String(i).padStart(3, '0') + '.png');
  turntableIdx = 0;
  const area = document.getElementById('preview-area');
  if (!area) return;
  area.innerHTML =
    '<div id="turntable-wrap">' +
      '<img id="turntable-img" src="' + turntableUrls[0] + '">' +
      '<button type="button" id="tt-prev">‹</button>' +
      '<button type="button" id="tt-next">›</button>' +
    '</div>' +
    '<div id="tip"></div>';
  document.getElementById('tt-prev').onclick = () => turntableStep(-1, run_id);
  document.getElementById('tt-next').onclick = () => turntableStep(1, run_id);
  // Auto-rotate exactly ONE full loop (n steps -> back to angle_000, the
  // front view) then stop -- a slow spin is a nice "look, you can see it
  // from every side" intro, but left running the whole multi-minute wait it
  // just looks like a gimmick on repeat. Prev/next stay live afterwards for
  // anyone who wants to keep looking around.
  let stepsTaken = 0;
  turntableTimer = setInterval(() => {
    if (Date.now() < turntablePauseUntil) return;
    turntableIdx = (turntableIdx + 1) % turntableUrls.length;
    const img = document.getElementById('turntable-img');
    if (img) img.src = turntableUrls[turntableIdx];
    stepsTaken++;
    if (stepsTaken >= turntableUrls.length) {
      clearInterval(turntableTimer);
      turntableTimer = null;
    }
  }, 500);  // ~6s for one full loop at 12 angles -- a calmer product-viewer pace
  startTips();
}

async function checkStatus(run_id) {
  const resp = await fetch('/status/' + run_id, { cache: 'no-store' });
  if (!resp.ok) {
    console.warn('status poll failed', resp.status);  // should never be 304 now (server sends no-store)
    return;
  }
  const s = await resp.json();
  updateProgress(s.phase, s);
  const statusSub = document.getElementById('status-sub');
  if (statusSub) statusSub.textContent = s.elapsed_seconds != null ? '已進行 ' + s.elapsed_seconds + ' 秒' : '';

  if (s.phase === 'error') {
    stopTurntable();
    stopTips();
    // Replaces the whole #stage (progress bar/label included), not just
    // #preview-area -- the error covers everything above it too.
    const stage = document.getElementById('stage');
    if (stage) { stage.textContent = s.message; stage.style.color = 'red'; }
    clearInterval(poll);
    return;
  }

  if (s.video_ready) {
    stopTurntable();
    stopTips();
    // Same reasoning -- the finished video covers the progress bar/label
    // instead of appearing below it.
    const stage = document.getElementById('stage');
    if (stage) stage.innerHTML =
      '<video src="/file/' + run_id + '/video.mp4?t=' + Date.now() + '" controls autoplay loop></video>';
    clearInterval(poll);
    return;
  }

  if (s.preview_ready && !turntableUrls.length && s.turntable_frames) {
    setupTurntable(run_id, s.turntable_frames);
  }
}

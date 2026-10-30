/**
 * VietVoice Studio - Text-to-Speech Application
 * Features:
 * - Hybrid Engine (Cheap-TTS + Web Speech API)
 * - Audiobook & Novel Chapter Manager for massive texts (e.g. 49,000 words)
 * - Safe Batch Processing with auto-pacing and per-chapter downloads
 */

// DOM Elements
const tabCheapTts = document.getElementById('tabCheapTts');
const tabWebSpeech = document.getElementById('tabWebSpeech');
const cheapTtsConfigCard = document.getElementById('cheapTtsConfigCard');
const btnToggleKeyEdit = document.getElementById('btnToggleKeyEdit');
const keyEditBox = document.getElementById('keyEditBox');
const cheapTtsKeyInput = document.getElementById('cheapTtsKeyInput');
const btnSaveCheapTtsKey = document.getElementById('btnSaveCheapTtsKey');

const audiobookBanner = document.getElementById('audiobookBanner');
const bannerWordCount = document.getElementById('bannerWordCount');
const bannerHours = document.getElementById('bannerHours');
const btnScrollToAudiobook = document.getElementById('btnScrollToAudiobook');

const audiobookCard = document.getElementById('audiobookCard');
const abFoundChaptersCount = document.getElementById('abFoundChaptersCount');
const wordsPerPartSelect = document.getElementById('wordsPerPartSelect');
const btnStartBatch = document.getElementById('btnStartBatch');
const btnStartBatchIcon = document.getElementById('btnStartBatchIcon');
const btnStartBatchText = document.getElementById('btnStartBatchText');
const btnStopBatch = document.getElementById('btnStopBatch');
const batchProgressContainer = document.getElementById('batchProgressContainer');
const batchProgressText = document.getElementById('batchProgressText');
const batchProgressPercent = document.getElementById('batchProgressPercent');
const batchProgressBar = document.getElementById('batchProgressBar');
const chapterList = document.getElementById('chapterList');

// Merged Audiobook MP3 Card DOM Elements
const mergedAudiobookCard = document.getElementById('mergedAudiobookCard');
const mergedBadge = document.getElementById('mergedBadge');
const mergedReadyCount = document.getElementById('mergedReadyCount');
const mergedTotalTime = document.getElementById('mergedTotalTime');
const btnMergeAndDownloadMp3 = document.getElementById('btnMergeAndDownloadMp3');
const btnMergeIcon = document.getElementById('btnMergeIcon');
const btnMergeText = document.getElementById('btnMergeText');
const mergedPlayerContainer = document.getElementById('mergedPlayerContainer');
const mergedDurationText = document.getElementById('mergedDurationText');
const mergedAudioPlayer = document.getElementById('mergedAudioPlayer');

const textInput = document.getElementById('textInput');
const voiceSelect = document.getElementById('voiceSelect');
const voiceNoteText = document.getElementById('voiceNoteText');
const rateRange = document.getElementById('rateRange');
const pitchRange = document.getElementById('pitchRange');
const volumeRange = document.getElementById('volumeRange');
const rateValue = document.getElementById('rateValue');
const pitchValue = document.getElementById('pitchValue');
const volumeValue = document.getElementById('volumeValue');
const pitchControlGroup = document.getElementById('pitchControlGroup');
const cheapTtsPauseGroup = document.getElementById('cheapTtsPauseGroup');
const pauseDurationRange = document.getElementById('pauseDurationRange');
const pauseDurationValue = document.getElementById('pauseDurationValue');

const btnSpeak = document.getElementById('btnSpeak');
const btnSpeakIcon = document.getElementById('btnSpeakIcon');
const btnSpeakText = document.getElementById('btnSpeakText');
const btnPause = document.getElementById('btnPause');
const pauseIcon = document.getElementById('pauseIcon');
const pauseText = document.getElementById('pauseText');
const btnStop = document.getElementById('btnStop');
const btnClear = document.getElementById('btnClear');
const btnPaste = document.getElementById('btnPaste');
const btnTestVoice = document.getElementById('btnTestVoice');
const btnResetSettings = document.getElementById('btnResetSettings');
const btnClearHistory = document.getElementById('btnClearHistory');

const audioOutputCard = document.getElementById('audioOutputCard');
const audioPlayer = document.getElementById('audioPlayer');
const btnDownloadAudio = document.getElementById('btnDownloadAudio');
const btnDownloadAudioMp3 = document.getElementById('btnDownloadAudioMp3');
const audioDurationBadge = document.getElementById('audioDurationBadge');
const audioVoiceInfo = document.getElementById('audioVoiceInfo');

const charCountEl = document.getElementById('charCount');
const wordCountEl = document.getElementById('wordCount');
const estTimeEl = document.getElementById('estTime');
const voiceCountBadge = document.getElementById('voiceCountBadge');
const historyList = document.getElementById('historyList');

// Visualizer Canvas
const visualizerCanvas = document.getElementById('visualizer');
const canvasCtx = visualizerCanvas.getContext('2d');
const idleWaveMsg = document.getElementById('idleWaveMsg');

// State Variables
let currentEngine = 'cheaptts';
let synth = window.speechSynthesis;
let browserVoices = [];
let cheapTtsVoices = [];
let isSpeaking = false;
let isPaused = false;
let currentUtterance = null;
let textChunks = [];
let currentChunkIndex = 0;
let animationFrameId = null;
let lastGeneratedBlobUrl = null;
let lastGeneratedAudioBlob = null;

// Audiobook / Chapters State
let parsedChapters = [];
let isBatchRunning = false;
let batchCancelRequested = false;

// Preset sample texts (Vietnamese)
const SAMPLES = {
  intro: "Xin chào các bạn! Chào mừng bạn đến với VietVoice Studio. Ứng dụng đã kết nối trực tiếp tài khoản Cheap-TTS với các giọng đọc AI tự nhiên như Ngọc Huyền, Minh Quân, Mạnh Dũng.",
  news: "Trí tuệ nhân tạo đang thay đổi cách con người làm việc và giao tiếp hàng ngày. Các công nghệ tổng hợp giọng nói ngày càng trở nên tự nhiên, mang đến trải nghiệm sống động và tiện lợi cho mọi người.",
  novel: `Chương 1: Khởi Đầu Mới
Đáy sâu của vực thẳm dường như bị bao phủ bởi một làn sương mù dày đặc màu xám tro. Tiêu Viêm đứng trên mỏm đá cao, ánh mắt sắc bén nhìn về phía trước. Hắn cảm nhận được một luồng khí tức cực kỳ cường hãn đang từ từ thức tỉnh.

Chương 2: Quyết Định Sinh Tử
'Ngươi thực sự muốn tiến vào đó sao?' - Một giọng nói trầm thấp, mang theo vẻ uy nghiêm lạnh lùng đột ngột vang lên từ hư không. Tiêu Viêm cười nhạt: 'Nếu ta đã tới đây, thì hà tất phải hỏi lại câu này. Bất kể là ai cản đường, hôm nay ta cũng nhất định phải bước qua!'

Chương 3: Lửa Xanh Bùng Cháy
Lời nói vừa dứt, ngọn lửa xanh biếc trong tay hắn bỗng nhiên bùng cháy mãnh liệt, xé toạc màn sương mù u ám xung quanh. Con đường phía trước rốt cuộc đã hiện ra rõ ràng.`
};

// ==========================================
// 1. INITIALIZATION
// ==========================================
async function init() {
  renderHistory();
  setupCanvas();
  setupEventListeners();
  updateStats();

  await loadCheapTtsVoices();

  if (synth && synth.onvoiceschanged !== undefined) {
    synth.onvoiceschanged = loadBrowserVoices;
  }
}

// ==========================================
// 2. CHAPTER DETECTION & AUDIOBOOK STUDIO
// ==========================================
/**
 * Detects chapters in large texts.
 * Searches for "Chương 1", "Hồi 1", "Phần 1", "Chapter 1", etc.
 * Falls back to 1,500-word sections if no chapter titles are found.
 */
function detectChapters(text, customWordsPerPart) {
  if (!text || text.trim().length === 0) return [];

  const defaultPartSize = wordsPerPartSelect ? parseInt(wordsPerPartSelect.value) : 1000;
  const wordsPerPart = customWordsPerPart || defaultPartSize || 1000;

  // Match chapter headings at start of line
  const regex = /(?:^|\n)(Chương\s+\d+|Hồi\s+\d+|Phần\s+\d+|Quyển\s+\d+|Chapter\s+\d+)[^\n]*/gi;
  const matches = [...text.matchAll(regex)];

  if (matches.length >= 2) {
    const chapters = [];
    for (let i = 0; i < matches.length; i++) {
      const start = matches[i].index + (matches[i][0].startsWith('\n') ? 1 : 0);
      const end = (i < matches.length - 1) ? matches[i + 1].index : text.length;
      const title = matches[i][0].trim();
      const content = text.slice(start, end).trim();
      const words = content.split(/\s+/).filter(Boolean).length;
      chapters.push({
        id: i + 1,
        title,
        content,
        words,
        status: 'pending', // 'pending' | 'processing' | 'done' | 'error'
        blobUrl: null,
        blob: null,
        arrayBuffer: null,
        duration: null,
        durationSeconds: 0
      });
    }
    return chapters;
  }

  // Fallback: Split by selected words per section (~800, 1000, 1500 words)
  const words = text.trim().split(/\s+/).filter(Boolean);
  const parts = [];

  for (let i = 0; i < words.length; i += wordsPerPart) {
    const partWords = words.slice(i, i + wordsPerPart);
    const partNum = Math.floor(i / wordsPerPart) + 1;
    const content = partWords.join(' ');
    parts.push({
      id: partNum,
      title: `Phần ${partNum} (Từ chữ ${i + 1} đến ${Math.min(i + wordsPerPart, words.length)})`,
      content,
      words: partWords.length,
      status: 'pending',
      blobUrl: null,
      blob: null,
      arrayBuffer: null,
      duration: null,
      durationSeconds: 0
    });
  }

  return parts;
}

function renderChapterList() {
  chapterList.innerHTML = '';
  abFoundChaptersCount.textContent = parsedChapters.length;

  if (parsedChapters.length === 0) {
    chapterList.innerHTML = '<p class="text-xs text-slate-500 italic py-2">Chưa phát hiện chương nào.</p>';
    updateMergedCardState();
    return;
  }

  parsedChapters.forEach(chap => {
    const chapEl = document.createElement('div');
    chapEl.id = `chapter-card-${chap.id}`;
    chapEl.className = 'flex flex-col sm:flex-row sm:items-center justify-between p-3.5 rounded-xl bg-slate-900/80 border border-slate-700/60 gap-3 transition hover:border-indigo-500/40';

    const estMinutes = Math.max(1, Math.ceil(chap.words / 150));

    let statusBadge = '';
    if (chap.status === 'pending') {
      statusBadge = '<span class="text-[10px] bg-slate-800 text-slate-400 px-2.5 py-0.5 rounded-full border border-slate-700">Chờ tạo</span>';
    } else if (chap.status === 'processing') {
      statusBadge = '<span class="text-[10px] bg-amber-500/20 text-amber-300 px-2.5 py-0.5 rounded-full border border-amber-500/30 flex items-center gap-1"><i class="fa-solid fa-spinner fa-spin text-[9px]"></i> Đang xử lý...</span>';
    } else if (chap.status === 'done') {
      statusBadge = `<span class="text-[10px] bg-emerald-500/20 text-emerald-300 px-2.5 py-0.5 rounded-full border border-emerald-500/30 flex items-center gap-1"><i class="fa-solid fa-check text-[9px]"></i> Đã xong (${chap.duration || 'WAV'})</span>`;
    } else if (chap.status === 'error') {
      statusBadge = '<span class="text-[10px] bg-rose-500/20 text-rose-300 px-2.5 py-0.5 rounded-full border border-rose-500/30">Lỗi tạo</span>';
    }

    chapEl.innerHTML = `
      <div class="flex-1">
        <div class="flex items-center gap-2">
          <h4 class="text-xs font-semibold text-slate-200 truncate max-w-md">${escapeHtml(chap.title)}</h4>
          <span class="chap-badge">${statusBadge}</span>
        </div>
        <div class="flex items-center gap-3 text-[11px] text-slate-400 mt-1">
          <span><i class="fa-solid fa-font text-[10px] text-slate-500 mr-1"></i> ${chap.words.toLocaleString()} từ</span>
          <span><i class="fa-regular fa-clock text-[10px] text-slate-500 mr-1"></i> ~${estMinutes} phút nghe</span>
        </div>
      </div>

      <div class="flex items-center gap-2 shrink-0">
        <button
          class="btn-synth-chap px-3 py-1.5 rounded-lg bg-indigo-600/80 hover:bg-indigo-600 text-white text-xs font-medium transition active:scale-95 disabled:opacity-50 cursor-pointer"
          data-id="${chap.id}"
        >
          <i class="fa-solid fa-play text-[10px]"></i> Tạo Audio
        </button>

        <button
          class="btn-play-chap ${chap.blobUrl ? '' : 'hidden'} px-3 py-1.5 rounded-lg bg-slate-700 hover:bg-slate-600 text-slate-200 text-xs font-medium transition active:scale-95 cursor-pointer"
          data-id="${chap.id}"
        >
          <i class="fa-solid fa-volume-high text-[10px]"></i> Nghe
        </button>

        <a
          class="btn-down-chap ${chap.blobUrl ? '' : 'hidden'} px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium transition active:scale-95 cursor-pointer"
          href="${chap.blobUrl || '#'}"
          download="${getCleanFileName(chap.title)}.wav"
          data-id="${chap.id}"
        >
          <i class="fa-solid fa-download text-[10px]"></i> Tải .WAV
        </a>

        <button
          class="btn-down-mp3-chap ${chap.blobUrl ? '' : 'hidden'} px-3 py-1.5 rounded-lg bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white text-xs font-medium transition active:scale-95 flex items-center gap-1 cursor-pointer"
          data-id="${chap.id}"
          title="Tải file định dạng .MP3 siêu nhẹ"
        >
          <i class="fa-solid fa-file-audio text-[10px]"></i> Tải .MP3
        </button>
      </div>
    `;

    // Event listeners
    chapEl.querySelector('.btn-synth-chap').addEventListener('click', () => {
      synthesizeSingleChapter(chap);
    });

    chapEl.querySelector('.btn-play-chap').addEventListener('click', () => {
      if (chap.blobUrl) {
        audioOutputCard.classList.remove('hidden');
        audioPlayer.src = chap.blobUrl;
        audioDurationBadge.textContent = chap.duration || '';
        audioVoiceInfo.textContent = `${chap.title}`;
        btnDownloadAudio.href = chap.blobUrl;
        btnDownloadAudio.download = `${getCleanFileName(chap.title)}.wav`;
        lastGeneratedAudioBlob = chap.blob || null;
        audioPlayer.play();
        startVisualizer();
      }
    });

    const downMp3Btn = chapEl.querySelector('.btn-down-mp3-chap');
    if (downMp3Btn) {
      downMp3Btn.addEventListener('click', () => {
        downloadSingleChapterAsMp3(chap, downMp3Btn);
      });
    }

    chapterList.appendChild(chapEl);
  });

  updateMergedCardState();
}

function updateChapterCardUI(chap) {
  const card = document.getElementById(`chapter-card-${chap.id}`);
  if (!card) return;

  const badgeSpan = card.querySelector('.chap-badge');
  const synthBtn = card.querySelector('.btn-synth-chap');
  const playBtn = card.querySelector('.btn-play-chap');
  const downBtn = card.querySelector('.btn-down-chap');
  const downMp3Btn = card.querySelector('.btn-down-mp3-chap');

  if (chap.status === 'processing') {
    badgeSpan.innerHTML = '<span class="text-[10px] bg-amber-500/20 text-amber-300 px-2.5 py-0.5 rounded-full border border-amber-500/30 flex items-center gap-1"><i class="fa-solid fa-spinner fa-spin text-[9px]"></i> Đang xử lý...</span>';
    synthBtn.disabled = true;
  } else if (chap.status === 'done') {
    badgeSpan.innerHTML = `<span class="text-[10px] bg-emerald-500/20 text-emerald-300 px-2.5 py-0.5 rounded-full border border-emerald-500/30 flex items-center gap-1"><i class="fa-solid fa-check text-[9px]"></i> Đã xong (${chap.duration})</span>`;
    synthBtn.disabled = false;
    synthBtn.innerHTML = '<i class="fa-solid fa-rotate-right text-[10px]"></i> Tạo lại';
    playBtn.classList.remove('hidden');
    downBtn.classList.remove('hidden');
    downBtn.href = chap.blobUrl;
    if (downMp3Btn) downMp3Btn.classList.remove('hidden');
  } else if (chap.status === 'error') {
    badgeSpan.innerHTML = '<span class="text-[10px] bg-rose-500/20 text-rose-300 px-2.5 py-0.5 rounded-full border border-rose-500/30">Lỗi tạo</span>';
    synthBtn.disabled = false;
  }
}

async function synthesizeSingleChapter(chap) {
  chap.status = 'processing';
  updateChapterCardUI(chap);
  showToast(`Đang tạo âm thanh cho "${chap.title}"...`, 'info');

  const selectedVoice = voiceSelect.value || 'vi-entertainment';
  const rate = parseFloat(rateRange.value) || 1.0;
  const pauseSec = parseFloat(pauseDurationRange.value) || 0.4;
  const key = cheapTtsKeyInput.value.trim();

  try {
    const res = await fetch('/api/cheap-tts/synthesize', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text: chap.content,
        voice: selectedVoice,
        rate,
        key: key || undefined,
        pauses: {
          sentence: pauseSec,
          paragraph: pauseSec * 1.5
        }
      })
    });

    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.error || `Lỗi HTTP ${res.status}`);
    }

    const blob = await res.blob();
    const arrayBuffer = await blob.arrayBuffer();
    const secondsHeader = res.headers.get('X-Audio-Seconds');
    const durationSeconds = secondsHeader ? parseFloat(secondsHeader) : (blob.size / 44100);
    const seconds = `${durationSeconds.toFixed(1)}s`;

    chap.blob = blob;
    chap.arrayBuffer = arrayBuffer;
    chap.durationSeconds = durationSeconds;
    chap.blobUrl = URL.createObjectURL(blob);
    chap.duration = seconds;
    chap.status = 'done';
    updateChapterCardUI(chap);
    updateMergedCardState();

    showToast(`Đã tạo xong "${chap.title}" (${seconds})!`, 'success');
    return true;
  } catch (err) {
    console.error(`Error synthesizing chapter ${chap.title}:`, err);
    chap.status = 'error';
    updateChapterCardUI(chap);
    showToast(`Lỗi tạo "${chap.title}": ${err.message}`, 'error');
    return false;
  }
}

/**
 * Updates the UI state of the Merged Full Audiobook MP3 Card
 */
function updateMergedCardState() {
  if (!mergedAudiobookCard) return;

  const total = parsedChapters.length;
  const readyChapters = parsedChapters.filter(c => c.status === 'done' && (c.arrayBuffer || c.blob || c.blobUrl));
  const readyCount = readyChapters.length;

  if (mergedReadyCount) {
    mergedReadyCount.textContent = total > 0 ? `${readyCount} / ${total}` : '0';
  }

  // Calculate total duration in seconds
  let totalSec = 0;
  readyChapters.forEach(c => {
    if (c.durationSeconds && !isNaN(c.durationSeconds)) {
      totalSec += c.durationSeconds;
    } else if (c.arrayBuffer) {
      totalSec += Math.max(0, (c.arrayBuffer.byteLength - 44) / 44100);
    } else if (c.blob) {
      totalSec += Math.max(0, (c.blob.size - 44) / 44100);
    }
  });

  if (mergedTotalTime) {
    if (totalSec <= 0) {
      mergedTotalTime.textContent = '0s';
    } else if (totalSec < 60) {
      mergedTotalTime.textContent = `${Math.round(totalSec)}s`;
    } else {
      const mins = Math.floor(totalSec / 60);
      const secs = Math.round(totalSec % 60);
      mergedTotalTime.textContent = `${mins}p ${secs}s`;
    }
  }

  if (btnMergeAndDownloadMp3) {
    if (readyCount === 0) {
      btnMergeAndDownloadMp3.disabled = true;
      if (mergedBadge) {
        mergedBadge.textContent = 'Chờ hoàn tất các phần';
        mergedBadge.className = 'text-[10px] bg-slate-800 text-slate-400 px-2.5 py-0.5 rounded-full font-semibold border border-slate-700';
      }
    } else if (readyCount < total) {
      btnMergeAndDownloadMp3.disabled = false;
      if (mergedBadge) {
        mergedBadge.textContent = `Đã xong ${readyCount}/${total} phần (Có thể gộp ngay)`;
        mergedBadge.className = 'text-[10px] bg-amber-500/20 text-amber-300 px-2.5 py-0.5 rounded-full font-semibold border border-amber-500/30';
      }
    } else {
      btnMergeAndDownloadMp3.disabled = false;
      if (mergedBadge) {
        mergedBadge.textContent = `Sẵn sàng gộp trọn bộ ${total} phần!`;
        mergedBadge.className = 'text-[10px] bg-emerald-500/20 text-emerald-300 px-2.5 py-0.5 rounded-full font-semibold border border-emerald-500/30';
      }
    }
  }
}

/**
 * Merges multiple WAV ArrayBuffers into a single unified WAV Blob in the browser
 */
function mergeWavBuffersClient(arrayBuffers, silenceSec = 0.35, sampleRate = 22050) {
  if (!arrayBuffers || arrayBuffers.length === 0) return null;
  if (arrayBuffers.length === 1) return new Blob([arrayBuffers[0]], { type: 'audio/wav' });

  const silenceSamples = Math.round(silenceSec * sampleRate);
  // 16-bit mono PCM = 2 bytes per sample
  const silenceBytes = new Uint8Array(silenceSamples * 2);

  const parts = [];
  let totalDataLength = 0;

  for (let i = 0; i < arrayBuffers.length; i++) {
    const buf = arrayBuffers[i];
    if (buf.byteLength <= 44) continue;
    // Skip 44-byte WAV header
    const pcm = new Uint8Array(buf, 44);
    parts.push(pcm);
    totalDataLength += pcm.byteLength;

    if (i < arrayBuffers.length - 1 && silenceSec > 0) {
      parts.push(silenceBytes);
      totalDataLength += silenceBytes.byteLength;
    }
  }

  // Clone 44-byte header from the first buffer
  const firstHeaderBuf = arrayBuffers[0].slice(0, 44);
  const headerView = new DataView(firstHeaderBuf);

  // RIFF chunk size at offset 4 (totalDataLength + 36)
  headerView.setUint32(4, totalDataLength + 36, true);
  // data subchunk size at offset 40 (totalDataLength)
  headerView.setUint32(40, totalDataLength, true);

  return new Blob([firstHeaderBuf, ...parts], { type: 'audio/wav' });
}

/**
 * Merges all completed chapters and converts the combined audio to MP3 via server FFmpeg
 */
async function mergeAndDownloadFullAudiobook() {
  const readyChapters = parsedChapters.filter(c => c.status === 'done' && (c.arrayBuffer || c.blob || c.blobUrl));
  if (readyChapters.length === 0) {
    showToast('Chưa có phần nào được tạo xong! Vui lòng bấm "Tự động tạo tất cả các chương" trước.', 'warning');
    return;
  }

  if (btnMergeAndDownloadMp3) btnMergeAndDownloadMp3.disabled = true;
  if (btnMergeIcon) btnMergeIcon.className = 'fa-solid fa-spinner fa-spin text-sm';
  if (btnMergeText) btnMergeText.textContent = `Đang ghép ${readyChapters.length} phần âm thanh...`;

  try {
    // 1. Ensure all ready chapters have arrayBuffers loaded
    for (const chap of readyChapters) {
      if (!chap.arrayBuffer) {
        if (chap.blob) {
          chap.arrayBuffer = await chap.blob.arrayBuffer();
        } else if (chap.blobUrl) {
          const r = await fetch(chap.blobUrl);
          chap.blob = await r.blob();
          chap.arrayBuffer = await chap.blob.arrayBuffer();
        }
      }
    }

    // 2. Concatenate all WAV PCM buffers into a single WAV Blob
    const mergedWavBlob = mergeWavBuffersClient(
      readyChapters.map(c => c.arrayBuffer),
      0.35,
      22050
    );

    if (!mergedWavBlob) {
      throw new Error('Không thể gộp âm thanh (dữ liệu WAV rỗng)');
    }

    const wavSizeMB = (mergedWavBlob.size / (1024 * 1024)).toFixed(2);
    if (btnMergeText) btnMergeText.textContent = `Đang nén sang .MP3 siêu nhẹ (${wavSizeMB} MB)...`;
    showToast(`Đã gộp ${readyChapters.length} phần! Đang nén sang định dạng .MP3...`, 'info');

    // 3. Send merged WAV to backend FFmpeg converter
    const res = await fetch('/api/audio/convert-to-mp3', {
      method: 'POST',
      headers: { 'Content-Type': 'audio/wav' },
      body: mergedWavBlob
    });

    if (!res.ok) {
      const errJson = await res.json().catch(() => ({}));
      throw new Error(errJson.error || `Lỗi máy chủ HTTP ${res.status}`);
    }

    const mp3Blob = await res.blob();
    const mp3SizeMB = (mp3Blob.size / (1024 * 1024)).toFixed(2);
    const reductionPercent = Math.max(10, Math.round((1 - (mp3Blob.size / mergedWavBlob.size)) * 100));

    const mp3Url = URL.createObjectURL(mp3Blob);

    // 4. Trigger auto-download
    const filename = `vietvoice-tron-bo-${readyChapters.length}-phan.mp3`;
    const a = document.createElement('a');
    a.href = mp3Url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);

    // 5. Update audio player preview in the card
    if (mergedPlayerContainer && mergedAudioPlayer) {
      mergedPlayerContainer.classList.remove('hidden');
      mergedAudioPlayer.src = mp3Url;
      mergedAudioPlayer.onloadedmetadata = () => {
        if (mergedDurationText && mergedAudioPlayer.duration) {
          const totalSec = Math.round(mergedAudioPlayer.duration);
          const mins = Math.floor(totalSec / 60);
          const secs = totalSec % 60;
          mergedDurationText.textContent = `${mins}:${secs < 10 ? '0' : ''}${secs}`;
        }
      };
      mergedAudioPlayer.play().catch(() => {});
    }

    showToast(`Đã tải xuống "${filename}"! Dung lượng nhẹ hơn ${reductionPercent}% (${mp3SizeMB}MB so với ${wavSizeMB}MB WAV)`, 'success');

  } catch (err) {
    console.error('Error merging chapters:', err);
    showToast(`Lỗi gộp & xuất file MP3: ${err.message}`, 'error');
  } finally {
    if (btnMergeAndDownloadMp3) btnMergeAndDownloadMp3.disabled = false;
    if (btnMergeIcon) btnMergeIcon.className = 'fa-solid fa-cloud-arrow-down text-sm';
    if (btnMergeText) btnMergeText.textContent = 'Gộp & Tải Toàn Bộ .MP3';
  }
}

/**
 * Converts and downloads a single chapter as MP3
 */
async function downloadSingleChapterAsMp3(chap, btnEl) {
  let blob = chap.blob;
  if (!blob && chap.blobUrl) {
    try {
      const r = await fetch(chap.blobUrl);
      blob = await r.blob();
      chap.blob = blob;
    } catch (e) {
      console.warn('Could not fetch blob from blobUrl:', e);
    }
  }

  if (!blob) {
    showToast('Chưa có dữ liệu âm thanh để chuyển đổi', 'error');
    return;
  }

  const originalHtml = btnEl ? btnEl.innerHTML : '';
  if (btnEl) {
    btnEl.disabled = true;
    btnEl.innerHTML = '<i class="fa-solid fa-spinner fa-spin text-[10px]"></i> Nén MP3...';
  }

  try {
    showToast(`Đang nén "${chap.title}" sang file .MP3...`, 'info');
    const res = await fetch('/api/audio/convert-to-mp3', {
      method: 'POST',
      headers: { 'Content-Type': 'audio/wav' },
      body: blob
    });

    if (!res.ok) {
      const errJson = await res.json().catch(() => ({}));
      throw new Error(errJson.error || `Lỗi HTTP ${res.status}`);
    }

    const mp3Blob = await res.blob();
    const filename = `${getCleanFileName(chap.title)}.mp3`;
    const url = URL.createObjectURL(mp3Blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);

    const sizeKB = (mp3Blob.size / 1024).toFixed(0);
    showToast(`Đã tải xuống file MP3 "${filename}" (${sizeKB} KB)!`, 'success');
  } catch (err) {
    console.error('Error converting single chapter to MP3:', err);
    showToast(`Lỗi nén MP3: ${err.message}`, 'error');
  } finally {
    if (btnEl) {
      btnEl.disabled = false;
      btnEl.innerHTML = originalHtml;
    }
  }
}

// Batch queue processor: runs chapter by chapter with safe delays
async function startBatchChapters() {
  if (parsedChapters.length === 0) return;

  isBatchRunning = true;
  batchCancelRequested = false;

  btnStartBatch.disabled = true;
  btnStartBatchIcon.className = 'fa-solid fa-spinner fa-spin';
  btnStartBatchText.textContent = 'Đang tự động tạo...';
  btnStopBatch.disabled = false;

  let completedCount = parsedChapters.filter(c => c.status === 'done').length;
  updateBatchProgress(completedCount, parsedChapters.length);

  for (let i = 0; i < parsedChapters.length; i++) {
    if (batchCancelRequested) {
      showToast('Đã tạm dừng hàng đợi tạo Audiobook', 'info');
      break;
    }

    const chap = parsedChapters[i];
    if (chap.status === 'done') continue; // Skip already completed

    batchProgressText.textContent = `Đang xử lý: ${chap.title} (${i + 1}/${parsedChapters.length})...`;

    const success = await synthesizeSingleChapter(chap);
    if (success) {
      completedCount++;
      updateBatchProgress(completedCount, parsedChapters.length);
    }

    // Pacing delay between chapters (1.2 seconds) to guarantee no rate limits
    if (i < parsedChapters.length - 1 && !batchCancelRequested) {
      await new Promise(r => setTimeout(r, 1200));
    }
  }

  isBatchRunning = false;
  btnStartBatch.disabled = false;
  btnStartBatchIcon.className = 'fa-solid fa-play';
  btnStartBatchText.textContent = 'Tự động tạo tất cả các chương';
  btnStopBatch.disabled = true;

  if (completedCount === parsedChapters.length) {
    showToast('Hoàn tất tạo toàn bộ các chương của sách/truyện!', 'success');
    batchProgressText.textContent = `Đã hoàn tất toàn bộ ${parsedChapters.length} chương!`;
  }
}

function updateBatchProgress(completed, total) {
  const percent = total > 0 ? Math.round((completed / total) * 100) : 0;
  batchProgressPercent.textContent = `${percent}%`;
  batchProgressBar.style.width = `${percent}%`;
  batchProgressText.textContent = `Tiến độ: Đã xong ${completed} / ${total} chương (${percent}%)`;
}

function getCleanFileName(title) {
  return title
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-zA-Z0-9_\-\s]/g, '')
    .trim()
    .replace(/\s+/g, '_')
    .slice(0, 40) || 'chapter_audio';
}

// ==========================================
// 3. CHEAP-TTS VOICES & SYNTHESIS (STANDARD)
// ==========================================
async function loadCheapTtsVoices() {
  voiceSelect.innerHTML = '<option value="">Đang tải danh sách giọng AI từ Cheap-TTS...</option>';

  try {
    const res = await fetch('/api/cheap-tts/voices');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    if (data.success && data.voices) {
      cheapTtsVoices = data.voices;
      populateCheapTtsVoiceList(cheapTtsVoices);
      return;
    }
    throw new Error(data.error || 'Không tải được danh sách giọng');
  } catch (err) {
    cheapTtsVoices = [
      { id: 'vi-entertainment', name: 'Ngọc Huyền', language: 'vi', useCase: 'Giải trí / Kể chuyện' },
      { id: 'vi-commentary', name: 'Minh Quân', language: 'vi', useCase: 'Bình luận phim' },
      { id: 'vi-advertising', name: 'Mạnh Dũng', language: 'vi', useCase: 'Quảng cáo / TVC' },
      { id: 'vi-tiktok-clip', name: 'Adam', language: 'vi', useCase: 'TikTok clip' }
    ];
    populateCheapTtsVoiceList(cheapTtsVoices);
  }
}

function populateCheapTtsVoiceList(voicesList) {
  voiceSelect.innerHTML = '';
  voiceCountBadge.textContent = `${voicesList.length} giọng AI`;

  const groupVi = document.createElement('optgroup');
  groupVi.label = '⭐ Giọng AI Tiếng Việt Nổi Bật (Cheap-TTS)';

  const groupOther = document.createElement('optgroup');
  groupOther.label = '🌐 Giọng AI Quốc Tế (Anh, Pháp, Đức, Nhật, ...)';

  voicesList.forEach(v => {
    const opt = document.createElement('option');
    opt.value = v.id;
    opt.textContent = `${v.name} (${v.useCase || v.id}) - ${v.language.toUpperCase()}`;
    opt.dataset.name = v.name;
    opt.dataset.lang = v.language;

    if (v.language === 'vi' || v.id.startsWith('vi')) {
      groupVi.appendChild(opt);
    } else {
      groupOther.appendChild(opt);
    }
  });

  if (groupVi.children.length > 0) voiceSelect.appendChild(groupVi);
  if (groupOther.children.length > 0) voiceSelect.appendChild(groupOther);

  voiceSelect.value = 'vi-entertainment';
}

async function startCheapTtsSynthesis(text) {
  // If user submits a massive text via the main button, prompt them to use Chapter mode
  const words = text.trim().split(/\s+/).filter(Boolean).length;
  if (words > 2500) {
    showToast(`Văn bản này rất dài (${words.toLocaleString()} từ). Vui lòng dùng Bộ chia chương bên dưới để tạo từng chương an toàn!`, 'warning');
    audiobookCard.scrollIntoView({ behavior: 'smooth' });
    return;
  }

  const selectedVoice = voiceSelect.value || 'vi-entertainment';
  const rate = parseFloat(rateRange.value) || 1.0;
  const pauseSec = parseFloat(pauseDurationRange.value) || 0.4;
  const key = cheapTtsKeyInput.value.trim();

  const isLong = text.length > 700;
  const estChunks = Math.ceil(text.length / 650);

  btnSpeak.disabled = true;
  btnSpeakIcon.className = 'fa-solid fa-spinner fa-spin text-sm';
  btnSpeakText.textContent = isLong ? `Đang xử lý ${estChunks} đoạn...` : 'Đang tạo âm thanh AI...';
  btnStop.disabled = false;

  showToast(isLong ? `Văn bản dài (~${estChunks} đoạn). Đang tự động ghép nối âm thanh...` : 'Đang tạo âm thanh AI...', 'info');

  try {
    const response = await fetch('/api/cheap-tts/synthesize', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text,
        voice: selectedVoice,
        rate,
        key: key || undefined,
        pauses: {
          sentence: pauseSec,
          paragraph: pauseSec * 1.5
        }
      })
    });

    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      throw new Error(errData.error || `Lỗi server HTTP ${response.status}`);
    }

    const audioBlob = await response.blob();
    const secondsHeader = response.headers.get('X-Audio-Seconds');
    const chunksHeader = response.headers.get('X-Total-Chunks') || '1';
    const voiceNameHeader = decodeURIComponent(response.headers.get('X-Voice-Name') || selectedVoice);

    if (lastGeneratedBlobUrl) {
      URL.revokeObjectURL(lastGeneratedBlobUrl);
    }

    const blobUrl = URL.createObjectURL(audioBlob);
    lastGeneratedBlobUrl = blobUrl;
    lastGeneratedAudioBlob = audioBlob;

    audioOutputCard.classList.remove('hidden');
    audioPlayer.src = blobUrl;
    btnDownloadAudio.href = blobUrl;
    btnDownloadAudio.download = `cheap-tts-${selectedVoice}-${Date.now()}.wav`;

    const seconds = secondsHeader ? parseFloat(secondsHeader).toFixed(1) : ((audioBlob.size / 32000).toFixed(1));
    const chunkNote = parseInt(chunksHeader) > 1 ? ` • Đã ghép ${chunksHeader} đoạn liền mạch` : '';
    audioDurationBadge.textContent = `${seconds}s`;
    audioVoiceInfo.textContent = `Giọng đọc: ${voiceNameHeader} • Dung lượng: ${(audioBlob.size / 1024).toFixed(1)} KB${chunkNote}`;

    audioPlayer.volume = parseFloat(volumeRange.value) || 1.0;
    await audioPlayer.play();

    startVisualizer();
    showToast(`Tạo thành công ${seconds}s âm thanh! File đã sẵn sàng để tải về.`, 'success');
  } catch (err) {
    console.error('Cheap-TTS synthesis error:', err);
    showToast(`Lỗi tạo giọng nói: ${err.message}`, 'error');
  } finally {
    btnSpeak.disabled = false;
    btnSpeakIcon.className = 'fa-solid fa-play text-sm';
    btnSpeakText.textContent = 'Tạo giọng nói AI';
  }
}

// ==========================================
// 4. WEB SPEECH ENGINE
// ==========================================
function loadBrowserVoices() {
  if (!synth) return;
  browserVoices = synth.getVoices();
  if (currentEngine === 'webspeech') populateBrowserVoiceList();
}

function populateBrowserVoiceList() {
  voiceSelect.innerHTML = '';
  voiceCountBadge.textContent = `${browserVoices.length} giọng`;

  const viVoices = browserVoices.filter(v => v.lang.toLowerCase().startsWith('vi') || v.name.toLowerCase().includes('vietnam'));
  const otherVoices = browserVoices.filter(v => !viVoices.includes(v));

  if (viVoices.length > 0) {
    const groupVi = document.createElement('optgroup');
    groupVi.label = '⭐ Giọng đọc Tiếng Việt (Máy của bạn)';
    viVoices.forEach(voice => {
      const option = document.createElement('option');
      option.value = voice.name;
      option.textContent = `${voice.name} (${voice.lang})`;
      groupVi.appendChild(option);
    });
    voiceSelect.appendChild(groupVi);
  }

  if (otherVoices.length > 0) {
    const groupOther = document.createElement('optgroup');
    groupOther.label = '🌐 Ngôn ngữ khác';
    otherVoices.forEach(voice => {
      const option = document.createElement('option');
      option.value = voice.name;
      option.textContent = `${voice.name} (${voice.lang})`;
      groupOther.appendChild(option);
    });
    voiceSelect.appendChild(groupOther);
  }

  if (viVoices.length > 0) voiceSelect.value = viVoices[0].name;
}

function splitTextIntoChunks(text) {
  if (!text) return [];
  const regex = /[^.?!;\n]+[.?!;\n]+|[^.?!;\n]+$/g;
  const rawChunks = text.match(regex) || [text];
  const cleanChunks = [];
  rawChunks.forEach(chunk => {
    const trimmed = chunk.trim();
    if (trimmed.length > 0) {
      if (trimmed.length > 200) {
        const sub = trimmed.match(/.{1,180}(\s|$)/g) || [trimmed];
        sub.forEach(s => { if (s.trim().length > 0) cleanChunks.push(s.trim()); });
      } else {
        cleanChunks.push(trimmed);
      }
    }
  });
  return cleanChunks;
}

// Keep-alive timer for Web Speech API in Chrome/Safari (prevents abrupt stopping after 15s)
let webSpeechKeepAlive = null;

function startWebSpeech(text) {
  stopSpeaking();
  textChunks = splitTextIntoChunks(text);
  if (textChunks.length === 0) return;

  currentChunkIndex = 0;
  isSpeaking = true;
  isPaused = false;
  updateUIForPlaying(true);
  startVisualizer();

  if (webSpeechKeepAlive) clearInterval(webSpeechKeepAlive);
  webSpeechKeepAlive = setInterval(() => {
    if (isSpeaking && !isPaused && synth && synth.speaking) {
      synth.pause();
      synth.resume();
    }
  }, 10000);

  speakChunk(currentChunkIndex);
}

function speakChunk(index) {
  if (index >= textChunks.length || !isSpeaking) {
    stopSpeaking();
    showToast('Đã đọc xong văn bản!', 'success');
    return;
  }

  const chunkText = textChunks[index];
  const utterance = new SpeechSynthesisUtterance(chunkText);
  const chosenVoice = browserVoices.find(v => v.name === voiceSelect.value);
  if (chosenVoice) {
    utterance.voice = chosenVoice;
    utterance.lang = chosenVoice.lang;
  }
  utterance.rate = parseFloat(rateRange.value);
  utterance.pitch = parseFloat(pitchRange.value);
  utterance.volume = parseFloat(volumeRange.value);

  utterance.onend = () => {
    if (!isSpeaking) return;
    currentChunkIndex++;
    if (currentChunkIndex < textChunks.length) {
      speakChunk(currentChunkIndex);
    } else {
      stopSpeaking();
      showToast('Đã đọc xong văn bản!', 'success');
    }
  };

  utterance.onerror = (e) => {
    if (e.error === 'canceled' || e.error === 'interrupted') return;
    showToast(`Lỗi phát giọng nói: ${e.error}`, 'error');
    stopSpeaking();
  };

  currentUtterance = utterance;
  synth.speak(utterance);
}

function togglePause() {
  if (!isSpeaking) return;
  if (synth.speaking && !isPaused) {
    synth.pause();
    isPaused = true;
    pauseIcon.className = 'fa-solid fa-play';
    pauseText.textContent = 'Tiếp tục';
  } else if (isPaused) {
    synth.resume();
    isPaused = false;
    pauseIcon.className = 'fa-solid fa-pause';
    pauseText.textContent = 'Tạm dừng';
  }
}

function stopSpeaking() {
  if (synth) synth.cancel();
  if (audioPlayer && !audioPlayer.paused) audioPlayer.pause();
  if (webSpeechKeepAlive) {
    clearInterval(webSpeechKeepAlive);
    webSpeechKeepAlive = null;
  }
  isSpeaking = false;
  isPaused = false;
  currentUtterance = null;
  textChunks = [];
  currentChunkIndex = 0;
  updateUIForPlaying(false);
  stopVisualizer();
}

// ==========================================
// 5. ENGINE SWITCHER
// ==========================================
function switchEngine(engine) {
  if (currentEngine === engine) return;
  stopSpeaking();
  currentEngine = engine;

  if (engine === 'cheaptts') {
    tabCheapTts.classList.add('active', 'cheap-tts-active');
    tabWebSpeech.classList.remove('active');
    cheapTtsConfigCard.classList.remove('hidden');
    pitchControlGroup.classList.add('hidden');
    cheapTtsPauseGroup.classList.remove('hidden');
    btnPause.classList.add('hidden');
    btnSpeakText.textContent = 'Tạo giọng nói AI';
    voiceNoteText.textContent = 'Giọng AI Cheap-TTS tự nhiên chuyên dùng cho Kể chuyện, Review phim, Tiểu thuyết.';
    populateCheapTtsVoiceList(cheapTtsVoices);
    showToast('Đã chuyển sang Cheap-TTS Cloud AI', 'info');
  } else {
    tabWebSpeech.classList.add('active');
    tabCheapTts.classList.remove('active', 'cheap-tts-active');
    cheapTtsConfigCard.classList.add('hidden');
    pitchControlGroup.classList.remove('hidden');
    cheapTtsPauseGroup.classList.add('hidden');
    btnPause.classList.remove('hidden');
    btnSpeakText.textContent = 'Đọc văn bản';
    voiceNoteText.textContent = 'Giọng đọc trình duyệt miễn phí trên máy tính của bạn.';
    populateBrowserVoiceList();
    showToast('Đã chuyển sang Trình duyệt (Web Speech)', 'info');
  }
}

// ==========================================
// 6. UI CONTROLS & STATS
// ==========================================
async function handleSpeakAction() {
  const text = textInput.value.trim();
  if (!text) {
    showToast('Vui lòng nhập văn bản cần đọc!', 'warning');
    textInput.focus();
    return;
  }

  saveToHistory(text);

  if (currentEngine === 'cheaptts') {
    await startCheapTtsSynthesis(text);
  } else {
    startWebSpeech(text);
  }
}

function updateUIForPlaying(playing) {
  if (playing) {
    btnSpeak.classList.add('bg-rose-600', 'speaking-active');
    btnSpeakText.textContent = 'Đang đọc...';
    btnPause.disabled = false;
    btnStop.disabled = false;
  } else {
    btnSpeak.classList.remove('bg-rose-600', 'speaking-active');
    btnSpeakText.textContent = currentEngine === 'cheaptts' ? 'Tạo giọng nói AI' : 'Đọc văn bản';
    btnPause.disabled = true;
    btnStop.disabled = true;
  }
}

function updateStats() {
  const text = textInput.value || '';
  const charLen = text.length;
  const words = text.trim() ? text.trim().split(/\s+/).filter(Boolean).length : 0;

  charCountEl.textContent = charLen.toLocaleString();
  wordCountEl.textContent = words.toLocaleString();

  const currentRate = parseFloat(rateRange.value) || 1.0;
  const totalMinutes = words > 0 ? (words / (150 * currentRate)) : 0;
  const seconds = Math.ceil(totalMinutes * 60);

  if (seconds < 60) {
    estTimeEl.textContent = `${seconds}s`;
  } else if (totalMinutes < 60) {
    const mins = Math.floor(totalMinutes);
    const remSec = seconds % 60;
    estTimeEl.textContent = `${mins}m ${remSec}s`;
  } else {
    const hours = (totalMinutes / 60).toFixed(1);
    estTimeEl.textContent = `~${hours} giờ`;
  }

  // Check if massive text or novel chapter headings detected (>= 600 words or Chapter tags)
  const hasChapterHeadings = /(?:^|\n)(Chương\s+\d+|Hồi\s+\d+|Phần\s+\d+|Quyển\s+\d+|Chapter\s+\d+)/i.test(text);
  if (words >= 600 || hasChapterHeadings) {
    audiobookBanner.classList.remove('hidden');
    audiobookCard.classList.remove('hidden');
    bannerWordCount.textContent = words.toLocaleString();
    const hours = (totalMinutes / 60).toFixed(1);
    bannerHours.textContent = `~${hours} giờ đọc`;

    // Only re-parse if not currently running batch and no chapters are done/processing
    const hasActiveOrCompleted = parsedChapters.some(c => c.status === 'done' || c.status === 'processing');
    if (!hasActiveOrCompleted) {
      const partSize = wordsPerPartSelect ? parseInt(wordsPerPartSelect.value) : 1000;
      parsedChapters = detectChapters(text, partSize);
      renderChapterList();
    }
  } else {
    audiobookBanner.classList.add('hidden');
    if (parsedChapters.length === 0) {
      audiobookCard.classList.add('hidden');
    }
  }
}

function resetSettings() {
  rateRange.value = 1.0;
  pitchRange.value = 1.0;
  volumeRange.value = 1.0;
  pauseDurationRange.value = 0.4;
  rateValue.textContent = '1.0x';
  pitchValue.textContent = '1.0';
  volumeValue.textContent = '100%';
  pauseDurationValue.textContent = '0.4s';
  updateStats();
  showToast('Đã khôi phục cài đặt mặc định!', 'info');
}

// ==========================================
// 7. VISUALIZER
// ==========================================
function setupCanvas() {
  const dpr = window.devicePixelRatio || 1;
  const rect = visualizerCanvas.getBoundingClientRect();
  visualizerCanvas.width = rect.width * dpr;
  visualizerCanvas.height = rect.height * dpr;
  canvasCtx.scale(dpr, dpr);
}

let wavePhase = 0;
function drawWave() {
  const isAudioPlaying = audioPlayer && !audioPlayer.paused;
  if (!isSpeaking && !isAudioPlaying) return;

  const rect = visualizerCanvas.getBoundingClientRect();
  const width = rect.width;
  const height = rect.height;

  canvasCtx.clearRect(0, 0, width, height);

  const numBars = 36;
  const barWidth = 4;
  const gap = (width - numBars * barWidth) / (numBars + 1);

  wavePhase += 0.08;

  for (let i = 0; i < numBars; i++) {
    const sin1 = Math.sin(wavePhase + i * 0.25);
    const sin2 = Math.cos(wavePhase * 0.7 + i * 0.15);
    const intensity = Math.abs(sin1 * 0.6 + sin2 * 0.4);
    const barHeight = Math.max(6, intensity * (height * 0.75));

    const x = gap + i * (barWidth + gap);
    const y = (height - barHeight) / 2;

    const grad = canvasCtx.createLinearGradient(0, y, 0, y + barHeight);
    grad.addColorStop(0, '#f59e0b');
    grad.addColorStop(1, '#ea580c');

    canvasCtx.fillStyle = grad;
    canvasCtx.beginPath();
    canvasCtx.roundRect(x, y, barWidth, barHeight, 3);
    canvasCtx.fill();
  }

  animationFrameId = requestAnimationFrame(drawWave);
}

function startVisualizer() {
  idleWaveMsg.classList.add('hidden');
  cancelAnimationFrame(animationFrameId);
  drawWave();
}

function stopVisualizer() {
  cancelAnimationFrame(animationFrameId);
  const rect = visualizerCanvas.getBoundingClientRect();
  canvasCtx.clearRect(0, 0, rect.width, rect.height);
  idleWaveMsg.classList.remove('hidden');
}

// ==========================================
// 8. HISTORY MANAGEMENT
// ==========================================
function saveToHistory(text) {
  if (!text || text.length < 3) return;
  let history = JSON.parse(localStorage.getItem('vietvoice_history') || '[]');
  history = history.filter(item => item.text !== text);
  history.unshift({
    text: text.slice(0, 150) + (text.length > 150 ? '...' : ''),
    fullText: text,
    time: new Date().toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' }),
    engine: currentEngine === 'cheaptts' ? 'Cheap-TTS AI' : 'Web Speech'
  });
  if (history.length > 10) history = history.slice(0, 10);
  localStorage.setItem('vietvoice_history', JSON.stringify(history));
  renderHistory();
}

function renderHistory() {
  const history = JSON.parse(localStorage.getItem('vietvoice_history') || '[]');
  historyList.innerHTML = '';
  if (history.length === 0) {
    historyList.innerHTML = '<p class="text-xs text-slate-500 italic py-2">Chưa có đoạn văn bản nào trong lịch sử.</p>';
    return;
  }
  history.forEach((item, index) => {
    const el = document.createElement('div');
    el.className = 'history-item flex items-center justify-between p-2 rounded-lg bg-slate-900/60 border border-slate-700/50 cursor-pointer group';
    el.innerHTML = `
      <div class="flex-1 truncate mr-2">
        <p class="text-xs text-slate-200 truncate group-hover:text-amber-300 font-medium">${escapeHtml(item.text)}</p>
        <span class="text-[10px] text-slate-500">${item.time} • ${item.engine}</span>
      </div>
      <button class="delete-history opacity-0 group-hover:opacity-100 p-1 hover:text-rose-400 text-slate-500 transition text-xs" title="Xóa">
        <i class="fa-solid fa-xmark"></i>
      </button>
    `;
    el.addEventListener('click', (e) => {
      if (e.target.closest('.delete-history')) return;
      textInput.value = item.fullText || item.text;
      updateStats();
      showToast('Đã tải văn bản từ lịch sử', 'info');
    });
    el.querySelector('.delete-history').addEventListener('click', (e) => {
      e.stopPropagation();
      deleteHistoryItem(index);
    });
    historyList.appendChild(el);
  });
}

function deleteHistoryItem(index) {
  let history = JSON.parse(localStorage.getItem('vietvoice_history') || '[]');
  history.splice(index, 1);
  localStorage.setItem('vietvoice_history', JSON.stringify(history));
  renderHistory();
}

function clearAllHistory() {
  localStorage.removeItem('vietvoice_history');
  renderHistory();
  showToast('Đã xóa toàn bộ lịch sử', 'info');
}

// ==========================================
// 9. TOAST NOTIFICATIONS
// ==========================================
let toastTimer = null;
function showToast(message, type = 'info') {
  const toast = document.getElementById('toast');
  const toastMsg = document.getElementById('toastMsg');
  const toastIcon = document.getElementById('toastIcon');

  clearTimeout(toastTimer);
  toastMsg.textContent = message;

  if (type === 'success') {
    toastIcon.className = 'fa-solid fa-circle-check text-emerald-400 text-lg';
  } else if (type === 'warning') {
    toastIcon.className = 'fa-solid fa-triangle-exclamation text-amber-400 text-lg';
  } else if (type === 'error') {
    toastIcon.className = 'fa-solid fa-circle-xmark text-rose-400 text-lg';
  } else {
    toastIcon.className = 'fa-solid fa-circle-info text-amber-400 text-lg';
  }

  toast.classList.remove('translate-y-20', 'opacity-0');
  toast.classList.add('translate-y-0', 'opacity-100');

  toastTimer = setTimeout(() => {
    toast.classList.remove('translate-y-0', 'opacity-100');
    toast.classList.add('translate-y-20', 'opacity-0');
  }, 3200);
}

function escapeHtml(string) {
  return String(string)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

// ==========================================
// 10. EVENT LISTENERS
// ==========================================
function setupEventListeners() {
  tabCheapTts.addEventListener('click', () => switchEngine('cheaptts'));
  tabWebSpeech.addEventListener('click', () => switchEngine('webspeech'));

  btnToggleKeyEdit.addEventListener('click', () => {
    keyEditBox.classList.toggle('hidden');
  });

  btnSaveCheapTtsKey.addEventListener('click', () => {
    const key = cheapTtsKeyInput.value.trim();
    if (key) {
      showToast('Đã lưu mã khóa Cheap-TTS mới!', 'success');
      keyEditBox.classList.add('hidden');
      loadCheapTtsVoices();
    }
  });

  // Audiobook batch events
  btnScrollToAudiobook.addEventListener('click', () => {
    audiobookCard.scrollIntoView({ behavior: 'smooth' });
  });

  btnStartBatch.addEventListener('click', () => {
    startBatchChapters();
  });

  btnStopBatch.addEventListener('click', () => {
    batchCancelRequested = true;
    btnStopBatch.disabled = true;
    showToast('Đang dừng hàng đợi sau chương hiện tại...', 'info');
  });

  // Merge full audiobook and download MP3 button
  if (btnMergeAndDownloadMp3) {
    btnMergeAndDownloadMp3.addEventListener('click', () => {
      mergeAndDownloadFullAudiobook();
    });
  }

  // Single audio MP3 download button
  if (btnDownloadAudioMp3) {
    btnDownloadAudioMp3.addEventListener('click', async () => {
      if (!lastGeneratedAudioBlob) {
        showToast('Chưa có file âm thanh AI nào để tải về dạng .MP3', 'warning');
        return;
      }
      const origHtml = btnDownloadAudioMp3.innerHTML;
      try {
        btnDownloadAudioMp3.disabled = true;
        btnDownloadAudioMp3.innerHTML = '<i class="fa-solid fa-spinner fa-spin text-sm"></i> Đang nén...';
        showToast('Đang nén file sang định dạng .MP3...', 'info');

        const res = await fetch('/api/audio/convert-to-mp3', {
          method: 'POST',
          headers: { 'Content-Type': 'audio/wav' },
          body: lastGeneratedAudioBlob
        });

        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData.error || `Lỗi HTTP ${res.status}`);
        }

        const mp3Blob = await res.blob();
        const selectedVoice = voiceSelect.value || 'cheap-tts';
        const filename = `cheap-tts-${selectedVoice}-${Date.now()}.mp3`;
        const url = URL.createObjectURL(mp3Blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);

        const sizeKB = (mp3Blob.size / 1024).toFixed(0);
        showToast(`Đã tải xuống file MP3 "${filename}" (${sizeKB} KB)!`, 'success');
      } catch (err) {
        console.error('MP3 download error:', err);
        showToast(`Lỗi xuất file MP3: ${err.message}`, 'error');
      } finally {
        btnDownloadAudioMp3.disabled = false;
        btnDownloadAudioMp3.innerHTML = origHtml;
      }
    });
  }

  if (wordsPerPartSelect) {
    wordsPerPartSelect.addEventListener('change', () => {
      const text = textInput.value || '';
      if (text.trim()) {
        const size = parseInt(wordsPerPartSelect.value) || 1000;
        parsedChapters = detectChapters(text, size);
        renderChapterList();
        showToast(`Đã chia lại văn bản thành các phần ~${size.toLocaleString()} từ`, 'info');
      }
    });
  }

  // Audio Player Visualizer
  audioPlayer.addEventListener('play', () => startVisualizer());
  audioPlayer.addEventListener('pause', () => stopVisualizer());
  audioPlayer.addEventListener('ended', () => stopVisualizer());

  // Input tracking
  textInput.addEventListener('input', updateStats);

  // Play / Pause / Stop
  btnSpeak.addEventListener('click', handleSpeakAction);
  btnPause.addEventListener('click', togglePause);
  btnStop.addEventListener('click', stopSpeaking);

  // Sliders
  rateRange.addEventListener('input', () => {
    rateValue.textContent = `${parseFloat(rateRange.value).toFixed(1)}x`;
    updateStats();
  });

  pitchRange.addEventListener('input', () => {
    pitchValue.textContent = parseFloat(pitchRange.value).toFixed(1);
  });

  volumeRange.addEventListener('input', () => {
    const vol = parseFloat(volumeRange.value);
    volumeValue.textContent = `${Math.round(vol * 100)}%`;
    if (audioPlayer) audioPlayer.volume = vol;
  });

  pauseDurationRange.addEventListener('input', () => {
    pauseDurationValue.textContent = `${parseFloat(pauseDurationRange.value).toFixed(1)}s`;
  });

  btnClear.addEventListener('click', () => {
    if (textInput.value) {
      textInput.value = '';
      parsedChapters = [];
      updateStats();
      showToast('Đã xóa nội dung', 'info');
      textInput.focus();
    }
  });

  btnPaste.addEventListener('click', async () => {
    try {
      const text = await navigator.clipboard.readText();
      if (text) {
        textInput.value = text;
        updateStats();
        showToast('Đã dán văn bản từ bộ nhớ tạm', 'success');
      }
    } catch {
      showToast('Vui lòng nhấn phím Ctrl+V / Cmd+V để dán', 'warning');
    }
  });

  btnTestVoice.addEventListener('click', handleSpeakAction);
  btnResetSettings.addEventListener('click', resetSettings);
  btnClearHistory.addEventListener('click', clearAllHistory);

  // Samples
  document.querySelectorAll('.sample-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const sampleKey = btn.dataset.sample;
      if (SAMPLES[sampleKey]) {
        textInput.value = SAMPLES[sampleKey];
        updateStats();
        showToast(`Đã áp dụng mẫu "${btn.textContent}"`, 'info');
      }
    });
  });

  // Keyboard Shortcuts
  document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      handleSpeakAction();
    } else if (e.key === 'Escape') {
      e.preventDefault();
      stopSpeaking();
    }
  });

  window.addEventListener('resize', () => setupCanvas());
}

// Start
document.addEventListener('DOMContentLoaded', init);

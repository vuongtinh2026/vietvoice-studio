/**
 * Voxly AI Studio — Multilingual Audio & Video Dubbing Studio (#viewDubbing)
 * - Upload .MP3 / .WAV / .M4A or .MP4 / .MOV / .WEBM Video
 * - Automatic Speech-to-Text (faster-whisper 99 languages) + Cross-Language Translation
 * - Voice Changer (same language, new AI/Cloned voice) OR Foreign Language Dubbing
 * - Instant .MP4 Video Stream Re-Muxing with Original Audio Mute / 15% Ambient Ducking
 */
(function () {
  'use strict';

  const TARGET_LANG_OPTIONS = [
    { value: 'same', vi: '🔄 Giữ nguyên ngôn ngữ gốc (Chỉ đổi sang giọng đọc khác)', en: '🔄 Keep Original Language (Change AI Voice Only)', localePrefix: '' },
    { value: 'vi', vi: '🇻🇳 Dịch sang Tiếng Việt (Vietnamese)', en: '🇻🇳 Translate to Vietnamese (Tiếng Việt)', localePrefix: 'vi' },
    { value: 'en', vi: '🇺🇸🇬🇧 Dịch sang Tiếng Anh (English)', en: '🇺🇸🇬🇧 Translate to English (US / UK)', localePrefix: 'en-' },
    { value: 'zh-CN', vi: '🇨🇳 Dịch sang Tiếng Trung Giản Thể (Mandarin)', en: '🇨🇳 Translate to Chinese (Mandarin)', localePrefix: 'zh-CN' },
    { value: 'zh-TW', vi: '🇹🇼 Dịch sang Tiếng Trung Phồn Thể (Taiwan/HK)', en: '🇹🇼 Translate to Traditional Chinese (TW/HK)', localePrefix: 'zh-TW' },
    { value: 'ja', vi: '🇯🇵 Dịch sang Tiếng Nhật (Japanese)', en: '🇯🇵 Translate to Japanese (日本語)', localePrefix: 'ja-' },
    { value: 'ko', vi: '🇰🇷 Dịch sang Tiếng Hàn (Korean)', en: '🇰🇷 Translate to Korean (한국어)', localePrefix: 'ko-' },
    { value: 'fr', vi: '🇫🇷 Dịch sang Tiếng Pháp (French)', en: '🇫🇷 Translate to French (Français)', localePrefix: 'fr-' },
    { value: 'de', vi: '🇩🇪 Dịch sang Tiếng Đức (German)', en: '🇩🇪 Translate to German (Deutsch)', localePrefix: 'de-' },
    { value: 'es', vi: '🇪🇸 Dịch sang Tiếng Tây Ban Nha (Spanish)', en: '🇪🇸 Translate to Spanish (Español)', localePrefix: 'es-' },
    { value: 'pt', vi: '🇧🇷🇵🇹 Dịch sang Tiếng Bồ Đào Nha (Portuguese)', en: '🇧🇷🇵🇹 Translate to Portuguese', localePrefix: 'pt-' },
    { value: 'ru', vi: '🇷🇺 Dịch sang Tiếng Nga (Russian)', en: '🇷🇺 Translate to Russian (Русский)', localePrefix: 'ru-' },
    { value: 'it', vi: '🇮🇹 Dịch sang Tiếng Ý (Italian)', en: '🇮🇹 Translate to Italian (Italiano)', localePrefix: 'it-' },
    { value: 'th', vi: '🇹🇭 Dịch sang Tiếng Thái (Thai)', en: '🇹🇭 Translate to Thai (ภาษาไทย)', localePrefix: 'th-' },
    { value: 'id', vi: '🇮🇩 Dịch sang Tiếng Indonesia (Indonesian)', en: '🇮🇩 Translate to Indonesian', localePrefix: 'id-' },
    { value: 'ms', vi: '🇲🇾 Dịch sang Tiếng Mã Lai (Malay)', en: '🇲🇾 Translate to Malay', localePrefix: 'ms-' },
    { value: 'km', vi: '🇰🇭 Dịch sang Tiếng Khmer (Cambodia)', en: '🇰🇭 Translate to Khmer', localePrefix: 'km-' },
    { value: 'lo', vi: '🇱🇦 Dịch sang Tiếng Lào (Lao)', en: '🇱🇦 Translate to Lao', localePrefix: 'lo-' },
    { value: 'my', vi: '🇲🇲 Dịch sang Tiếng Myanmar (Burmese)', en: '🇲🇲 Translate to Burmese (Myanmar)', localePrefix: 'my-' },
    { value: 'tl', vi: '🇵🇭 Dịch sang Tiếng Philippines (Filipino)', en: '🇵🇭 Translate to Filipino (Tagalog)', localePrefix: 'fil-' },
    { value: 'hi', vi: '🇮🇳 Dịch sang Tiếng Ấn Độ (Hindi)', en: '🇮🇳 Translate to Hindi (India)', localePrefix: 'hi-' },
    { value: 'ar', vi: '🇸🇦 Dịch sang Tiếng Ả Rập (Arabic)', en: '🇸🇦 Translate to Arabic', localePrefix: 'ar-' },
    { value: 'tr', vi: '🇹🇷 Dịch sang Tiếng Thổ Nhĩ Kỳ (Turkish)', en: '🇹🇷 Translate to Turkish', localePrefix: 'tr-' },
    { value: 'nl', vi: '🇳🇱 Dịch sang Tiếng Hà Lan (Dutch)', en: '🇳🇱 Translate to Dutch', localePrefix: 'nl-' },
    { value: 'pl', vi: '🇵🇱 Dịch sang Tiếng Ba Lan (Polish)', en: '🇵🇱 Translate to Polish', localePrefix: 'pl-' },
    { value: 'uk', vi: '🇺🇦 Dịch sang Tiếng Ukraina (Ukrainian)', en: '🇺🇦 Translate to Ukrainian', localePrefix: 'uk-' },
    { value: 'sv', vi: '🇸🇪 Dịch sang Tiếng Thụy Điển (Swedish)', en: '🇸🇪 Translate to Swedish', localePrefix: 'sv-' },
    { value: 'cs', vi: '🇨🇿 Dịch sang Tiếng Séc (Czech)', en: '🇨🇿 Translate to Czech', localePrefix: 'cs-' },
    { value: 'el', vi: '🇬🇷 Dịch sang Tiếng Hy Lạp (Greek)', en: '🇬🇷 Translate to Greek', localePrefix: 'el-' },
    { value: 'he', vi: '🇮🇱 Dịch sang Tiếng Do Thái (Hebrew)', en: '🇮🇱 Translate to Hebrew', localePrefix: 'he-' }
  ];

  const SOURCE_LANG_OPTIONS = [
    { value: 'auto', vi: '✨ Tự động nhận diện ngôn ngữ nói (Auto-Detect)', en: '✨ Auto-Detect Spoken Language' },
    { value: 'vi', vi: '🇻🇳 Tiếng Việt (Vietnamese)', en: '🇻🇳 Vietnamese' },
    { value: 'en', vi: '🇺🇸🇬🇧 Tiếng Anh (English)', en: '🇺🇸🇬🇧 English' },
    { value: 'zh', vi: '🇨🇳 Tiếng Trung (Chinese)', en: '🇨🇳 Chinese (Mandarin)' },
    { value: 'ja', vi: '🇯🇵 Tiếng Nhật (Japanese)', en: '🇯🇵 Japanese' },
    { value: 'ko', vi: '🇰🇷 Tiếng Hàn (Korean)', en: '🇰🇷 Korean' },
    { value: 'fr', vi: '🇫🇷 Tiếng Pháp (French)', en: '🇫🇷 French' },
    { value: 'de', vi: '🇩🇪 Tiếng Đức (German)', en: '🇩🇪 German' },
    { value: 'es', vi: '🇪🇸 Tiếng Tây Ban Nha (Spanish)', en: '🇪🇸 Spanish' },
    { value: 'pt', vi: '🇧🇷 Tiếng Bồ Đào Nha (Portuguese)', en: '🇧🇷 Portuguese' },
    { value: 'ru', vi: '🇷🇺 Tiếng Nga (Russian)', en: '🇷🇺 Russian' },
    { value: 'th', vi: '🇹🇭 Tiếng Thái (Thai)', en: '🇹🇭 Thai' },
    { value: 'id', vi: '🇮🇩 Tiếng Indonesia', en: '🇮🇩 Indonesian' },
    { value: 'hi', vi: '🇮🇳 Tiếng Ấn Độ (Hindi)', en: '🇮🇳 Hindi' },
    { value: 'ar', vi: '🇸🇦 Tiếng Ả Rập (Arabic)', en: '🇸🇦 Arabic' }
  ];

  let selectedMediaFile = null;
  let selectedIsVideo = false;
  let currentMediaSessionId = '';
  let lastDetectedLang = 'auto';
  let dubVoicesCatalog = [];
  let previewObjUrl = null;
  let activeDubSource = 'none'; // 'none' | 'file' | 'youtube'
  let lastYoutubeKey = '';
  let lastYoutubeTitle = '';

  function normalizeOnlineUrl(raw) {
    const trimmed = String(raw || '').trim();
    if (!trimmed) return '';
    // Extract embedded http(s) URL out of Douyin / TikTok / Bilibili app share text!
    const mHttp = trimmed.match(/https?:\/\/[^\s<>"'，。！？；：）】》]+/i);
    if (mHttp) {
      return mHttp[0].replace(/[.,;!?)\]}'"]+$/, '');
    }
    const mBare = trimmed.match(/(?:www\.|v\.|m\.)?(?:douyin\.com|iesdouyin\.com|youtube\.com|youtu\.be|tiktok\.com|vt\.tiktok\.com|fb\.watch)\/[^\s<>"'，。！？；：）】》]+/i);
    if (mBare) {
      return `https://${mBare[0].replace(/[.,;!?)\]}'"]+$/, '')}`;
    }
    if (/^(www\.|m\.)/i.test(trimmed)) {
      return `https://${trimmed}`;
    }
    return trimmed;
  }

  const CLOUD_AI_MODELS = {
    gemini: [
      { value: 'gemini-2.5-flash', label: 'Gemini 2.5 Flash (Nhanh & Cực Chuẩn)' },
      { value: 'gemini-2.5-pro', label: 'Gemini 2.5 Pro (Đỉnh cao Điện Ảnh)' }
    ],
    deepseek: [
      { value: 'deepseek-chat', label: 'DeepSeek V3 (Trung-Việt Siêu Chuẩn)' }
    ],
    openai: [
      { value: 'gpt-4o-mini', label: 'GPT-4o Mini (Nhanh & Mượt)' },
      { value: 'gpt-4o', label: 'GPT-4o (Biên Kịch Cao Cấp)' }
    ]
  };

  function getProAiConfig() {
    const provider = document.getElementById('dubAiProviderSelect')?.value || 'local';
    const apiKey = (document.getElementById('dubAiApiKeyInput')?.value || '').trim();
    const model = (document.getElementById('dubAiModelSelect')?.value || '').trim();
    return { aiProvider: provider, aiApiKey: apiKey, aiModel: model, multiVoiceCast: false };
  }

  function syncAiProviderUi() {
    const provSel = document.getElementById('dubAiProviderSelect');
    const cfgRow = document.getElementById('dubAiCloudConfigRow');
    const keyIn = document.getElementById('dubAiApiKeyInput');
    const mdlSel = document.getElementById('dubAiModelSelect');
    if (!provSel || !cfgRow) return;
    const prov = provSel.value || 'local';
    try { localStorage.setItem('voxly_dub_ai_provider', prov); } catch {}
    if (prov === 'local' || prov === 'local_14b' || prov === 'local_fast') {
      cfgRow.classList.add('hidden');
      return;
    }
    cfgRow.classList.remove('hidden');
    const models = CLOUD_AI_MODELS[prov] || [];
    if (mdlSel) {
      const savedMdl = (() => { try { return localStorage.getItem(`voxly_dub_ai_model_${prov}`) || ''; } catch { return ''; } })();
      mdlSel.innerHTML = models.map(m => `<option value="${m.value}">${esc(m.label)}</option>`).join('');
      if (savedMdl && models.some(m => m.value === savedMdl)) mdlSel.value = savedMdl;
    }
    if (keyIn) {
      const savedKey = (() => { try { return localStorage.getItem(`voxly_dub_ai_key_${prov}`) || ''; } catch { return ''; } })();
      keyIn.value = savedKey;
      keyIn.placeholder = prov === 'gemini'
        ? 'Dán Google Gemini / Vertex API Key (AIza... hoặc AQ.Ab...) — lưu cục bộ...'
        : (prov === 'deepseek' ? 'Dán DeepSeek API Key (sk-...) — lưu cục bộ...' : 'Dán OpenAI API Key (sk-...) — lưu cục bộ...');
    }
  }

  function stripTimestampsForQuota(raw) {
    return String(raw || '')
      .split(/\r?\n/)
      .map(line => line
        .replace(/^\s*\[\d{1,2}:\d{2}(?::\d{2})?(?:\.\d+)?\s*-\s*\d{1,2}:\d{2}(?::\d{2})?(?:\.\d+)?\]\s*/, '')
        .replace(/^\[[^\]]{2,28}\]\s*/, '')
        .trim())
      .filter(Boolean)
      .join(' ')
      .trim();
  }

  function getOrigVolumePct() {
    const r = document.getElementById('dubOrigVolRange');
    return r ? Math.max(0, Math.min(100, parseInt(r.value, 10) || 0)) : 45;
  }

  function setOrigVolumePct(pctVal) {
    const v = Math.max(0, Math.min(100, Math.round(Number(pctVal) || 0)));
    const r1 = document.getElementById('dubOrigVolRange');
    const r2 = document.getElementById('dubOutOrigVolRange');
    const b1 = document.getElementById('dubOrigVolBadge');
    const b2 = document.getElementById('dubOutOrigVolBadge');
    if (r1 && Number(r1.value) !== v) r1.value = String(v);
    if (r2 && Number(r2.value) !== v) r2.value = String(v);

    const isVi = isViLang();
    const label = v === 0 ? (isVi ? '0% (Tắt)' : '0% (Mute)') : `${v}%`;
    [b1, b2].forEach(b => {
      if (!b) return;
      b.textContent = label;
      b.classList.toggle('text-slate-400', v === 0);
      b.classList.toggle('text-cyan-200', v > 0);
    });

    document.querySelectorAll('.dub-vol-preset').forEach(btn => {
      const p = parseInt(btn.getAttribute('data-orig-vol') || '-1', 10);
      const active = p === v;
      btn.classList.toggle('bg-cyan-500/20', active);
      btn.classList.toggle('border-cyan-400/40', active);
      btn.classList.toggle('text-cyan-200', active);
      btn.classList.toggle('bg-white/5', !active);
      btn.classList.toggle('border-white/10', !active);
    });
  }

  function isViLang() {
    return !window.VoiceVietQuota || window.VoiceVietQuota.getLang() === 'vi';
  }

  function esc(s) {
    return String(s || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function isVideoFilename(name, mime = '') {
    if (String(mime || '').startsWith('video/')) return true;
    return /\.(mp4|mov|webm|mkv|m4v|avi)$/i.test(String(name || ''));
  }

  function populateLanguageDropdowns() {
    const isVi = isViLang();
    const srcSel = document.getElementById('dubSourceLang');
    const tgtSel = document.getElementById('dubTargetLang');
    const bgSel = document.getElementById('dubBgMixSelect');

    if (srcSel) {
      const prev = srcSel.value || 'auto';
      srcSel.innerHTML = SOURCE_LANG_OPTIONS.map(o => `<option value="${o.value}">${esc(isVi ? o.vi : o.en)}</option>`).join('');
      if ([...srcSel.options].some(x => x.value === prev)) srcSel.value = prev;
    }

    if (tgtSel) {
      const defaultTgt = isVi ? 'vi' : 'en';
      const prev = tgtSel.value || defaultTgt;
      tgtSel.innerHTML = TARGET_LANG_OPTIONS.map(o => `<option value="${o.value}">${esc(isVi ? o.vi : o.en)}</option>`).join('');
      tgtSel.value = [...tgtSel.options].some(x => x.value === prev) ? prev : defaultTgt;
    }

    if (bgSel) {
      const prevBg = bgSel.value || 'mute';
      bgSel.innerHTML = isVi
        ? `<option value="mute">🔇 Tắt hẳn tiếng gốc — Thay 100% bằng giọng mới</option>
           <option value="duck15">🔉 Giữ nhạc/tiếng nền gốc nhỏ 15% (Thuyết minh đè)</option>`
        : `<option value="mute">🔇 Mute Original 100% — Clean Voice Replacement</option>
           <option value="duck15">🔉 Keep 15% Original Ambience (Voice-Over Mix)</option>`;
      bgSel.value = prevBg;
    }

    const ytInput = document.getElementById('dubYoutubeUrlInput');
    if (ytInput) {
      ytInput.placeholder = isVi
        ? 'Dán link YouTube, Douyin (douyin.com / v.douyin.com / văn bản chia sẻ app), TikTok...'
        : 'Paste YouTube, Douyin (douyin.com / v.douyin.com / app share text), or TikTok link...';
    }

    const ytModeSel = document.getElementById('dubYoutubeModeSelect');
    if (ytModeSel) {
      const prevMode = ytModeSel.value || 'video';
      ytModeSel.innerHTML = isVi
        ? `<option value="video">🎬 Tải Video .MP4 + Thuyết minh (1080p Full HD)</option>
           <option value="audio">🎵 Chỉ lấy Âm thanh .MP3 (Siêu tốc)</option>`
        : `<option value="video">🎬 Video .MP4 + AI Narration (1080p Full HD)</option>
           <option value="audio">🎵 Audio Only .MP3 (Fast)</option>`;
      ytModeSel.value = prevMode === 'audio' ? 'audio' : 'video';
    }
  }

  function populateDubVoiceDropdown(autoPickForLang = false) {
    const voiceSel = document.getElementById('dubTargetVoice');
    const tgtSel = document.getElementById('dubTargetLang');
    const showAllChk = document.getElementById('dubShowAllVoicesChk');
    if (!voiceSel || !dubVoicesCatalog.length) return;

    const qApi = window.VoiceVietQuota;
    const isVi = isViLang();
    const fmtName = (v) => (qApi && qApi.formatVoiceDisplayName ? qApi.formatVoiceDisplayName(v) : v.name);
    const fmtGender = (g) => (isVi ? (g || '') : (g === 'Nam' ? 'Male' : (g === 'Nữ' ? 'Female' : g)));

    const prevVoice = voiceSel.value;
    const targetVal = tgtSel ? tgtSel.value : 'en';
    const effectiveLang = targetVal === 'same' ? (lastDetectedLang !== 'auto' ? lastDetectedLang : '') : targetVal;
    const targetMeta = TARGET_LANG_OPTIONS.find(o => o.value === effectiveLang);
    const prefix = targetMeta ? targetMeta.localePrefix : (effectiveLang ? effectiveLang.split('-')[0].toLowerCase() : '');
    const showAll = Boolean(showAllChk && showAllChk.checked) || !prefix;

    const privVoices = dubVoicesCatalog.filter(v => v.isPrivate || v.id.startsWith('private-'));
    const matchingVoices = dubVoicesCatalog.filter(v => {
      if (v.isPrivate || v.id.startsWith('private-')) return false;
      if (!prefix) return true;
      if (prefix === 'vi') return v.language === 'vi';
      return String(v.language || '').toLowerCase().startsWith(prefix.toLowerCase());
    });

    const pool = showAll
      ? dubVoicesCatalog.filter(v => !v.isPrivate && !v.id.startsWith('private-'))
      : (matchingVoices.length > 0 ? matchingVoices : dubVoicesCatalog.filter(v => !v.isPrivate && !v.id.startsWith('private-')));

    let html = '';
    if (privVoices.length > 0) {
      html += `<optgroup label="${isVi ? '🔒 Giọng Nhân Bản Độc Quyền Của Tôi' : '🔒 My Private Cloned Voices'}">`;
      privVoices.forEach(v => {
        html += `<option value="${v.id}">🔒 ${esc(fmtName(v))} (${esc(fmtGender(v.gender))})</option>`;
      });
      html += '</optgroup>';
    }

    const viGroup = pool.filter(v => v.language === 'vi');
    const intlGroup = pool.filter(v => v.language !== 'vi');

    if (viGroup.length > 0) {
      html += `<optgroup label="${isVi ? '🇻🇳 Giọng AI Tiếng Việt Studio 48kHz' : '🇻🇳 Vietnamese 48kHz Studio Voices'}">`;
      viGroup.forEach(v => {
        html += `<option value="${v.id}">✨ ${esc(fmtName(v))} (${esc(fmtGender(v.gender))})</option>`;
      });
      html += '</optgroup>';
    }

    if (intlGroup.length > 0) {
      const byCountry = new Map();
      intlGroup.forEach(v => {
        const cKey = (qApi && qApi.formatCountryLocaleLabel) ? qApi.formatCountryLocaleLabel(v) : (v.country || v.language);
        if (!byCountry.has(cKey)) byCountry.set(cKey, []);
        byCountry.get(cKey).push(v);
      });
      byCountry.forEach((arr, cLabel) => {
        html += `<optgroup label="${esc(cLabel)}">`;
        arr.forEach(v => {
          html += `<option value="${v.id}">${esc(fmtName(v))}</option>`;
        });
        html += '</optgroup>';
      });
    }

    voiceSel.innerHTML = html;

    if (!autoPickForLang && prevVoice && [...voiceSel.options].some(o => o.value === prevVoice)) {
      voiceSel.value = prevVoice;
    } else if (matchingVoices.length > 0) {
      const preferredMap = {
        vi: 'free-vi-ngoc-huyen',
        en: 'free-intl-en-us-avamultilingual',
        'zh-CN': 'free-intl-zh-cn-xiaoxiao',
        ja: 'free-intl-ja-jp-nanami',
        ko: 'free-intl-ko-kr-sunhi',
        fr: 'free-intl-fr-fr-viviennemultilingual',
        de: 'free-intl-de-de-tanja',
        es: 'free-intl-es-es-ximena',
        ru: 'free-intl-ru-ru-dmitry',
        th: 'free-intl-th-th-premwadee',
        id: 'free-intl-id-id-gadis',
        hi: 'free-intl-hi-in-swara',
        km: 'free-intl-km-kh-sreymom'
      };
      const prefId = preferredMap[effectiveLang];
      const pref = (prefId && matchingVoices.find(v => v.id === prefId))
        || matchingVoices.find(v => String(v.language || '').toLowerCase() === 'en-us' && v.featured)
        || matchingVoices.find(v => v.featured)
        || matchingVoices[0];
      voiceSel.value = pref.id;
    } else if (voiceSel.options.length > 0) {
      voiceSel.value = voiceSel.options[0].value;
    }
  }

  async function loadDubVoicesCatalog() {
    try {
      const res = await fetch('/api/free-tts/voices');
      const data = await res.json();
      if (data.success && Array.isArray(data.voices)) {
        dubVoicesCatalog = data.voices;
        populateDubVoiceDropdown(true);
      }
    } catch (e) {
      console.warn('Dubbing voice load note:', e);
    }
  }

  function setDubProgress(visible, textStr = '', pct = 0) {
    const box = document.getElementById('dubProgressBox');
    const txt = document.getElementById('dubProgressText');
    const bar = document.getElementById('dubProgressBar');
    const pctEl = document.getElementById('dubProgressPct');
    if (!box) return;
    box.classList.toggle('hidden', !visible);
    if (txt && textStr) txt.textContent = textStr;
    if (bar) bar.style.width = `${Math.max(0, Math.min(100, pct))}%`;
    if (pctEl) pctEl.textContent = `${Math.round(pct)}%`;
  }

  function syncYoutubeInputState() {
    const ytInput = document.getElementById('dubYoutubeUrlInput');
    const ytModeSel = document.getElementById('dubYoutubeModeSelect');
    const btnClear = document.getElementById('btnClearYoutubeUrl');
    const ytBar = document.getElementById('dubYoutubeBar');
    const ytBadge = document.getElementById('dubYoutubeStatusBadge');
    const videoOpts = document.getElementById('dubVideoOptionsRow');

    const rawUrl = normalizeOnlineUrl(ytInput ? ytInput.value : '');
    const ytMode = ytModeSel?.value === 'audio' ? 'audio' : 'video';

    if (btnClear) btnClear.classList.toggle('hidden', !rawUrl);

    if (!rawUrl) {
      if (ytBar) ytBar.classList.remove('ring-1', 'ring-rose-400/60');
      if (ytBadge) ytBadge.classList.add('hidden');
      if (activeDubSource === 'youtube') {
        activeDubSource = selectedMediaFile ? 'file' : 'none';
        currentMediaSessionId = '';
        lastYoutubeKey = '';
        lastYoutubeTitle = '';
      }
      return;
    }

    activeDubSource = 'youtube';
    selectedIsVideo = ytMode === 'video';
    if (ytBar) ytBar.classList.add('ring-1', 'ring-rose-400/60');

    const nextKey = `${rawUrl}|${ytMode}`;
    if (nextKey !== lastYoutubeKey) {
      currentMediaSessionId = '';
      lastYoutubeTitle = '';
      const srcBox = document.getElementById('dubSourceTranscript');
      const trBox = document.getElementById('dubTranslatedScript');
      if (srcBox) srcBox.value = '';
      if (trBox) trBox.value = '';
      document.getElementById('dubScriptsEditorCard')?.classList.add('hidden');
      document.getElementById('dubOutputCard')?.classList.add('hidden');
      document.getElementById('dubOriginalPreviewWrap')?.classList.add('hidden');
      document.getElementById('btnDubQuickRemix')?.classList.add('hidden');
      if (ytBadge) ytBadge.classList.add('hidden');
    }
  }

  function handleSelectMediaFile(file) {
    if (!file) return;
    selectedMediaFile = file;
    activeDubSource = 'file';
    lastYoutubeKey = '';
    lastYoutubeTitle = '';
    selectedIsVideo = isVideoFilename(file.name, file.type);
    currentMediaSessionId = '';
    document.getElementById('dubYoutubeBar')?.classList.remove('ring-1', 'ring-rose-400/60');
    document.getElementById('dubYoutubeStatusBadge')?.classList.add('hidden');
    document.getElementById('btnDubQuickRemix')?.classList.add('hidden');
    const srcBox = document.getElementById('dubSourceTranscript');
    const trBox = document.getElementById('dubTranslatedScript');
    if (srcBox) srcBox.value = '';
    if (trBox) trBox.value = '';
    document.getElementById('dubScriptsEditorCard')?.classList.add('hidden');
    document.getElementById('dubOutputCard')?.classList.add('hidden');

    const isVi = isViLang();
    const fileLabel = document.getElementById('dubSelectedFileLabel');
    const origWrap = document.getElementById('dubOriginalPreviewWrap');
    const origVid = document.getElementById('dubOrigVideoPreview');
    const origAud = document.getElementById('dubOrigAudioPreview');

    const sizeMB = (file.size / (1024 * 1024)).toFixed(2);
    if (fileLabel) {
      const kindBadge = selectedIsVideo
        ? (isVi ? '🎬 VIDEO MP4/MOV' : '🎬 VIDEO')
        : (isVi ? '🎵 ÂM THANH MP3/WAV' : '🎵 AUDIO');
      fileLabel.innerHTML = `<span class="text-emerald-300 font-bold"><i class="fa-solid fa-circle-check mr-1"></i>[${kindBadge}] ${esc(file.name)} (${sizeMB} MB)</span>`;
    }

    if (previewObjUrl) URL.revokeObjectURL(previewObjUrl);
    previewObjUrl = URL.createObjectURL(file);

    if (origWrap && origVid && origAud) {
      origWrap.classList.remove('hidden');
      if (selectedIsVideo) {
        origAud.pause();
        origAud.classList.add('hidden');
        origVid.src = previewObjUrl;
        origVid.classList.remove('hidden');
      } else {
        origVid.pause();
        origVid.classList.add('hidden');
        origAud.src = previewObjUrl;
        origAud.classList.remove('hidden');
      }
    }
  }

  function formatElapsedTimer(sec) {
    const s = Math.max(0, Math.floor(sec));
    const hrs = Math.floor(s / 3600);
    const mins = Math.floor((s % 3600) / 60);
    const rem = s % 60;
    if (hrs > 0) return `${hrs}:${String(mins).padStart(2, '0')}:${String(rem).padStart(2, '0')}`;
    if (mins > 0) return `${mins}:${String(rem).padStart(2, '0')}`;
    return `${rem}s`;
  }

  let activeDubPollGen = 0;

  /**
   * Polls an async server background job (`/api/dubbing/job/:jobId`) every 1.5s so even
   * 2–5+ hour feature films NEVER hit Chromium/Safari idle HTTP fetch timeouts!
   * Supports instant 1-click user cancellation via `#btnDubCancelJob`.
   */
  async function waitForDubAsyncJob(jobId, opts = {}) {
    const myPollGen = ++activeDubPollGen;
    const isVi = isViLang();
    const minPct = opts.minPct ?? 18;
    const maxPct = opts.maxPct ?? 65;
    let liveMsg = opts.baseMsg || '';
    let livePct = minPct;
    const t0 = Date.now();
    let consecutiveNetErrs = 0;

    while (true) {
      await new Promise(r => setTimeout(r, 1500));
      if (myPollGen !== activeDubPollGen) {
        throw new Error(isVi ? 'Đã dừng tác vụ dịch hiện tại.' : 'Current dubbing job was cancelled.');
      }
      const sec = Math.floor((Date.now() - t0) / 1000);
      try {
        const pr = await fetch(`/api/dubbing/job/${encodeURIComponent(jobId)}`);
        if (myPollGen !== activeDubPollGen) {
          throw new Error(isVi ? 'Đã dừng tác vụ dịch hiện tại.' : 'Current dubbing job was cancelled.');
        }
        const jd = await pr.json().catch(() => ({}));
        consecutiveNetErrs = 0;

        if (!pr.ok && jd.status === 'not_found') {
          throw new Error(jd.error || 'Tác vụ nền không còn tồn tại.');
        }
        if (jd.status === 'error') {
          throw new Error(jd.error || 'Lỗi xử lý nền!');
        }
        if (jd.status === 'done') {
          if (window.VoiceVietQuota && typeof window.VoiceVietQuota.syncFromHeaders === 'function') {
            try { window.VoiceVietQuota.syncFromHeaders(pr.headers); } catch {}
          }
          return jd.data || {};
        }

        const pd = jd.progress || {};
        if (pd && pd.active) {
          const msgCandidate = isVi ? pd.vi : pd.en;
          if (msgCandidate) liveMsg = msgCandidate;
          if (typeof pd.pct === 'number' && pd.pct >= minPct && pd.pct <= maxPct) {
            livePct = Math.max(livePct, pd.pct);
          }
        }
        const fallbackPct = Math.min(maxPct, Math.max(livePct, minPct + Math.floor(sec * 0.25)));
        setDubProgress(true, `${liveMsg} (${formatElapsedTimer(sec)})`, fallbackPct);
      } catch (err) {
        if (err && /Lỗi|Tác vụ|Đã dừng|cancelled|Không tìm thấy|vượt quá|hết hạn|HTTP 403/i.test(String(err.message || ''))) {
          throw err;
        }
        consecutiveNetErrs += 1;
        if (consecutiveNetErrs >= 25) {
          throw new Error('Mất kết nối tới máy chủ cục bộ trong lúc xử lý video dài!');
        }
      }
    }
  }

  async function runTranscribeAndTranslate() {
    const isVi = isViLang();
    const ytInput = document.getElementById('dubYoutubeUrlInput');
    const ytUrl = normalizeOnlineUrl(ytInput ? ytInput.value : '');
    const ytMode = document.getElementById('dubYoutubeModeSelect')?.value === 'audio' ? 'audio' : 'video';
    const useYoutube = (activeDubSource === 'youtube' && Boolean(ytUrl)) || (!selectedMediaFile && Boolean(ytUrl));

    if (!useYoutube && !selectedMediaFile) {
      if (typeof window.showToast === 'function') {
        window.showToast(
          isVi
            ? 'Vui lòng dán link YouTube / Douyin hoặc chọn file âm thanh (.mp3, .wav) / video (.mp4) trước!'
            : 'Please paste a YouTube / Douyin URL or choose an audio (.mp3, .wav) / video (.mp4) file first!',
          'warning'
        );
      }
      ytInput?.focus();
      return null;
    }

    const srcLang = document.getElementById('dubSourceLang')?.value || 'auto';
    const tgtLang = document.getElementById('dubTargetLang')?.value || 'en';
    const aiCfg = getProAiConfig();
    const isDouyinLink = /(?:douyin\.com|iesdouyin\.com)/i.test(ytUrl);
    const platName = isDouyinLink ? 'Douyin' : 'YouTube';

    const baseStep1Msg = useYoutube
      ? (isVi
          ? (ytMode === 'video'
              ? `🎬 Bước 1/2: Đang tải Video từ ${platName}, bóc lời & biên dịch thuyết minh chuẩn từng từ...`
              : `🎵 Bước 1/2: Đang trích xuất Âm thanh từ ${platName}, bóc lời & biên dịch thuyết minh...`)
          : (ytMode === 'video'
              ? `🎬 Step 1/2: Downloading ${platName} video, extracting speech & translating exact narration...`
              : `🎵 Step 1/2: Extracting ${platName} audio, transcribing & translating exact narration...`))
      : (isVi
          ? '🎙️ Bước 1/2: AI đang tải tệp, nhận diện lời thoại & biên dịch thuyết minh chuẩn từng từ...'
          : '🎙️ Step 1/2: Uploading media, extracting speech & translating exact narration...');

    setDubProgress(true, baseStep1Msg, 14);

    let res;
    if (useYoutube) {
      if (ytInput && ytInput.value.trim() !== ytUrl) ytInput.value = ytUrl;
      res = await fetch('/api/dubbing/youtube?async=1', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url: ytUrl,
          downloadMode: ytMode,
          sourceLang: srcLang,
          targetLang: tgtLang,
          aiProvider: aiCfg.aiProvider,
          aiApiKey: aiCfg.aiApiKey,
          aiModel: aiCfg.aiModel,
          multiVoiceCast: aiCfg.multiVoiceCast
        })
      });
    } else {
      const upHeaders = {
        'Content-Type': 'application/octet-stream',
        'X-File-Name': encodeURIComponent(selectedMediaFile.name),
        'X-Source-Lang': srcLang,
        'X-Target-Lang': tgtLang,
        'X-Ai-Provider': aiCfg.aiProvider,
        'X-Ai-Model': aiCfg.aiModel,
        'X-Multi-Voice': aiCfg.multiVoiceCast ? '1' : '0'
      };
      if (aiCfg.aiApiKey) upHeaders['X-Ai-Api-Key'] = aiCfg.aiApiKey;
      res = await fetch('/api/dubbing/transcribe-translate?async=1', {
        method: 'POST',
        headers: upHeaders,
        body: selectedMediaFile
      });
    }

    let data = await res.json().catch(() => ({}));
    if (!res.ok || !data.success) {
      throw new Error(data.error || `HTTP ${res.status}`);
    }
    if (data.async && data.jobId) {
      data = await waitForDubAsyncJob(data.jobId, { baseMsg: baseStep1Msg, minPct: 16, maxPct: 66 });
    }
    if (!data || !data.success) {
      throw new Error((data && data.error) || 'Không nhận được kết quả nhận diện lời thoại.');
    }

    currentMediaSessionId = data.mediaSessionId || '';
    lastDetectedLang = data.detectedLang || 'vi';
    selectedIsVideo = Boolean(data.isVideo);

    if (useYoutube) {
      activeDubSource = 'youtube';
      lastYoutubeKey = `${ytUrl}|${ytMode}`;
      lastYoutubeTitle = data.title || 'youtube_video';

      const ytBadge = document.getElementById('dubYoutubeStatusBadge');
      if (ytBadge) {
        ytBadge.textContent = `✅ ${data.title || 'YouTube'} • ${data.durationSec || 0}s`;
        ytBadge.classList.remove('hidden');
      }

      if (data.origPreviewUrl) {
        const origWrap = document.getElementById('dubOriginalPreviewWrap');
        const origVid = document.getElementById('dubOrigVideoPreview');
        const origAud = document.getElementById('dubOrigAudioPreview');
        if (origWrap && origVid && origAud) {
          origWrap.classList.remove('hidden');
          if (selectedIsVideo) {
            origAud.pause();
            origAud.classList.add('hidden');
            origVid.src = data.origPreviewUrl;
            origVid.classList.remove('hidden');
          } else {
            origVid.pause();
            origVid.classList.add('hidden');
            origAud.src = data.origPreviewUrl;
            origAud.classList.remove('hidden');
          }
        }
      }
    }

    const srcBox = document.getElementById('dubSourceTranscript');
    const trBox = document.getElementById('dubTranslatedScript');
    const detBadge = document.getElementById('dubDetectedLangBadge');
    const scriptsCard = document.getElementById('dubScriptsEditorCard');

    if (srcBox) srcBox.value = data.sourceText || '';
    if (trBox) trBox.value = data.translatedText || '';
    if (detBadge) {
      const segCnt = data.segmentsCount || 0;
      detBadge.textContent = isVi
        ? `Ngôn ngữ gốc: ${(data.detectedLang || '').toUpperCase()} • ${data.durationSec || 0}s • ${segCnt} câu thuyết minh`
        : `Detected: ${(data.detectedLang || '').toUpperCase()} • ${data.durationSec || 0}s • ${segCnt} cues`;
    }
    if (scriptsCard) scriptsCard.classList.remove('hidden');

    if (tgtLang === 'same') {
      populateDubVoiceDropdown(false);
    }

    return data;
  }

  function computeOutputBaseSlug() {
    const rawTitleSource = (activeDubSource === 'youtube' && lastYoutubeTitle)
      ? lastYoutubeTitle
      : (selectedMediaFile ? selectedMediaFile.name.replace(/\.[^/.]+$/, '') : 'voxly_dubbed');
    return rawTitleSource
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .replace(/đ/gi, 'd')
      .replace(/[^a-zA-Z0-9_-]+/g, '_')
      .replace(/^_+|_+$/g, '')
      .slice(0, 48) || 'voxly_dubbed';
  }

  function applyRenderedMediaToPlayer(data, preserveSeekSec = null) {
    const outCard = document.getElementById('dubOutputCard');
    const outVidWrap = document.getElementById('dubOutVideoWrap');
    const outVid = document.getElementById('dubResultVideoPlayer');
    const outAudWrap = document.getElementById('dubOutAudioWrap');
    const outAud = document.getElementById('dubResultAudioPlayer');
    const dlMp4 = document.getElementById('btnDubDownloadMp4');
    const dlMp3 = document.getElementById('btnDubDownloadMp3');
    const dlWav = document.getElementById('btnDubDownloadWav');

    if (outCard) outCard.classList.remove('hidden');
    document.getElementById('btnDubQuickRemix')?.classList.remove('hidden');

    const baseSlug = computeOutputBaseSlug();
    const tgtCode = document.getElementById('dubTargetLang')?.value || 'dub';

    if (dlMp3 && data.audioMp3Url) {
      dlMp3.href = data.audioMp3Url;
      dlMp3.download = `${baseSlug}_${tgtCode}_voxly.mp3`;
    }
    if (dlWav && data.audioWavUrl) {
      dlWav.href = data.audioWavUrl;
      dlWav.download = `${baseSlug}_${tgtCode}_48khz.wav`;
    }

    if (data.dubbedVideoUrl && outVidWrap && outVid) {
      outVidWrap.classList.remove('hidden');
      outAudWrap?.classList.add('hidden');
      outVid.src = data.dubbedVideoUrl;
      if (preserveSeekSec !== null && preserveSeekSec > 0) {
        outVid.addEventListener('loadedmetadata', () => {
          outVid.currentTime = Math.min(preserveSeekSec, Math.max(0, (outVid.duration || preserveSeekSec) - 0.1));
          outVid.play().catch(() => {});
        }, { once: true });
      } else {
        outVid.play().catch(() => {});
      }
      if (dlMp4) {
        dlMp4.classList.remove('hidden');
        dlMp4.href = data.dubbedVideoUrl;
        dlMp4.download = `${baseSlug}_${tgtCode}_voxly.mp4`;
      }
    } else {
      outVidWrap?.classList.add('hidden');
      if (dlMp4) dlMp4.classList.add('hidden');
      if (outAudWrap && outAud && data.audioMp3Url) {
        outAudWrap.classList.remove('hidden');
        outAud.src = data.audioMp3Url;
        if (preserveSeekSec !== null && preserveSeekSec > 0) {
          outAud.addEventListener('loadedmetadata', () => {
            outAud.currentTime = Math.min(preserveSeekSec, Math.max(0, (outAud.duration || preserveSeekSec) - 0.1));
            outAud.play().catch(() => {});
          }, { once: true });
        } else {
          outAud.play().catch(() => {});
        }
      }
    }
  }

  async function runRenderDubbing() {
    const isVi = isViLang();
    const trBox = document.getElementById('dubTranslatedScript');
    const text = (trBox ? trBox.value : '').trim();
    const spokenForQuota = stripTimestampsForQuota(text);
    if (!spokenForQuota) {
      if (typeof window.showToast === 'function') {
        window.showToast(
          isVi ? 'Chưa có nội dung bản dịch để lồng tiếng!' : 'Translated script is empty!',
          'warning'
        );
      }
      return;
    }

    if (window.VoiceVietQuota && !window.VoiceVietQuota.checkCanGenerate(spokenForQuota.length)) {
      return;
    }

    const voiceId = document.getElementById('dubTargetVoice')?.value || 'free-vi-ngoc-huyen';
    if (voiceId.startsWith('private-') && typeof window.ensurePrivateVoiceAuthorized === 'function') {
      const ok = await window.ensurePrivateVoiceAuthorized(voiceId);
      if (!ok) return;
    }

    const rate = parseFloat(document.getElementById('rateRange')?.value) || 1.0;
    const pause = parseFloat(document.getElementById('pauseDurationRange')?.value) || 0.25;
    const origVolumePct = getOrigVolumePct();
    const smartDucking = document.getElementById('dubSmartDuckChk') ? document.getElementById('dubSmartDuckChk').checked : true;
    const syncTimeline = document.getElementById('dubSyncTimelineChk') ? document.getElementById('dubSyncTimelineChk').checked : true;
    const autoFitTiming = document.getElementById('dubAutoFitChk') ? document.getElementById('dubAutoFitChk').checked : true;
    const multiVoiceCast = false;

    const baseStep2Msg = selectedIsVideo
      ? (isVi
          ? '🎙️ Bước 2/2: Đang đọc thuyết minh 48kHz khớp mốc thời gian & trộn âm thanh gốc vào Video .MP4...'
          : '🎙️ Step 2/2: Synthesizing timestamp-synced 48kHz narration & mixing original audio into .MP4...')
      : (isVi
          ? '🎧 Bước 2/2: Đang tổng hợp giọng thuyết minh AI 48kHz theo mốc thoại & trộn âm nền...'
          : '🎧 Step 2/2: Synthesizing synced 48kHz narration & mixing original audio...');
    setDubProgress(true, baseStep2Msg, 68);

    const headers = { 'Content-Type': 'application/json' };
    const tok = typeof window.getOwnerToken === 'function' ? window.getOwnerToken() : '';
    if (tok) headers['X-Owner-Token'] = tok;

    const res = await fetch('/api/dubbing/render?async=1', {
      method: 'POST',
      headers,
      body: JSON.stringify({
        text,
        voice: voiceId,
        rate,
        pause,
        origVolumePct,
        smartDucking,
        syncTimeline,
        autoFitTiming,
        multiVoiceCast,
        mediaSessionId: currentMediaSessionId
      })
    });

    let data = await res.json().catch(() => ({}));
    if (!res.ok || !data.success) {
      throw new Error(data.error || `HTTP ${res.status}`);
    }
    if (data.async && data.jobId) {
      data = await waitForDubAsyncJob(data.jobId, { baseMsg: baseStep2Msg, minPct: 68, maxPct: 98 });
    }
    if (!data || !data.success) {
      throw new Error((data && data.error) || 'Lỗi xuất file thuyết minh.');
    }

    if (data.mediaSessionId) currentMediaSessionId = data.mediaSessionId;
    setDubProgress(true, isVi ? '✅ Hoàn tất dịch & thuyết minh chuẩn xác khớp mốc thời gian!' : '✅ Timestamp-synced narration complete!', 100);

    applyRenderedMediaToPlayer(data, null);

    const metaInfo = document.getElementById('dubOutputMetaText');
    const secStr = `${(data.elapsedMs / 1000).toFixed(2)}s`;
    const cuesInfo = data.syncedSegmentsCount
      ? (isVi ? ` • Khớp ${data.syncedSegmentsCount} câu thoại` : ` • Synced ${data.syncedSegmentsCount} cues`)
      : '';
    const volInfo = isVi ? ` • Âm gốc: ${origVolumePct}%` : ` • Orig Audio: ${origVolumePct}%`;
    if (metaInfo) {
      metaInfo.textContent = isVi
        ? `⚡ Hoàn tất trong ${secStr}${cuesInfo}${volInfo} • Giọng thuyết minh: ${data.voiceName} • Thời lượng: ${data.audioSeconds}s • Đã trừ ${(data.charsUsed || 0).toLocaleString('vi-VN')} ký tự`
        : `⚡ Rendered in ${secStr}${cuesInfo}${volInfo} • Narrator: ${data.voiceName} • Duration: ${data.audioSeconds}s • Used ${(data.charsUsed || 0).toLocaleString('en-US')} chars`;
    }

    document.getElementById('dubOutputCard')?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    if (typeof window.showToast === 'function') {
      window.showToast(
        isVi
          ? `🎉 Đã xuất bản thuyết minh khớp lời thoại thành công trong ${secStr}!`
          : `🎉 Synced narration rendered in ${secStr}!`,
        'success'
      );
    }
  }

  async function runQuickVolumeRemix() {
    const isVi = isViLang();
    if (!currentMediaSessionId) return;
    const origVolumePct = getOrigVolumePct();
    const smartDucking = document.getElementById('dubSmartDuckChk') ? document.getElementById('dubSmartDuckChk').checked : true;

    const btnTop = document.getElementById('btnDubQuickRemix');
    const btnOut = document.getElementById('btnDubOutApplyRemix');
    if (btnTop) btnTop.disabled = true;
    if (btnOut) btnOut.disabled = true;

    const outVid = document.getElementById('dubResultVideoPlayer');
    const outAud = document.getElementById('dubResultAudioPlayer');
    const prevSeek = (outVid && !outVid.parentElement.classList.contains('hidden'))
      ? outVid.currentTime
      : (outAud ? outAud.currentTime : 0);

    try {
      const res = await fetch('/api/dubbing/remix', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          mediaSessionId: currentMediaSessionId,
          origVolumePct,
          smartDucking
        })
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok || !data.success) {
        throw new Error(data.error || `HTTP ${res.status}`);
      }

      applyRenderedMediaToPlayer(data, prevSeek);

      const metaInfo = document.getElementById('dubOutputMetaText');
      const secStr = `${(data.elapsedMs / 1000).toFixed(2)}s`;
      if (metaInfo) {
        metaInfo.textContent = isVi
          ? `🎚️ Đã cập nhật Âm lượng gốc: ${origVolumePct}% (${smartDucking ? 'Tự động dìm/nổi thông minh' : 'Giữ đều'}) trong ${secStr} • Thời lượng: ${data.audioSeconds}s • 0 ký tự`
          : `🎚️ Updated Original Audio Mix: ${origVolumePct}% (${smartDucking ? 'Smart Ducking' : 'Constant'}) in ${secStr} • Duration: ${data.audioSeconds}s • 0 chars`;
      }
      if (typeof window.showToast === 'function') {
        window.showToast(
          isVi
            ? `🎚️ Đã cập nhật âm lượng gốc ${origVolumePct}% trong ${secStr} (Không tốn ký tự)!`
            : `🎚️ Updated original audio mix to ${origVolumePct}% in ${secStr} (0 chars used)!`,
          'success'
        );
      }
    } catch (err) {
      if (typeof window.showToast === 'function') {
        window.showToast(err.message, 'error');
      }
    } finally {
      if (btnTop) btnTop.disabled = false;
      if (btnOut) btnOut.disabled = false;
    }
  }

  document.addEventListener('DOMContentLoaded', () => {
    populateLanguageDropdowns();
    loadDubVoicesCatalog();
    setOrigVolumePct(45);

    const aiProvSel = document.getElementById('dubAiProviderSelect');
    const aiKeyIn = document.getElementById('dubAiApiKeyInput');
    const aiMdlSel = document.getElementById('dubAiModelSelect');
    if (aiProvSel) {
      let savedProv = (() => { try { return localStorage.getItem('voxly_dub_ai_provider') || 'local'; } catch { return 'local'; } })();
      if (savedProv === 'local_fast') savedProv = 'local';
      if ([...aiProvSel.options].some(o => o.value === savedProv)) aiProvSel.value = savedProv;
      syncAiProviderUi();
      aiProvSel.addEventListener('change', () => syncAiProviderUi());
    }
    if (aiKeyIn) {
      aiKeyIn.addEventListener('input', () => {
        const p = aiProvSel?.value || 'local';
        if (p !== 'local' && p !== 'local_14b') {
          try { localStorage.setItem(`voxly_dub_ai_key_${p}`, aiKeyIn.value.trim()); } catch {}
        }
      });
    }
    if (aiMdlSel) {
      aiMdlSel.addEventListener('change', () => {
        const p = aiProvSel?.value || 'local';
        if (p !== 'local' && p !== 'local_14b') {
          try { localStorage.setItem(`voxly_dub_ai_model_${p}`, aiMdlSel.value); } catch {}
        }
      });
    }

    const btnCancelJob = document.getElementById('btnDubCancelJob');
    if (btnCancelJob) {
      btnCancelJob.addEventListener('click', async () => {
        activeDubPollGen += 1;
        btnCancelJob.disabled = true;
        try {
          await fetch('/api/dubbing/cancel', { method: 'POST' });
        } catch {}
        setDubProgress(false);
        btnCancelJob.disabled = false;
        const b1 = document.getElementById('btnDubFullAuto');
        const b2 = document.getElementById('btnDubTranscribeOnly');
        const b3 = document.getElementById('btnDubRegenerate');
        if (b1) b1.disabled = false;
        if (b2) b2.disabled = false;
        if (b3) b3.disabled = false;
        if (typeof window.showToast === 'function') {
          window.showToast(
            isViLang() ? '⛔ Đã dừng tác vụ dịch cũ! Bạn có thể dịch video mới ngay.' : '⛔ Stopped current job! You can start a new video now.',
            'info'
          );
        }
      });
    }

    const fileIn = document.getElementById('dubMediaFileInput');
    const btnPick = document.getElementById('btnPickDubMedia');
    const dropZone = document.getElementById('dubDropZone');
    const ytInput = document.getElementById('dubYoutubeUrlInput');
    const ytModeSel = document.getElementById('dubYoutubeModeSelect');
    const btnPasteYt = document.getElementById('btnPasteYoutubeUrl');
    const btnClearYt = document.getElementById('btnClearYoutubeUrl');
    const origVolRange = document.getElementById('dubOrigVolRange');
    const outOrigVolRange = document.getElementById('dubOutOrigVolRange');
    const btnQuickRemix = document.getElementById('btnDubQuickRemix');
    const btnOutApplyRemix = document.getElementById('btnDubOutApplyRemix');
    const tgtSel = document.getElementById('dubTargetLang');
    const showAllChk = document.getElementById('dubShowAllVoicesChk');
    const btnPreviewVoice = document.getElementById('btnDubPreviewVoice');
    const btnFullAuto = document.getElementById('btnDubFullAuto');
    const btnTranscribeOnly = document.getElementById('btnDubTranscribeOnly');
    const btnRetranslate = document.getElementById('btnDubRetranslate');
    const btnRegenerate = document.getElementById('btnDubRegenerate');

    if (origVolRange) {
      origVolRange.addEventListener('input', () => setOrigVolumePct(origVolRange.value));
    }
    if (outOrigVolRange) {
      outOrigVolRange.addEventListener('input', () => setOrigVolumePct(outOrigVolRange.value));
    }
    document.querySelectorAll('.dub-vol-preset').forEach(btn => {
      btn.addEventListener('click', () => {
        setOrigVolumePct(btn.getAttribute('data-orig-vol') || '45');
        if (currentMediaSessionId && !document.getElementById('dubOutputCard')?.classList.contains('hidden')) {
          runQuickVolumeRemix();
        }
      });
    });
    if (btnQuickRemix) {
      btnQuickRemix.addEventListener('click', () => runQuickVolumeRemix());
    }
    if (btnOutApplyRemix) {
      btnOutApplyRemix.addEventListener('click', () => runQuickVolumeRemix());
    }

    if (ytInput) {
      ytInput.addEventListener('input', () => syncYoutubeInputState());
      ytInput.addEventListener('change', () => syncYoutubeInputState());
      ytInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          e.preventDefault();
          syncYoutubeInputState();
          if (btnFullAuto && !btnFullAuto.disabled) btnFullAuto.click();
        }
      });
    }

    if (ytModeSel) {
      ytModeSel.addEventListener('change', () => syncYoutubeInputState());
    }

    if (btnPasteYt && ytInput) {
      btnPasteYt.addEventListener('click', async () => {
        try {
          if (navigator.clipboard && navigator.clipboard.readText) {
            const clip = (await navigator.clipboard.readText()).trim();
            if (clip) {
              ytInput.value = clip;
              syncYoutubeInputState();
              return;
            }
          }
        } catch {}
        ytInput.focus();
        ytInput.select();
        if (typeof window.showToast === 'function') {
          window.showToast(
            isViLang() ? 'Nhấn Cmd+V / Ctrl+V để dán link YouTube vào ô!' : 'Press Cmd+V / Ctrl+V to paste the YouTube URL!',
            'info'
          );
        }
      });
    }

    if (btnClearYt && ytInput) {
      btnClearYt.addEventListener('click', () => {
        ytInput.value = '';
        syncYoutubeInputState();
        ytInput.focus();
      });
    }

    if (btnPick && fileIn) {
      btnPick.addEventListener('click', () => fileIn.click());
      fileIn.addEventListener('change', (e) => {
        const f = e.target.files?.[0];
        if (f) handleSelectMediaFile(f);
      });
    }

    if (dropZone) {
      dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('border-cyan-400', 'bg-cyan-950/20');
      });
      dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('border-cyan-400', 'bg-cyan-950/20');
      });
      dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('border-cyan-400', 'bg-cyan-950/20');
        const f = e.dataTransfer?.files?.[0];
        if (f) handleSelectMediaFile(f);
      });
    }

    if (tgtSel) {
      tgtSel.addEventListener('change', async () => {
        populateDubVoiceDropdown(true);
        // Auto-retranslate if transcript is already extracted!
        const srcTxt = (document.getElementById('dubSourceTranscript')?.value || '').trim();
        if (srcTxt) {
          try {
            if (tgtSel.value === 'same') {
              const trBox = document.getElementById('dubTranslatedScript');
              if (trBox) trBox.value = srcTxt;
              return;
            }
            const r = await fetch('/api/dubbing/retranslate', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                text: srcTxt,
                sourceLang: lastDetectedLang || 'auto',
                targetLang: tgtSel.value,
                ...getProAiConfig()
              })
            });
            const d = await r.json();
            if (r.ok && d.success) {
              const trBox = document.getElementById('dubTranslatedScript');
              if (trBox) trBox.value = d.translatedText || '';
            }
          } catch {}
        }
      });
    }

    if (showAllChk) {
      showAllChk.addEventListener('change', () => populateDubVoiceDropdown(false));
    }

    if (btnPreviewVoice) {
      btnPreviewVoice.addEventListener('click', async () => {
        const vSel = document.getElementById('dubTargetVoice');
        const vId = vSel?.value;
        const vName = vSel?.selectedOptions?.[0]?.textContent || vId;
        if (vId && typeof window.previewSpecificVoice === 'function') {
          const orig = btnPreviewVoice.innerHTML;
          btnPreviewVoice.disabled = true;
          btnPreviewVoice.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
          await window.previewSpecificVoice(vId, vName);
          btnPreviewVoice.disabled = false;
          btnPreviewVoice.innerHTML = orig;
        }
      });
    }

    if (btnFullAuto) {
      btnFullAuto.addEventListener('click', async () => {
        btnFullAuto.disabled = true;
        if (btnTranscribeOnly) btnTranscribeOnly.disabled = true;
        try {
          const existingSrc = (document.getElementById('dubSourceTranscript')?.value || '').trim();
          if (currentMediaSessionId && existingSrc) {
            const tgtVal = document.getElementById('dubTargetLang')?.value || 'vi';
            setDubProgress(
              true,
              isViLang() ? '🌐 Đang dịch sang ngôn ngữ mới...' : '🌐 Translating into selected language...',
              40
            );
            if (tgtVal === 'same') {
              document.getElementById('dubTranslatedScript').value = existingSrc;
            } else {
              const r = await fetch('/api/dubbing/retranslate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text: existingSrc, sourceLang: lastDetectedLang || 'auto', targetLang: tgtVal, ...getProAiConfig() })
              });
              const d = await r.json().catch(() => ({}));
              if (!r.ok || !d.success) throw new Error(d.error || `HTTP ${r.status}`);
              document.getElementById('dubTranslatedScript').value = d.translatedText || '';
            }
            await runRenderDubbing();
          } else {
            const trData = await runTranscribeAndTranslate();
            if (trData) {
              await runRenderDubbing();
            }
          }
        } catch (err) {
          setDubProgress(false);
          if (typeof window.showToast === 'function') {
            window.showToast((isViLang() ? 'Lỗi dịch âm thanh: ' : 'Dubbing error: ') + err.message, 'error');
          }
        } finally {
          btnFullAuto.disabled = false;
          if (btnTranscribeOnly) btnTranscribeOnly.disabled = false;
        }
      });
    }

    if (btnTranscribeOnly) {
      btnTranscribeOnly.addEventListener('click', async () => {
        btnTranscribeOnly.disabled = true;
        if (btnFullAuto) btnFullAuto.disabled = true;
        try {
          const trData = await runTranscribeAndTranslate();
          if (trData) {
            setDubProgress(
              true,
              isViLang()
                ? '✅ Đã bóc lời & dịch thuyết minh xong! Bạn có thể kiểm tra/chỉnh sửa bên dưới rồi bấm Tạo Giọng Thuyết Minh.'
                : '✅ Transcribed & translated! Review/edit below, then click Render Narrated Output.',
              100
            );
          }
        } catch (err) {
          setDubProgress(false);
          if (typeof window.showToast === 'function') {
            window.showToast(err.message, 'error');
          }
        } finally {
          btnTranscribeOnly.disabled = false;
          if (btnFullAuto) btnFullAuto.disabled = false;
        }
      });
    }

    if (btnRetranslate) {
      btnRetranslate.addEventListener('click', async () => {
        const srcTxt = (document.getElementById('dubSourceTranscript')?.value || '').trim();
        const tgtVal = document.getElementById('dubTargetLang')?.value || 'en';
        if (!srcTxt) return;
        btnRetranslate.disabled = true;
        try {
          if (tgtVal === 'same') {
            document.getElementById('dubTranslatedScript').value = srcTxt;
          } else {
            const r = await fetch('/api/dubbing/retranslate', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ text: srcTxt, sourceLang: lastDetectedLang || 'auto', targetLang: tgtVal, ...getProAiConfig() })
            });
            const d = await r.json();
            if (r.ok && d.success) {
              document.getElementById('dubTranslatedScript').value = d.translatedText || '';
            }
          }
        } finally {
          btnRetranslate.disabled = false;
        }
      });
    }

    if (btnRegenerate) {
      btnRegenerate.addEventListener('click', async () => {
        btnRegenerate.disabled = true;
        try {
          await runRenderDubbing();
        } catch (err) {
          setDubProgress(false);
          if (typeof window.showToast === 'function') {
            window.showToast(err.message, 'error');
          }
        } finally {
          btnRegenerate.disabled = false;
        }
      });
    }

    window.addEventListener('voiceviet:langchange', () => {
      populateLanguageDropdowns();
      populateDubVoiceDropdown(false);
      setOrigVolumePct(getOrigVolumePct());
      if (selectedMediaFile) {
        const fileLabel = document.getElementById('dubSelectedFileLabel');
        const sizeMB = (selectedMediaFile.size / (1024 * 1024)).toFixed(2);
        const isVi = isViLang();
        if (fileLabel) {
          const kindBadge = selectedIsVideo
            ? (isVi ? '🎬 VIDEO MP4/MOV' : '🎬 VIDEO')
            : (isVi ? '🎵 ÂM THANH MP3/WAV' : '🎵 AUDIO');
          fileLabel.innerHTML = `<span class="text-emerald-300 font-bold"><i class="fa-solid fa-circle-check mr-1"></i>[${kindBadge}] ${esc(selectedMediaFile.name)} (${sizeMB} MB)</span>`;
        }
      }
    });
  });

  window.reloadDubVoicesCatalog = loadDubVoicesCatalog;
})();

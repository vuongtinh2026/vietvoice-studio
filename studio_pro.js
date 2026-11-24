/**
 * VoiceViet Studio Pro Extensions v3.0
 * - Navigation, VietQR Modal & Dynamic 48kHz Voice Catalog
 * - Smart Long-Story Auto-Role Parser (Narrator + Multi-Character Quotes & Dashes)
 * - Visual Per-Segment Role Distinction & Override
 * - Separated Per-Speaker Audio Export (Voice-Only MP3 + Timeline-Synced CapCut Stem WAV)
 */

(function () {
  'use strict';

  // =========================================================================
  // 1. NAVIGATION VIEW SWITCHER
  // =========================================================================
  const navTabs = document.querySelectorAll('.nav-tab');
  const contentViews = document.querySelectorAll('.content-view');
  const btnHeaderPricing = document.getElementById('btnHeaderPricing');
  const btnSidebarUpgrade = document.getElementById('btnSidebarUpgrade');

  function switchView(targetViewId) {
    contentViews.forEach(view => {
      if (view.id === targetViewId) {
        view.classList.remove('hidden');
      } else {
        view.classList.add('hidden');
      }
    });

    navTabs.forEach(tab => {
      if (tab.getAttribute('data-view') === targetViewId) {
        tab.classList.add('active');
      } else {
        tab.classList.remove('active');
      }
    });

    if (targetViewId === 'viewBatchWord') {
      const batchWordCard = document.getElementById('batchWordCard');
      if (batchWordCard) batchWordCard.classList.remove('hidden');
    }

    const mainEl = document.querySelector('main');
    if (mainEl) mainEl.scrollTo({ top: 0, behavior: 'smooth' });
    if (targetViewId === 'viewStudio' && typeof window.dispatchEvent === 'function') {
      requestAnimationFrame(() => window.dispatchEvent(new Event('resize')));
    }
  }
  window.switchStudioView = switchView;

  navTabs.forEach(tab => {
    tab.addEventListener('click', () => {
      const targetView = tab.getAttribute('data-view');
      if (targetView) switchView(targetView);
    });
  });

  document.querySelectorAll('[data-jump-view]').forEach(el => {
    el.addEventListener('click', () => {
      const target = el.getAttribute('data-jump-view');
      if (target) switchView(target);
    });
  });

  // Hero Showcase Banner Collapse / Expand Toggle
  const btnToggleHeroBanner = document.getElementById('btnToggleHeroBanner');
  const studioHeroBody = document.getElementById('studioHeroBody');
  const heroToggleIcon = document.getElementById('heroToggleIcon');
  const heroToggleText = document.getElementById('heroToggleText');

  function applyHeroCollapseState(collapsed) {
    if (!studioHeroBody) return;
    const qApi = window.VoiceVietQuota;
    if (collapsed) {
      studioHeroBody.classList.add('hidden');
      if (heroToggleIcon) heroToggleIcon.className = 'fa-solid fa-chevron-down text-[10px]';
      if (heroToggleText) heroToggleText.textContent = qApi ? qApi.t('hero_expand') : 'Mở rộng giới thiệu';
    } else {
      studioHeroBody.classList.remove('hidden');
      if (heroToggleIcon) heroToggleIcon.className = 'fa-solid fa-chevron-up text-[10px]';
      if (heroToggleText) heroToggleText.textContent = qApi ? qApi.t('hero_collapse') : 'Thu gọn';
    }
  }

  if (btnToggleHeroBanner && studioHeroBody) {
    let heroCollapsed = localStorage.getItem('voiceviet_hero_collapsed') === '1';
    applyHeroCollapseState(heroCollapsed);
    btnToggleHeroBanner.addEventListener('click', () => {
      heroCollapsed = !heroCollapsed;
      localStorage.setItem('voiceviet_hero_collapsed', heroCollapsed ? '1' : '0');
      applyHeroCollapseState(heroCollapsed);
    });
  }

  if (btnHeaderPricing) btnHeaderPricing.addEventListener('click', () => switchView('viewPricing'));
  if (btnSidebarUpgrade) btnSidebarUpgrade.addEventListener('click', () => switchView('viewPricing'));

  // =========================================================================
  // 2. EXPRESSION / PROSODY QUICK INSERT BUTTONS (... , [cười], [thở dài])
  // =========================================================================
  function insertAtCursor(textarea, cueText) {
    if (!textarea) return;
    const start = textarea.selectionStart ?? textarea.value.length;
    const end = textarea.selectionEnd ?? textarea.value.length;
    const before = textarea.value.slice(0, start);
    const after = textarea.value.slice(end);
    textarea.value = before + cueText + after;
    const newPos = start + cueText.length;
    textarea.focus();
    textarea.setSelectionRange(newPos, newPos);
    textarea.dispatchEvent(new Event('input'));
  }

  document.querySelectorAll('.insert-cue-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      insertAtCursor(document.getElementById('textInput'), btn.getAttribute('data-cue') || '');
    });
  });

  document.querySelectorAll('.insert-dialogue-cue-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      insertAtCursor(document.getElementById('dialogueScriptInput'), btn.getAttribute('data-cue') || '');
    });
  });

  // =========================================================================
  // 3. VIETQR MODAL
  // =========================================================================
  const vietqrModal = document.getElementById('vietqrModal');
  const btnCloseVietqrModal = document.getElementById('btnCloseVietqrModal');
  const vietqrImage = document.getElementById('vietqrImage');
  const vietqrPlanName = document.getElementById('vietqrPlanName');
  const vietqrAmount = document.getElementById('vietqrAmount');
  const vietqrMemo = document.getElementById('vietqrMemo');

  function openVietqrModal(planName, amount) {
    if (typeof window.openRealOrderCheckoutModal === 'function') {
      window.openRealOrderCheckoutModal(planName, amount);
      return;
    }
    if (!vietqrModal) return;
    const memo = `VVDON${Math.floor(100000 + Math.random() * 900000)}`;
    if (vietqrPlanName) vietqrPlanName.textContent = planName;
    if (vietqrAmount) vietqrAmount.textContent = `${parseInt(amount).toLocaleString('vi-VN')} VNĐ`;
    if (vietqrMemo) vietqrMemo.textContent = memo;
    vietqrModal.classList.remove('hidden');
  }

  function closeVietqrModal() {
    if (vietqrModal) vietqrModal.classList.add('hidden');
  }

  document.querySelectorAll('.btn-buy-plan').forEach(btn => {
    btn.addEventListener('click', () => {
      openVietqrModal(btn.getAttribute('data-plan') || 'VIP Tháng', btn.getAttribute('data-amount') || '25000');
    });
  });

  if (btnCloseVietqrModal) btnCloseVietqrModal.addEventListener('click', closeVietqrModal);
  if (vietqrModal) {
    vietqrModal.addEventListener('click', (e) => {
      if (e.target === vietqrModal) closeVietqrModal();
    });
  }

  // =========================================================================
  // 4. DYNAMIC 142-LANGUAGE / 110-COUNTRY CATALOG, DIALOGUE SYNC & PRIVATE VAULT
  // =========================================================================
  const voiceSelect = document.getElementById('voiceSelect');
  const languageFilterSelect = document.getElementById('languageFilterSelect');
  const voiceCatalogGrid = document.getElementById('voiceCatalogGrid');
  const voiceSearchInput = document.getElementById('voiceSearchInput');
  const catalogLanguageFilter = document.getElementById('catalogLanguageFilter');
  const catalogTotalCountBadge = document.getElementById('catalogTotalCountBadge');
  const catalogLoadMoreWrap = document.getElementById('catalogLoadMoreWrap');
  const btnLoadMoreCatalog = document.getElementById('btnLoadMoreCatalog');
  let allCatalogVoices = [];
  let catalogDisplayLimit = 90;

  function escapeHtmlSafe(str) {
    return String(str || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function populateCatalogCountrySelect(selectEl, voicesList) {
    if (!selectEl || !voicesList || !voicesList.length) return;
    const qApi = window.VoiceVietQuota;
    const isVi = !qApi || qApi.getLang() === 'vi';
    if (qApi && typeof qApi.localizeRegionSelectOptions === 'function') {
      qApi.localizeRegionSelectOptions(selectEl);
    }

    const prevVal = selectEl.value || 'all';
    const oldGroup = selectEl.querySelector('optgroup[data-dynamic-countries="1"]');
    if (oldGroup) oldGroup.remove();

    const localeStats = new Map();
    voicesList.forEach(v => {
      if (!v.id.startsWith('free-intl-')) return;
      const loc = v.language;
      if (!localeStats.has(loc)) {
        const locLabel = (qApi && typeof qApi.formatCountryLocaleLabel === 'function')
          ? qApi.formatCountryLocaleLabel(v)
          : (v.country || loc);
        localeStats.set(loc, { label: locLabel, count: 0 });
      }
      localeStats.get(loc).count += 1;
    });

    if (localeStats.size > 0) {
      const og = document.createElement('optgroup');
      og.setAttribute('data-dynamic-countries', '1');
      og.label = isVi
        ? `🏳️ Chọn Trực Tiếp Từng Quốc Gia & Ngôn Ngữ (${localeStats.size} Ngôn ngữ)`
        : `🏳️ Select Specific Country & Language (${localeStats.size} Locales)`;
      localeStats.forEach((info, loc) => {
        const opt = document.createElement('option');
        opt.value = `locale:${loc}`;
        opt.textContent = isVi ? `${info.label} (${info.count} giọng)` : `${info.label} (${info.count} voices)`;
        og.appendChild(opt);
      });
      selectEl.appendChild(og);
    }
    if ([...selectEl.options].some(o => o.value === prevVal)) {
      selectEl.value = prevVal;
    }
  }

  function matchesCatalogCategory(v, cat) {
    if (!cat || cat === 'all') return true;
    const lang = v.language || '';
    const isPriv = Boolean(v.isPrivate || v.id.startsWith('private-'));
    if (cat === 'private') return isPriv;
    if (cat === 'vi') return (lang === 'vi' || v.id.startsWith('vi-')) && !isPriv;
    if (cat.startsWith('region:')) return v.region === cat.slice(7);
    if (cat.startsWith('locale:')) return lang === cat.slice(7);
    return lang.toLowerCase().startsWith(cat.toLowerCase());
  }

  function buildVoiceOptionsHtml(selectedId) {
    const qApi = window.VoiceVietQuota;
    const isVi = !qApi || qApi.getLang() === 'vi';
    const fmtName = (v) => (qApi && qApi.formatVoiceDisplayName ? qApi.formatVoiceDisplayName(v) : v.name);
    const fmtGender = (g) => {
      if (isVi) return g || 'VN';
      if (g === 'Nam') return 'Male';
      if (g === 'Nữ') return 'Female';
      return g || 'Studio';
    };

    if (!allCatalogVoices || allCatalogVoices.length === 0) {
      return `
        <option value="free-vi-ngoc-huyen" ${selectedId === 'free-vi-ngoc-huyen' ? 'selected' : ''}>✨ Ngọc Huyền (Studio 48kHz)</option>
        <option value="free-vi-minh-quan" ${selectedId === 'free-vi-minh-quan' ? 'selected' : ''}>✨ Minh Quân (Studio 48kHz)</option>
        <option value="free-vi-thien-tam" ${selectedId === 'free-vi-thien-tam' ? 'selected' : ''}>✨ Thiện Tâm (Studio 48kHz)</option>
      `;
    }
    const privVoices = allCatalogVoices.filter(v => v.isPrivate || v.id.startsWith('private-'));
    const freeStudioVi = allCatalogVoices.filter(v => v.id.startsWith('free-') && v.language === 'vi' && !v.isPrivate);
    const freeGlobal = allCatalogVoices.filter(v => v.id.startsWith('free-') && v.language !== 'vi');
    const proCloud = allCatalogVoices.filter(v => v.id.startsWith('vi-'));

    let html = '';
    if (privVoices.length > 0) {
      html += `<optgroup label="${isVi ? '🔒 Giọng Nhân Bản Độc Quyền Của Tôi (48kHz Chủ Sở Hữu)' : '🔒 My Private Cloned Voices (48kHz Owner)'}">`;
      privVoices.forEach(v => {
        const sel = v.id === selectedId ? 'selected' : '';
        html += `<option value="${v.id}" ${sel}>🔒 ${escapeHtmlSafe(fmtName(v))} (${fmtGender(v.gender)})</option>`;
      });
      html += '</optgroup>';
    }

    html += `<optgroup label="${isVi ? '✨ Giọng AI Tiếng Việt Studio 48kHz (Khuyên dùng)' : '✨ Vietnamese 48kHz Studio Voices (Recommended)'}">`;
    freeStudioVi.forEach(v => {
      const sel = v.id === selectedId ? 'selected' : '';
      html += `<option value="${v.id}" ${sel}>✨ ${escapeHtmlSafe(fmtName(v))} (${fmtGender(v.gender)})</option>`;
    });
    html += '</optgroup>';

    if (freeGlobal.length > 0) {
      const byCountry = new Map();
      freeGlobal.forEach(v => {
        const cKey = (qApi && qApi.formatCountryLocaleLabel) ? qApi.formatCountryLocaleLabel(v) : (v.country || v.language);
        if (!byCountry.has(cKey)) byCountry.set(cKey, []);
        byCountry.get(cKey).push(v);
      });
      byCountry.forEach((items, cLabel) => {
        html += `<optgroup label="${escapeHtmlSafe(cLabel)}">`;
        items.forEach(v => {
          const sel = v.id === selectedId ? 'selected' : '';
          html += `<option value="${v.id}" ${sel}>${escapeHtmlSafe(fmtName(v))}</option>`;
        });
        html += '</optgroup>';
      });
    }

    if (proCloud.length > 0) {
      html += `<optgroup label="${isVi ? '⚡ Giọng Cheap-TTS Cloud' : '⚡ Cheap-TTS Cloud Voices'}">`;
      proCloud.forEach(v => {
        const sel = v.id === selectedId ? 'selected' : '';
        html += `<option value="${v.id}" ${sel}>${escapeHtmlSafe(fmtName(v))} (${v.id})</option>`;
      });
      html += '</optgroup>';
    }
    return html;
  }

  function refreshAllDialogueSelects() {
    document.querySelectorAll('.dialogue-voice-select').forEach(sel => {
      const cur = sel.value;
      sel.innerHTML = buildVoiceOptionsHtml(cur);
      if (cur) sel.value = cur;
    });
  }

  function syncCatalogRegionTabActive() {
    const activeVal = catalogLanguageFilter ? catalogLanguageFilter.value : 'all';
    document.querySelectorAll('.catalog-region-tab').forEach(tab => {
      const reg = tab.getAttribute('data-region') || 'all';
      if (reg === activeVal) {
        tab.className = 'catalog-region-tab px-3 py-1.5 rounded-xl bg-emerald-500/25 text-emerald-200 border border-emerald-400/50 text-xs font-bold transition cursor-pointer';
      } else {
        tab.className = 'catalog-region-tab px-3 py-1.5 rounded-xl bg-white/5 hover:bg-white/10 text-slate-300 border border-white/10 text-xs font-semibold transition cursor-pointer';
      }
    });
  }

  function renderCatalogCards(resetLimit = false) {
    if (!voiceCatalogGrid || !allCatalogVoices.length) return;
    if (resetLimit) catalogDisplayLimit = 90;

    const qApi = window.VoiceVietQuota;
    const isVi = !qApi || qApi.getLang() === 'vi';
    const cat = catalogLanguageFilter ? catalogLanguageFilter.value : 'all';
    const query = voiceSearchInput ? voiceSearchInput.value.toLowerCase().trim() : '';
    syncCatalogRegionTabActive();

    const visibleVoices = allCatalogVoices.filter(v => {
      if (!matchesCatalogCategory(v, cat)) return false;
      if (!query) return true;
      const locName = qApi && qApi.formatVoiceDisplayName ? qApi.formatVoiceDisplayName(v) : '';
      const locUse = qApi && qApi.formatVoiceUseCase ? qApi.formatVoiceUseCase(v) : '';
      const hay = `${v.name} ${locName} ${v.country || ''} ${v.useCase || ''} ${locUse} ${v.language || ''} ${v.id}`.toLowerCase();
      return hay.includes(query);
    });

    if (catalogTotalCountBadge) {
      const normalizedLangs = new Set(
        visibleVoices.map(v => (v.id.startsWith('free-') || v.id.startsWith('private-')) ? v.language : 'vi')
      );
      catalogTotalCountBadge.textContent = isVi
        ? `${visibleVoices.length.toLocaleString('vi-VN')} Giọng • ${normalizedLangs.size} Ngôn ngữ`
        : `${visibleVoices.length.toLocaleString('en-US')} Voices • ${normalizedLangs.size} Languages`;
    }

    voiceCatalogGrid.innerHTML = '';
    if (visibleVoices.length === 0) {
      if (catalogLoadMoreWrap) catalogLoadMoreWrap.classList.add('hidden');
      voiceCatalogGrid.innerHTML = `<div class="col-span-full text-center py-8 text-xs text-slate-400 italic">${
        isVi ? 'Không tìm thấy giọng đọc nào khớp với bộ lọc hiện tại.' : 'No voices match your current filter.'
      }</div>`;
      return;
    }

    const slice = visibleVoices.slice(0, catalogDisplayLimit);
    const frag = document.createDocumentFragment();

    slice.forEach(v => {
      const isPriv = Boolean(v.isPrivate || v.id.startsWith('private-'));
      const isFreeVi = v.id.startsWith('free-') && v.language === 'vi' && !isPriv;
      const isGlobal = v.id.startsWith('free-') && v.language !== 'vi';
      const isPro = v.id.startsWith('vi-pro-');

      const dispName = (qApi && qApi.formatVoiceDisplayName) ? qApi.formatVoiceDisplayName(v) : v.name;
      const dispUseCase = (qApi && qApi.formatVoiceUseCase) ? qApi.formatVoiceUseCase(v) : (v.useCase || v.id);

      const cleanLetters = dispName.replace(/[^\p{L}\s]/gu, '').trim();
      const initials = (cleanLetters || dispName).split(/\s+/).map(w => w[0]).join('').slice(0, 2).toUpperCase();

      let badgeColor = 'bg-amber-500/20 text-amber-300 border-amber-500/30';
      let avatarBg = 'bg-slate-800 text-amber-400 border border-slate-700';
      let cardBorder = 'border-slate-800 hover:border-amber-500/50';
      let badgeText = v.badge || (isVi ? 'Tiêu Chuẩn' : 'STANDARD');
      let btnBg = 'bg-slate-800 hover:bg-slate-700 text-slate-200';

      if (isPriv) {
        badgeColor = 'bg-amber-500/25 text-amber-300 border-amber-400/50';
        avatarBg = 'bg-gradient-to-tr from-amber-500 to-orange-600 text-slate-950';
        cardBorder = 'border-amber-500/50 hover:border-amber-400 bg-gradient-to-br from-amber-950/20 to-slate-900/90';
        badgeText = isVi ? '🔒 ĐỘC QUYỀN 48kHz' : '🔒 EXCLUSIVE 48kHz';
        btnBg = 'bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-400 text-slate-950 font-bold';
      } else if (isFreeVi) {
        badgeColor = 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30';
        avatarBg = 'bg-gradient-to-tr from-emerald-600 to-teal-600 text-white';
        cardBorder = 'border-emerald-500/30 hover:border-emerald-400';
        badgeText = v.badge || 'STUDIO 48kHz';
        btnBg = 'bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white';
      } else if (isGlobal) {
        badgeColor = 'bg-cyan-500/20 text-cyan-300 border-cyan-500/30';
        avatarBg = 'bg-gradient-to-tr from-cyan-600 to-blue-600 text-white';
        cardBorder = 'border-cyan-500/30 hover:border-cyan-400';
        badgeText = v.badge || 'GLOBAL 48kHz';
        btnBg = 'bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white';
      } else if (isPro) {
        badgeColor = 'bg-purple-500/20 text-purple-300 border-purple-500/30';
        avatarBg = 'bg-gradient-to-tr from-purple-600 to-indigo-600 text-white';
        cardBorder = 'border-purple-500/30 hover:border-purple-500';
        badgeText = 'PRO 48kHz';
        btnBg = 'bg-purple-600 hover:bg-purple-500 text-white';
      }

      const card = document.createElement('div');
      card.className = `voice-luxury-card p-4 rounded-2xl border ${cardBorder} flex flex-col justify-between gap-3.5`;
      card.innerHTML = `
        <div class="flex items-start gap-3">
          <div class="w-10 h-10 rounded-2xl ${avatarBg} flex items-center justify-center font-extrabold text-xs shrink-0 shadow-lg">
            ${isPriv ? '<i class="fa-solid fa-crown text-sm"></i>' : escapeHtmlSafe(initials)}
          </div>
          <div class="flex-1 min-w-0">
            <div class="flex items-start justify-between gap-1.5">
              <h4 class="text-xs font-extrabold text-white line-clamp-2 leading-snug" title="${escapeHtmlSafe(dispName)}">${escapeHtmlSafe(dispName)}</h4>
              <span class="text-[9px] ${badgeColor} border px-1.5 py-0.5 rounded-md font-mono font-semibold shrink-0">${escapeHtmlSafe(badgeText)}</span>
            </div>
            <p class="text-[11px] text-slate-300/90 font-medium mt-1 line-clamp-2 leading-snug">${escapeHtmlSafe(dispUseCase)}</p>
          </div>
        </div>
        <div class="flex items-center gap-2 pt-1 border-t border-white/5">
          <button class="preview-voice-quick-btn px-3 py-1.5 bg-white/5 hover:bg-white/10 text-amber-300 border border-white/10 rounded-xl text-xs font-bold transition cursor-pointer shrink-0" data-voice-id="${v.id}" data-voice-name="${escapeHtmlSafe(dispName)}">
            <i class="fa-solid fa-volume-high mr-1"></i>${isVi ? 'Nghe thử' : 'Preview'}
          </button>
          <button class="select-voice-quick-btn flex-1 py-1.5 ${btnBg} rounded-xl text-xs font-bold transition cursor-pointer shadow" data-voice-id="${v.id}" data-voice-name="${escapeHtmlSafe(dispName)}">
            ${isVi ? 'Chọn Giọng Này' : 'Select Voice'}
          </button>
        </div>
      `;
      frag.appendChild(card);
    });

    voiceCatalogGrid.appendChild(frag);

    if (catalogLoadMoreWrap && btnLoadMoreCatalog) {
      const remaining = visibleVoices.length - slice.length;
      if (remaining > 0) {
        catalogLoadMoreWrap.classList.remove('hidden');
        btnLoadMoreCatalog.innerHTML = isVi
          ? `<i class="fa-solid fa-angles-down mr-1"></i> Xem thêm ${Math.min(150, remaining)} giọng đọc tiếp theo (còn ${remaining.toLocaleString('vi-VN')} giọng)...`
          : `<i class="fa-solid fa-angles-down mr-1"></i> Load ${Math.min(150, remaining)} more voices (${remaining.toLocaleString('en-US')} remaining)...`;
      } else {
        catalogLoadMoreWrap.classList.add('hidden');
      }
    }

    voiceCatalogGrid.querySelectorAll('.preview-voice-quick-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        const vId = btn.getAttribute('data-voice-id');
        const vName = btn.getAttribute('data-voice-name');
        if (typeof window.previewSpecificVoice === 'function') {
          const orig = btn.innerHTML;
          btn.disabled = true;
          btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
          await window.previewSpecificVoice(vId, vName);
          btn.disabled = false;
          btn.innerHTML = orig;
        }
      });
    });

    voiceCatalogGrid.querySelectorAll('.select-voice-quick-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const vId = btn.getAttribute('data-voice-id');
        const vName = btn.getAttribute('data-voice-name');
        if (voiceSelect && vId) {
          if (languageFilterSelect) {
            languageFilterSelect.value = 'all';
            languageFilterSelect.dispatchEvent(new Event('change'));
          }
          if (typeof window.switchEngine === 'function') {
            window.switchEngine((vId.startsWith('free-') || vId.startsWith('private-')) ? 'free' : 'cheaptts');
          }
          voiceSelect.value = vId;
          voiceSelect.dispatchEvent(new Event('change'));
          switchView('viewStudio');
          if (typeof showToast === 'function') {
            showToast(isVi ? `Đã chọn giọng: ${vName}` : `Selected voice: ${vName}`, 'success');
          }
        }
      });
    });
  }

  async function loadAndRenderVoiceCatalog() {
    try {
      const res = await fetch('/api/cheap-tts/voices');
      const data = await res.json();
      if (!data.success || !data.voices) return;

      allCatalogVoices = data.voices;
      populateCatalogCountrySelect(catalogLanguageFilter, allCatalogVoices);
      refreshAllDialogueSelects();
      renderCatalogCards(true);
    } catch (e) {
      console.warn('Cannot render dynamic voice catalog:', e);
    }
  }

  loadAndRenderVoiceCatalog();

  if (btnLoadMoreCatalog) {
    btnLoadMoreCatalog.addEventListener('click', () => {
      catalogDisplayLimit += 150;
      renderCatalogCards(false);
    });
  }
  if (voiceSearchInput) {
    voiceSearchInput.addEventListener('input', () => renderCatalogCards(true));
  }
  if (catalogLanguageFilter) {
    catalogLanguageFilter.addEventListener('change', () => renderCatalogCards(true));
  }

  document.querySelectorAll('.catalog-region-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      const reg = tab.getAttribute('data-region') || 'all';
      if (catalogLanguageFilter) {
        catalogLanguageFilter.value = reg;
        renderCatalogCards(true);
      }
    });
  });

  window.addEventListener('voiceviet:langchange', () => {
    if (allCatalogVoices && allCatalogVoices.length > 0) {
      populateCatalogCountrySelect(catalogLanguageFilter, allCatalogVoices);
      refreshAllDialogueSelects();
      renderCatalogCards(false);
    }
    setVaultUnlockedBadges(lastVaultUnlocked);
    renderPrivateVoicesCards(lastVaultVoices, lastVaultUnlocked);
    syncDefaultSpeakerCardTitlesForLang();
    renderParsedSegmentsPanel();
    const isVi = isViStudio();
    if (!pendingCloneBlob && cloneSelectedFileName) {
      cloneSelectedFileName.textContent = isVi
        ? 'Chưa chọn file giọng mẫu (.mp3, .wav, .m4a, .ogg, .flac)'
        : 'No sample audio selected (.mp3, .wav, .m4a, .ogg, .flac)';
    }
    if (recordCloneMicText && (!micRecorder || micRecorder.state !== 'recording')) {
      recordCloneMicText.textContent = isVi ? 'Thu Âm Micro' : 'Record Mic';
    }
    if (dialogueStatus && (dialogueStatus.textContent.includes('Sẵn sàng') || dialogueStatus.textContent.includes('Ready to parse'))) {
      dialogueStatus.textContent = isVi
        ? 'Sẵn sàng bóc tách & tạo hội thoại đa giọng...'
        : 'Ready to parse & render multi-speaker dialogue...';
    }
    const isCollapsed = studioHeroBody ? studioHeroBody.classList.contains('hidden') : false;
    applyHeroCollapseState(isCollapsed);
  });

  // =========================================================================
  // 4.5 PRIVATE VOICE CLONE VAULT (OWNER PIN + MULTI-WINDOW 48KHZ ENROLLMENT)
  // =========================================================================
  const vaultLockStatusBadge = document.getElementById('vaultLockStatusBadge');
  const sidebarVaultBadge = document.getElementById('sidebarVaultBadge');
  const ownerPinInput = document.getElementById('ownerPinInput');
  const btnTogglePinVisibility = document.getElementById('btnTogglePinVisibility');
  const btnUnlockPrivateVault = document.getElementById('btnUnlockPrivateVault');
  const btnLockPrivateVault = document.getElementById('btnLockPrivateVault');
  const btnToggleChangePin = document.getElementById('btnToggleChangePin');
  const changePinBox = document.getElementById('changePinBox');
  const currentPinInput = document.getElementById('currentPinInput');
  const newPinInput = document.getElementById('newPinInput');
  const btnChangeOwnerPin = document.getElementById('btnChangeOwnerPin');
  const privateVoicesList = document.getElementById('privateVoicesList');
  const privateVoicesCountBadge = document.getElementById('privateVoicesCountBadge');

  const cloneVoiceNameInput = document.getElementById('cloneVoiceNameInput');
  const cloneVoiceGenderSelect = document.getElementById('cloneVoiceGenderSelect');
  const cloneVoiceDescInput = document.getElementById('cloneVoiceDescInput');
  const cloneAudioFileInput = document.getElementById('cloneAudioFileInput');
  const btnPickCloneFile = document.getElementById('btnPickCloneFile');
  const btnRecordCloneMic = document.getElementById('btnRecordCloneMic');
  const recordCloneMicText = document.getElementById('recordCloneMicText');
  const cloneDropZone = document.getElementById('cloneDropZone');
  const cloneSelectedFileName = document.getElementById('cloneSelectedFileName');
  const cloneSamplePreviewPlayer = document.getElementById('cloneSamplePreviewPlayer');
  const cloneVoiceStatus = document.getElementById('cloneVoiceStatus');
  const btnCreateCloneVoice = document.getElementById('btnCreateCloneVoice');

  let pendingCloneBlob = null;
  let micRecorder = null;
  let micChunks = [];
  let lastVaultVoices = [];
  let lastVaultUnlocked = false;

  function isViStudio() {
    return !window.VoiceVietQuota || window.VoiceVietQuota.getLang() === 'vi';
  }

  function setVaultUnlockedBadges(isUnlocked) {
    lastVaultUnlocked = Boolean(isUnlocked);
    const isVi = isViStudio();
    if (vaultLockStatusBadge) {
      if (isUnlocked) {
        vaultLockStatusBadge.className = 'text-[11px] bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 px-2.5 py-0.5 rounded-full font-bold flex items-center gap-1';
        vaultLockStatusBadge.innerHTML = isVi
          ? '<i class="fa-solid fa-unlock text-[10px]"></i> ĐÃ MỞ KHÓA CHỦ SỞ HỮU'
          : '<i class="fa-solid fa-unlock text-[10px]"></i> OWNER VAULT UNLOCKED';
      } else {
        vaultLockStatusBadge.className = 'text-[11px] bg-rose-500/20 text-rose-300 border border-rose-500/40 px-2.5 py-0.5 rounded-full font-bold flex items-center gap-1';
        vaultLockStatusBadge.innerHTML = isVi
          ? '<i class="fa-solid fa-lock text-[10px]"></i> ĐANG KHÓA BẢO VỆ'
          : '<i class="fa-solid fa-lock text-[10px]"></i> LOCKED & PROTECTED';
      }
    }
    if (sidebarVaultBadge) {
      if (isUnlocked) {
        sidebarVaultBadge.className = 'text-[9px] bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 px-1.5 py-0.5 rounded-md ml-auto font-semibold';
        sidebarVaultBadge.textContent = isVi ? '🔓 Đã Mở' : '🔓 Unlocked';
      } else {
        sidebarVaultBadge.className = 'text-[9px] bg-rose-500/20 text-rose-300 border border-rose-500/30 px-1.5 py-0.5 rounded-md ml-auto font-semibold';
        sidebarVaultBadge.textContent = isVi ? '🔒 Khóa' : '🔒 Locked';
      }
    }
  }

  function renderPrivateVoicesCards(voices, isUnlocked) {
    lastVaultVoices = Array.isArray(voices) ? voices : [];
    lastVaultUnlocked = Boolean(isUnlocked);
    if (!privateVoicesList) return;
    const isVi = isViStudio();
    const qApi = window.VoiceVietQuota;

    if (privateVoicesCountBadge) {
      privateVoicesCountBadge.textContent = isVi
        ? `${lastVaultVoices.length} giọng độc quyền`
        : `${lastVaultVoices.length} exclusive voice${lastVaultVoices.length === 1 ? '' : 's'}`;
    }
    if (!lastVaultVoices.length) {
      privateVoicesList.innerHTML = `<div class="col-span-full p-4 rounded-xl bg-slate-900/60 border border-slate-800 text-xs text-slate-400 italic text-center">${
        isVi
          ? 'Chưa có giọng nhân bản nào trong két sắt. Hãy tải file thu âm giọng của bạn lên khung bên dưới để nhân bản!'
          : 'No cloned voices in your vault yet. Upload a voice sample or record via microphone below to clone your voice!'
      }</div>`;
      return;
    }

    privateVoicesList.innerHTML = '';
    lastVaultVoices.forEach(v => {
      const dispUse = (qApi && qApi.formatVoiceUseCase) ? qApi.formatVoiceUseCase(v) : (v.useCase || '');
      const card = document.createElement('div');
      card.className = 'p-4 rounded-2xl bg-gradient-to-br from-slate-900 via-amber-950/15 to-slate-900 border border-amber-500/40 flex flex-col justify-between gap-3 shadow-xl';
      card.innerHTML = `
        <div class="flex items-start justify-between gap-3">
          <div class="flex items-start gap-3">
            <div class="w-11 h-11 rounded-xl bg-gradient-to-tr from-amber-500 to-orange-600 text-slate-950 flex items-center justify-center shadow-md shrink-0">
              <i class="fa-solid fa-crown text-lg"></i>
            </div>
            <div>
              <h4 class="text-xs sm:text-sm font-bold text-white flex flex-wrap items-center gap-1.5">
                <span>${escapeHtmlSafe(v.name)}</span>
                <span class="text-[9px] px-1.5 py-0.5 rounded font-mono ${isUnlocked ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30' : 'bg-rose-500/20 text-rose-300 border border-rose-500/30'}">
                  ${isUnlocked ? (isVi ? '🔓 Sẵn sàng' : '🔓 Ready') : (isVi ? '🔒 Đang khóa' : '🔒 Locked')}
                </span>
              </h4>
              <p class="text-[11px] text-slate-300 mt-1 leading-relaxed">${escapeHtmlSafe(dispUse)}</p>
              ${v.createdAt ? `<p class="text-[10px] text-slate-500 mt-1 font-mono">${isVi ? 'Mã hóa lúc:' : 'Encrypted:'} ${escapeHtmlSafe(v.createdAt)} • 48,000 Hz</p>` : ''}
            </div>
          </div>
          <button type="button" class="btn-delete-private-voice text-slate-500 hover:text-rose-400 text-xs p-1 cursor-pointer transition" data-voice-id="${v.id}" data-voice-name="${escapeHtmlSafe(v.name)}" title="${isVi ? 'Xóa vĩnh viễn giọng này khỏi két sắt' : 'Permanently delete from vault'}">
            <i class="fa-regular fa-trash-can"></i>
          </button>
        </div>

        <div class="flex flex-wrap items-center gap-2 pt-2 border-t border-slate-800/80">
          <button type="button" class="btn-preview-priv px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-amber-300 border border-slate-700 text-xs font-semibold transition cursor-pointer flex items-center gap-1.5" data-voice-id="${v.id}" data-voice-name="${escapeHtmlSafe(v.name)}">
            <i class="fa-solid fa-volume-high"></i> ${isVi ? 'Nghe thử 48kHz' : 'Preview 48kHz'}
          </button>
          <button type="button" class="btn-use-priv-studio flex-1 py-1.5 px-3 rounded-lg bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-400 text-slate-950 text-xs font-extrabold transition cursor-pointer flex items-center justify-center gap-1.5" data-voice-id="${v.id}" data-voice-name="${escapeHtmlSafe(v.name)}">
            <i class="fa-solid fa-wand-magic-sparkles"></i> ${isVi ? 'Chọn Dùng Ở Studio' : 'Use in Studio'}
          </button>
          <button type="button" class="btn-use-priv-dialogue px-3 py-1.5 rounded-lg bg-cyan-600/25 hover:bg-cyan-600/40 text-cyan-300 border border-cyan-500/40 text-xs font-semibold transition cursor-pointer" data-voice-id="${v.id}" data-voice-name="${escapeHtmlSafe(v.name)}" title="${isVi ? 'Đưa giọng của bạn vào vai Người dẫn chuyện trong Hội Thoại Đa Giọng' : 'Assign to Narrator (C) in Multi-Speaker Studio'}">
            <i class="fa-solid fa-comments mr-1"></i>${isVi ? 'Đa Giọng' : 'Multi-Speaker'}
          </button>
        </div>
      `;

      card.querySelector('.btn-preview-priv')?.addEventListener('click', async (ev) => {
        const btn = ev.currentTarget;
        if (typeof window.previewSpecificVoice === 'function') {
          const orig = btn.innerHTML;
          btn.disabled = true;
          btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang tạo...';
          await window.previewSpecificVoice(v.id, v.name);
          btn.disabled = false;
          btn.innerHTML = orig;
        }
      });

      card.querySelector('.btn-use-priv-studio')?.addEventListener('click', async () => {
        if (typeof window.ensurePrivateVoiceAuthorized === 'function') {
          const ok = await window.ensurePrivateVoiceAuthorized(v.id);
          if (!ok) return;
        }
        if (languageFilterSelect) {
          languageFilterSelect.value = 'all';
          languageFilterSelect.dispatchEvent(new Event('change'));
        }
        if (typeof window.switchEngine === 'function') window.switchEngine('free');
        if (voiceSelect) {
          voiceSelect.value = v.id;
          voiceSelect.dispatchEvent(new Event('change'));
        }
        switchView('viewStudio');
        if (typeof showToast === 'function') showToast(`👑 Đã chọn "${v.name}"! Sẵn sàng đọc kịch bản của bạn.`, 'success');
      });

      card.querySelector('.btn-use-priv-dialogue')?.addEventListener('click', async () => {
        if (typeof window.ensurePrivateVoiceAuthorized === 'function') {
          const ok = await window.ensurePrivateVoiceAuthorized(v.id);
          if (!ok) return;
        }
        const selC = document.getElementById('dialogueVoiceC');
        if (selC) selC.value = v.id;
        switchView('viewDialogue');
        if (typeof showToast === 'function') showToast(`👑 Đã gán "${v.name}" cho vai Người dẫn chuyện (C)!`, 'success');
      });

      card.querySelector('.btn-delete-private-voice')?.addEventListener('click', async () => {
        if (!window.confirm(`Bạn có chắc chắn muốn xóa vĩnh viễn giọng "${v.name}" khỏi Két Sắt không?`)) return;
        if (typeof window.ensurePrivateVoiceAuthorized === 'function') {
          const ok = await window.ensurePrivateVoiceAuthorized(v.id);
          if (!ok) return;
        }
        try {
          const tok = typeof window.getOwnerToken === 'function' ? window.getOwnerToken() : '';
          const r = await fetch('/api/private-voices/delete', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-Owner-Token': tok },
            body: JSON.stringify({ voiceId: v.id })
          });
          const d = await r.json();
          if (!r.ok || !d.success) throw new Error(d.error || 'Không thể xóa giọng');
          if (typeof window.reloadAllVoicesCatalog === 'function') await window.reloadAllVoicesCatalog();
          await loadAndRenderVoiceCatalog();
          await refreshVaultStatusUI();
          if (typeof showToast === 'function') showToast(`Đã xóa giọng "${v.name}" khỏi Két Sắt.`, 'info');
        } catch (err) {
          if (typeof showToast === 'function') showToast(`Lỗi xóa giọng: ${err.message}`, 'error');
        }
      });

      privateVoicesList.appendChild(card);
    });
  }

  async function refreshVaultStatusUI() {
    try {
      const tok = typeof window.getOwnerToken === 'function' ? window.getOwnerToken() : '';
      const r = await fetch('/api/private-voices/status', {
        headers: tok ? { 'X-Owner-Token': tok } : {}
      });
      const data = await r.json();
      if (data.success) {
        if (!data.unlocked && tok && typeof window.setOwnerToken === 'function') {
          window.setOwnerToken('');
        }
        setVaultUnlockedBadges(Boolean(data.unlocked));
        renderPrivateVoicesCards(data.voices || [], Boolean(data.unlocked));
      }
    } catch (e) {
      console.warn('Vault status check error:', e);
    }
  }
  window.refreshVaultStatusUI = refreshVaultStatusUI;
  refreshVaultStatusUI();

  if (btnTogglePinVisibility && ownerPinInput) {
    btnTogglePinVisibility.addEventListener('click', () => {
      const isPwd = ownerPinInput.type === 'password';
      ownerPinInput.type = isPwd ? 'text' : 'password';
      btnTogglePinVisibility.innerHTML = isPwd ? '<i class="fa-regular fa-eye-slash"></i>' : '<i class="fa-regular fa-eye"></i>';
    });
  }

  async function handleOwnerUnlock() {
    const pin = ownerPinInput ? ownerPinInput.value.trim() : '';
    if (!pin) {
      if (typeof showToast === 'function') showToast('Vui lòng nhập Mã PIN / Mật khẩu Chủ Sở Hữu!', 'warning');
      ownerPinInput?.focus();
      return;
    }
    if (btnUnlockPrivateVault) btnUnlockPrivateVault.disabled = true;
    try {
      const r = await fetch('/api/private-voices/unlock', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pin })
      });
      const data = await r.json();
      if (!r.ok || !data.success) throw new Error(data.error || 'Mã PIN Chủ Sở Hữu không đúng!');
      if (typeof window.setOwnerToken === 'function') window.setOwnerToken(data.token);
      if (ownerPinInput) ownerPinInput.value = '';
      await refreshVaultStatusUI();
      if (typeof showToast === 'function') showToast('🔓 Đã mở khóa Két Sắt Giọng Độc Quyền thành công!', 'success');
    } catch (err) {
      if (typeof showToast === 'function') showToast(err.message, 'error');
    } finally {
      if (btnUnlockPrivateVault) btnUnlockPrivateVault.disabled = false;
    }
  }

  if (btnUnlockPrivateVault) btnUnlockPrivateVault.addEventListener('click', handleOwnerUnlock);
  if (ownerPinInput) {
    ownerPinInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        handleOwnerUnlock();
      }
    });
  }

  if (btnLockPrivateVault) {
    btnLockPrivateVault.addEventListener('click', async () => {
      try {
        await fetch('/api/private-voices/lock', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' });
      } catch {}
      if (typeof window.setOwnerToken === 'function') window.setOwnerToken('');
      await refreshVaultStatusUI();
      if (typeof showToast === 'function') {
        showToast('🔒 Đã KHÓA Két Sắt! Không một ai khác có thể sử dụng giọng của bạn.', 'success');
      }
    });
  }

  if (btnToggleChangePin && changePinBox) {
    btnToggleChangePin.addEventListener('click', () => {
      changePinBox.classList.toggle('hidden');
    });
  }

  if (btnChangeOwnerPin) {
    btnChangeOwnerPin.addEventListener('click', async () => {
      const currentPin = currentPinInput ? currentPinInput.value.trim() : '';
      const newPin = newPinInput ? newPinInput.value.trim() : '';
      if (!currentPin || !newPin) {
        if (typeof showToast === 'function') showToast('Vui lòng nhập đầy đủ mật khẩu hiện tại và mật khẩu mới!', 'warning');
        return;
      }
      btnChangeOwnerPin.disabled = true;
      try {
        const r = await fetch('/api/private-voices/change-pin', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ currentPin, newPin })
        });
        const data = await r.json();
        if (!r.ok || !data.success) throw new Error(data.error || 'Đổi mật khẩu thất bại!');
        if (typeof window.setOwnerToken === 'function') window.setOwnerToken(data.token);
        if (currentPinInput) currentPinInput.value = '';
        if (newPinInput) newPinInput.value = '';
        changePinBox?.classList.add('hidden');
        await refreshVaultStatusUI();
        if (typeof showToast === 'function') showToast('🔐 Đã cập nhật Mật khẩu Chủ Sở Hữu mới & mã hóa lại Két Sắt!', 'success');
      } catch (err) {
        if (typeof showToast === 'function') showToast(err.message, 'error');
      } finally {
        btnChangeOwnerPin.disabled = false;
      }
    });
  }

  function setSelectedCloneSample(fileOrBlob, displayLabel) {
    pendingCloneBlob = fileOrBlob;
    if (cloneSelectedFileName) {
      const sizeKB = (fileOrBlob.size / 1024).toFixed(1);
      cloneSelectedFileName.innerHTML = `<span class="text-emerald-300"><i class="fa-solid fa-circle-check mr-1"></i>Đã nạp mẫu: <b>${escapeHtmlSafe(displayLabel)}</b> (${sizeKB} KB)</span>`;
    }
    if (cloneSamplePreviewPlayer) {
      cloneSamplePreviewPlayer.src = URL.createObjectURL(fileOrBlob);
      cloneSamplePreviewPlayer.classList.remove('hidden');
    }
  }

  if (btnPickCloneFile && cloneAudioFileInput) {
    btnPickCloneFile.addEventListener('click', () => cloneAudioFileInput.click());
    cloneAudioFileInput.addEventListener('change', (e) => {
      const f = e.target.files?.[0];
      if (f) setSelectedCloneSample(f, f.name);
    });
  }

  if (cloneDropZone) {
    cloneDropZone.addEventListener('dragover', (e) => {
      e.preventDefault();
      cloneDropZone.classList.add('border-purple-400');
    });
    cloneDropZone.addEventListener('dragleave', () => {
      cloneDropZone.classList.remove('border-purple-400');
    });
    cloneDropZone.addEventListener('drop', (e) => {
      e.preventDefault();
      cloneDropZone.classList.remove('border-purple-400');
      const f = e.dataTransfer?.files?.[0];
      if (f) setSelectedCloneSample(f, f.name);
    });
  }

  if (btnRecordCloneMic) {
    btnRecordCloneMic.addEventListener('click', async () => {
      if (micRecorder && micRecorder.state === 'recording') {
        micRecorder.stop();
        return;
      }
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        if (typeof showToast === 'function') showToast('Trình duyệt không hỗ trợ thu âm trực tiếp, vui lòng chọn file âm thanh!', 'warning');
        return;
      }
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        micChunks = [];
        micRecorder = new MediaRecorder(stream);
        micRecorder.ondataavailable = (ev) => {
          if (ev.data && ev.data.size > 0) micChunks.push(ev.data);
        };
        micRecorder.onstop = () => {
          stream.getTracks().forEach(t => t.stop());
          const blob = new Blob(micChunks, { type: micRecorder.mimeType || 'audio/webm' });
          setSelectedCloneSample(blob, `Thu-am-truc-tiep-${new Date().toLocaleTimeString('vi-VN')}.webm`);
          if (recordCloneMicText) recordCloneMicText.textContent = 'Thu Âm Micro';
          btnRecordCloneMic.classList.remove('bg-rose-600', 'text-white', 'animate-pulse');
          if (typeof showToast === 'function') showToast('Đã hoàn tất thu âm giọng mẫu!', 'success');
        };
        micRecorder.start();
        if (recordCloneMicText) recordCloneMicText.textContent = 'Đang thu... (Bấm để dừng)';
        btnRecordCloneMic.classList.add('bg-rose-600', 'text-white', 'animate-pulse');
      } catch (err) {
        if (typeof showToast === 'function') showToast('Không thể truy cập Micro: ' + err.message, 'error');
      }
    });
  }

  if (btnCreateCloneVoice) {
    btnCreateCloneVoice.addEventListener('click', async () => {
      if (!pendingCloneBlob) {
        if (typeof showToast === 'function') showToast('Vui lòng chọn file âm thanh giọng mẫu hoặc bấm Thu Âm Micro trước!', 'warning');
        return;
      }
      const name = (cloneVoiceNameInput?.value || '').trim() || '👑 Giọng Độc Quyền Của Tôi';
      const gender = cloneVoiceGenderSelect?.value || 'Nam';
      const description = (cloneVoiceDescInput?.value || '').trim() || 'Giọng nhân bản cá nhân độc quyền (48kHz Studio)';

      if (typeof window.ensurePrivateVoiceAuthorized === 'function') {
        const ok = await window.ensurePrivateVoiceAuthorized('private-enroll');
        if (!ok) return;
      }

      const origHtml = btnCreateCloneVoice.innerHTML;
      btnCreateCloneVoice.disabled = true;
      btnCreateCloneVoice.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang phân tích thanh quản & mã hóa 48kHz...';
      if (cloneVoiceStatus) {
        cloneVoiceStatus.innerHTML = '<span class="text-amber-300 font-semibold"><i class="fa-solid fa-spinner fa-spin mr-1"></i> Đang lọc tạp âm phòng thu, trích xuất đa cửa sổ thanh quản & mã hóa PBKDF2-SHA256 (~5-12 giây)...</span>';
      }

      try {
        const base64Audio = await new Promise((resolve, reject) => {
          const reader = new FileReader();
          reader.onload = () => {
            const resStr = String(reader.result || '');
            const commaIdx = resStr.indexOf(',');
            resolve(commaIdx >= 0 ? resStr.slice(commaIdx + 1) : resStr);
          };
          reader.onerror = () => reject(new Error('Không thể đọc file âm thanh'));
          reader.readAsDataURL(pendingCloneBlob);
        });

        const tok = typeof window.getOwnerToken === 'function' ? window.getOwnerToken() : '';
        const res = await fetch('/api/private-voices/enroll', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-Owner-Token': tok
          },
          body: JSON.stringify({
            name,
            gender,
            description,
            audioBase64: base64Audio
          })
        });
        const data = await res.json();
        if (!res.ok || !data.success) throw new Error(data.error || 'Không thể nhân bản giọng đọc');

        if (typeof window.reloadAllVoicesCatalog === 'function') await window.reloadAllVoicesCatalog();
        await loadAndRenderVoiceCatalog();
        await refreshVaultStatusUI();

        if (cloneVoiceNameInput) cloneVoiceNameInput.value = '';
        if (cloneVoiceDescInput) cloneVoiceDescInput.value = '';
        pendingCloneBlob = null;
        if (cloneSamplePreviewPlayer) cloneSamplePreviewPlayer.classList.add('hidden');
        if (cloneSelectedFileName) cloneSelectedFileName.textContent = 'Đã nhân bản & khóa bảo mật vào Két Sắt thành công!';
        if (cloneVoiceStatus) {
          cloneVoiceStatus.innerHTML = `<span class="text-emerald-400 font-bold"><i class="fa-solid fa-circle-check mr-1"></i> Hoàn tất! Giọng "${escapeHtmlSafe(data.voice?.name || name)}" đã sẵn sàng ở chuẩn 48kHz!</span>`;
        }
        if (typeof showToast === 'function') {
          showToast(`👑 Đã nhân bản & mã hóa giọng "${data.voice?.name || name}" thành công!`, 'success');
        }
      } catch (err) {
        if (cloneVoiceStatus) {
          cloneVoiceStatus.innerHTML = `<span class="text-rose-400 font-semibold"><i class="fa-solid fa-triangle-exclamation mr-1"></i> ${escapeHtmlSafe(err.message)}</span>`;
        }
        if (typeof showToast === 'function') showToast(`Lỗi nhân bản giọng: ${err.message}`, 'error');
      } finally {
        btnCreateCloneVoice.disabled = false;
        btnCreateCloneVoice.innerHTML = origHtml;
      }
    });
  }

  // =========================================================================
  // 5. MULTI-SPEAKER LONG-STORY PARSER & PER-VOICE SEPARATED TRACK STUDIO
  // =========================================================================
  const speakerGrid = document.getElementById('dialogueSpeakerCardsGrid');
  const btnAddDialogueSpeaker = document.getElementById('btnAddDialogueSpeaker');
  const btnAutoParseStory = document.getElementById('btnAutoParseStory');
  const btnLoadLongStorySample = document.getElementById('btnLoadLongStorySample');
  const btnLoadDialogueSample = document.getElementById('btnLoadDialogueSample');
  const dialogueScriptInput = document.getElementById('dialogueScriptInput');
  const dialogueParsedPanel = document.getElementById('dialogueParsedPanel');
  const dialogueParsedCountBadge = document.getElementById('dialogueParsedCountBadge');
  const dialogueRoleSummaryBadges = document.getElementById('dialogueRoleSummaryBadges');
  const dialogueSegmentsList = document.getElementById('dialogueSegmentsList');
  const btnGenerateDialogue = document.getElementById('btnGenerateDialogue');
  const btnStopDialogue = document.getElementById('btnStopDialogue');
  const dialogueStatus = document.getElementById('dialogueStatus');
  const dialogueOutputContainer = document.getElementById('dialogueOutputContainer');
  const dialogueAudioPlayer = document.getElementById('dialogueAudioPlayer');
  const btnDownloadDialogueMp3 = document.getElementById('btnDownloadDialogueMp3');
  const btnDownloadDialogueWav = document.getElementById('btnDownloadDialogueWav');
  const dialogueSeparatedTracksGrid = document.getElementById('dialogueSeparatedTracksGrid');
  const btnDownloadAllSeparatedTracks = document.getElementById('btnDownloadAllSeparatedTracks');

  const SPEAKER_THEMES = {
    A: { border: 'border-purple-500/40', text: 'text-purple-400', badge: 'bg-purple-500/20 text-purple-300 border-purple-500/30', defaultVoice: 'free-vi-ngoc-huyen', defaultLabel: 'Nhân vật Nữ (A)', defaultLabelEn: 'Female Role (A)' },
    B: { border: 'border-cyan-500/40', text: 'text-cyan-400', badge: 'bg-cyan-500/20 text-cyan-300 border-cyan-500/30', defaultVoice: 'free-vi-minh-quan', defaultLabel: 'Nhân vật Nam (B)', defaultLabelEn: 'Male Role (B)' },
    C: { border: 'border-amber-500/40', text: 'text-amber-400', badge: 'bg-amber-500/20 text-amber-300 border-amber-500/30', defaultVoice: 'free-vi-thien-tam', defaultLabel: 'Người dẫn chuyện (C)', defaultLabelEn: 'Narrator (C)' },
    D: { border: 'border-emerald-500/40', text: 'text-emerald-400', badge: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30', defaultVoice: 'free-vi-truc-ly', defaultLabel: 'Nhân vật D', defaultLabelEn: 'Character D' },
    E: { border: 'border-rose-500/40', text: 'text-rose-400', badge: 'bg-rose-500/20 text-rose-300 border-rose-500/30', defaultVoice: 'free-vi-pham-tuyen', defaultLabel: 'Nhân vật E', defaultLabelEn: 'Character E' },
    F: { border: 'border-indigo-500/40', text: 'text-indigo-400', badge: 'bg-indigo-500/20 text-indigo-300 border-indigo-500/30', defaultVoice: 'free-vi-my-duyen', defaultLabel: 'Nhân vật F', defaultLabelEn: 'Character F' },
    G: { border: 'border-orange-500/40', text: 'text-orange-400', badge: 'bg-orange-500/20 text-orange-300 border-orange-500/30', defaultVoice: 'free-vi-hai-dang', defaultLabel: 'Nhân vật G', defaultLabelEn: 'Character G' },
    H: { border: 'border-teal-500/40', text: 'text-teal-400', badge: 'bg-teal-500/20 text-teal-300 border-teal-500/30', defaultVoice: 'free-vi-ngoc-ngan', defaultLabel: 'Nhân vật H', defaultLabelEn: 'Character H' }
  };

  function getDefaultSpeakerRoleLabel(key) {
    const th = SPEAKER_THEMES[key] || SPEAKER_THEMES.D;
    return isViStudio() ? th.defaultLabel : th.defaultLabelEn;
  }

  function syncDefaultSpeakerCardTitlesForLang() {
    activeSpeakerKeys.forEach(k => {
      const th = SPEAKER_THEMES[k];
      if (!th) return;
      const cur = speakerNamesMap[k] || '';
      if (!cur || cur === th.defaultLabel || cur === th.defaultLabelEn) {
        updateSpeakerCardTitle(k, getDefaultSpeakerRoleLabel(k));
      }
    });
  }

  const EXTRA_KEYS = ['D', 'E', 'F', 'G', 'H'];
  let activeSpeakerKeys = ['A', 'B', 'C'];
  let speakerNamesMap = {
    A: 'Nhân vật Nữ (A)',
    B: 'Nhân vật Nam (B)',
    C: 'Người dẫn chuyện (C)'
  };
  let parsedDialogueSegments = [];
  let lastParsedRawScript = '';
  let separatedDownloadItems = [];
  let dialogueCancelRequested = false;

  function getTheme(key) {
    return SPEAKER_THEMES[key] || SPEAKER_THEMES.D;
  }

  function getSpeakerSelectEl(key) {
    if (key === 'A') return document.getElementById('dialogueVoiceA');
    if (key === 'B') return document.getElementById('dialogueVoiceB');
    if (key === 'C') return document.getElementById('dialogueVoiceC');
    return document.getElementById(`dialogueVoice_${key}`);
  }

  function getSpeakerVoiceId(key) {
    const sel = getSpeakerSelectEl(key);
    return sel ? sel.value : (getTheme(key).defaultVoice || 'free-vi-ngoc-huyen');
  }

  function getSpeakerVoiceDisplayName(key) {
    const sel = getSpeakerSelectEl(key);
    if (sel && sel.selectedOptions && sel.selectedOptions[0]) {
      return sel.selectedOptions[0].textContent.replace(/^✨\s*/, '').split('(')[0].trim();
    }
    return getSpeakerVoiceId(key);
  }

  function updateSpeakerCardTitle(key, customTitle) {
    speakerNamesMap[key] = customTitle;
    const card = speakerGrid ? speakerGrid.querySelector(`[data-speaker-key="${key}"]`) : null;
    if (card) {
      const titleSpan = card.querySelector('.speaker-role-title');
      if (titleSpan) titleSpan.textContent = customTitle;
    }
  }

  function ensureSpeakerCard(key, customLabel, preferredGender) {
    if (activeSpeakerKeys.includes(key)) {
      if (customLabel) updateSpeakerCardTitle(key, customLabel);
      return key;
    }
    if (!speakerGrid) return 'A';
    activeSpeakerKeys.push(key);
    const theme = getTheme(key);
    let defaultVoice = theme.defaultVoice;
    if (preferredGender === 'female') {
      const femPool = ['free-vi-truc-ly', 'free-vi-my-duyen', 'free-vi-ngoc-linh', 'free-vi-mai-anh', 'free-vi-hoaimy'];
      defaultVoice = femPool[activeSpeakerKeys.length % femPool.length];
    } else if (preferredGender === 'male') {
      const malePool = ['free-vi-pham-tuyen', 'free-vi-hai-dang', 'free-vi-thai-son', 'free-vi-adam-tiktok', 'free-vi-namminh'];
      defaultVoice = malePool[activeSpeakerKeys.length % malePool.length];
    }

    const roleLabel = customLabel || getDefaultSpeakerRoleLabel(key);
    speakerNamesMap[key] = roleLabel;

    const card = document.createElement('div');
    card.className = `dialogue-speaker-card p-3.5 rounded-xl bg-slate-900/80 border ${theme.border} flex flex-col gap-2`;
    card.setAttribute('data-speaker-key', key);
    card.innerHTML = `
      <div class="flex items-center justify-between text-xs">
        <span class="font-bold ${theme.text} flex items-center gap-1.5"><i class="fa-solid fa-user"></i> <span class="speaker-role-title">${escapeHtmlSafe(roleLabel)}</span></span>
        <span class="text-[10px] ${theme.badge} px-1.5 py-0.5 rounded font-mono">${key}:</span>
      </div>
      <select id="dialogueVoice_${key}" class="dialogue-voice-select w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200">
        ${buildVoiceOptionsHtml(defaultVoice)}
      </select>
    `;
    speakerGrid.appendChild(card);
    return key;
  }

  if (btnAddDialogueSpeaker) {
    btnAddDialogueSpeaker.addEventListener('click', () => {
      const nextKey = EXTRA_KEYS.find(k => !activeSpeakerKeys.includes(k));
      if (!nextKey) {
        if (typeof showToast === 'function') showToast('Đã đạt tối đa 8 nhân vật trong 1 cảnh!', 'warning');
        return;
      }
      ensureSpeakerCard(nextKey);
      renderParsedSegmentsPanel();
      if (typeof showToast === 'function') showToast(`Đã thêm Nhân vật ${nextKey}!`, 'success');
    });
  }

  // Heuristic gender detector from Vietnamese names / pronouns / attribution context
  function guessGenderFromVietnameseContext(contextStr) {
    const s = (contextStr || '').toLowerCase();
    const femaleHints = /\b(cô|nàng|chị|em|bà|mẹ|má|dì|cô ấy|nàng ấy|thiếp|nữ|huyền|lan|mai|linh|vy|my|nhung|hương|thảo|trang|ngọc|hà|yến|tuyết|trúc|duyên)\b/i;
    const maleHints = /\b(anh|chàng|hắn|ông|chú|bác|cha|bố|thầy|cậu|gã|y|trẫm|nam|quân|minh|hùng|tuyên|đức|sơn|khôi|dũng|long|phong|viêm|thành|khang)\b/i;
    if (femaleHints.test(s) && !maleHints.test(s)) return 'female';
    if (maleHints.test(s) && !femaleHints.test(s)) return 'male';
    // Check last subject right before speaking verb
    const lastClause = s.slice(-45);
    if (femaleHints.test(lastClause)) return 'female';
    if (maleHints.test(lastClause)) return 'male';
    return null;
  }

  /**
   * Smart Story & Script Parser:
   * Handles:
   * 1. Explicit speaker lines (`A: ...`, `B: ...`, `C: ...`, or `Quân: ...`, `Huyền: ...`, `Dẫn chuyện: ...`)
   * 2. Novel dash dialogue lines (`- ...`, `– ...`, `— ...`)
   * 3. Prose paragraphs with inline quoted dialogues (`“...”` or `"..."`), splitting Narrator vs Spoken Quotes!
   */
  function parseLongStoryIntoSegments(rawScript) {
    const text = (rawScript || '').replace(/\r\n/g, '\n').trim();
    if (!text) return [];

    const namedRoleMap = {}; // normalizedName -> speakerKey
    let usedMaleB = false;
    let usedFemaleA = false;
    let lastDialogueSpeaker = 'B';

    function resolveNamedCharacter(rawName) {
      const clean = rawName.replace(/^[\[\(]|[\]\)]$/g, '').trim();
      const upper = clean.toUpperCase();
      if (['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H'].includes(upper)) {
        if (!activeSpeakerKeys.includes(upper)) ensureSpeakerCard(upper);
        return upper;
      }
      const norm = clean.toLowerCase();
      if (/^(dẫn chuyện|người dẫn|narrator|thuyết minh|bối cảnh)$/i.test(norm)) {
        return 'C';
      }
      if (namedRoleMap[norm]) return namedRoleMap[norm];

      const gender = guessGenderFromVietnameseContext(clean);
      if (gender === 'female' && !usedFemaleA) {
        usedFemaleA = true;
        namedRoleMap[norm] = 'A';
        updateSpeakerCardTitle('A', `${clean} (A)`);
        return 'A';
      }
      if (gender === 'male' && !usedMaleB) {
        usedMaleB = true;
        namedRoleMap[norm] = 'B';
        updateSpeakerCardTitle('B', `${clean} (B)`);
        return 'B';
      }
      if (!usedFemaleA && gender !== 'male') {
        usedFemaleA = true;
        namedRoleMap[norm] = 'A';
        updateSpeakerCardTitle('A', `${clean} (A)`);
        return 'A';
      }
      if (!usedMaleB) {
        usedMaleB = true;
        namedRoleMap[norm] = 'B';
        updateSpeakerCardTitle('B', `${clean} (B)`);
        return 'B';
      }
      const extraKey = EXTRA_KEYS.find(k => !Object.values(namedRoleMap).includes(k)) || 'D';
      ensureSpeakerCard(extraKey, `${clean} (${extraKey})`, gender);
      namedRoleMap[norm] = extraKey;
      return extraKey;
    }

    function pickAlternatingDialogueSpeaker(contextBefore, contextAfter) {
      const g = guessGenderFromVietnameseContext(`${contextBefore || ''} ${contextAfter || ''}`);
      if (g === 'female') {
        lastDialogueSpeaker = 'A';
        return 'A';
      }
      if (g === 'male') {
        lastDialogueSpeaker = 'B';
        return 'B';
      }
      lastDialogueSpeaker = lastDialogueSpeaker === 'A' ? 'B' : 'A';
      return lastDialogueSpeaker;
    }

    const segments = [];
    const lines = text.split('\n');

    for (const rawLine of lines) {
      const line = rawLine.trim();
      if (!line) continue;

      // Case 1: Explicit `SpeakerName: content` (SpeakerName <= 22 chars, no quotes/dots inside name)
      const labelMatch = line.match(/^([A-Za-zÀ-ỹ0-9_\s\[\]\(\)]{1,22}):\s+(.+)$/);
      const candidateLabel = labelMatch ? labelMatch[1].trim() : '';
      const isNarrativeVerbColon = /\b(nói|hỏi|đáp|kêu|thở dài|thầm thì|gọi|bảo|cười|nghĩ|nhìn|rằng|như sau|là)$/i.test(candidateLabel);

      if (labelMatch && !isNarrativeVerbColon && candidateLabel.split(/\s+/).length <= 4) {
        const spk = resolveNamedCharacter(candidateLabel);
        const content = labelMatch[2].trim();
        if (content) {
          segments.push({ id: segments.length + 1, speaker: spk, text: content, audioBuffer: null, blobUrl: null, durationSec: 0 });
          if (spk !== 'C') lastDialogueSpeaker = spk;
        }
        continue;
      }

      // Case 2: Novel dash dialogue (`- Lời thoại...` or `– Lời thoại...`)
      const dashMatch = line.match(/^[—–\-]\s*(.+)$/);
      if (dashMatch) {
        const body = dashMatch[1].trim();
        // Check if trailing narrator attribution exists, e.g. `Chào cậu! - Huyền mỉm cười nói.`
        const trailMatch = body.match(/^(.+?[.?!…])\s+[—–\-]\s+([^—–\-]{3,60})$/);
        if (trailMatch) {
          const spoken = trailMatch[1].trim();
          const attr = trailMatch[2].trim();
          const spk = pickAlternatingDialogueSpeaker('', attr);
          segments.push({ id: segments.length + 1, speaker: spk, text: spoken, audioBuffer: null, blobUrl: null, durationSec: 0 });
          segments.push({ id: segments.length + 1, speaker: 'C', text: attr, audioBuffer: null, blobUrl: null, durationSec: 0 });
        } else {
          const prevNarr = segments.length > 0 && segments[segments.length - 1].speaker === 'C' ? segments[segments.length - 1].text : '';
          const spk = pickAlternatingDialogueSpeaker(prevNarr, '');
          segments.push({ id: segments.length + 1, speaker: spk, text: body, audioBuffer: null, blobUrl: null, durationSec: 0 });
        }
        continue;
      }

      // Case 3: Prose paragraph containing inline quoted speech `“...”` or `"..."`
      const quoteRegex = /[“"]([^”"]{2,})[”"]/g;
      if (quoteRegex.test(line)) {
        quoteRegex.lastIndex = 0;
        let lastIdx = 0;
        let m;
        while ((m = quoteRegex.exec(line)) !== null) {
          const narrBefore = line.slice(lastIdx, m.index).trim();
          const quotedSpeech = m[1].trim();
          const narrAfterPeek = line.slice(m.index + m[0].length, m.index + m[0].length + 50).trim();

          if (narrBefore) {
            segments.push({ id: segments.length + 1, speaker: 'C', text: narrBefore, audioBuffer: null, blobUrl: null, durationSec: 0 });
          }
          if (quotedSpeech) {
            const spk = pickAlternatingDialogueSpeaker(narrBefore, narrAfterPeek);
            segments.push({ id: segments.length + 1, speaker: spk, text: quotedSpeech, audioBuffer: null, blobUrl: null, durationSec: 0 });
          }
          lastIdx = m.index + m[0].length;
        }
        const tailNarr = line.slice(lastIdx).replace(/^[,.;:\s]+/, '').trim();
        if (tailNarr) {
          segments.push({ id: segments.length + 1, speaker: 'C', text: tailNarr, audioBuffer: null, blobUrl: null, durationSec: 0 });
        }
        continue;
      }

      // Case 4: Pure narration paragraph -> Narrator C
      segments.push({ id: segments.length + 1, speaker: 'C', text: line, audioBuffer: null, blobUrl: null, durationSec: 0 });
    }

    return segments;
  }

  function renderParsedSegmentsPanel() {
    if (!dialogueParsedPanel || !dialogueSegmentsList) return;
    if (!parsedDialogueSegments || parsedDialogueSegments.length === 0) {
      dialogueParsedPanel.classList.add('hidden');
      return;
    }

    const isVi = isViStudio();
    dialogueParsedPanel.classList.remove('hidden');
    if (dialogueParsedCountBadge) {
      dialogueParsedCountBadge.textContent = isVi
        ? `${parsedDialogueSegments.length} đoạn thoại`
        : `${parsedDialogueSegments.length} segments`;
    }

    // Role counts summary
    if (dialogueRoleSummaryBadges) {
      const counts = {};
      parsedDialogueSegments.forEach(s => { counts[s.speaker] = (counts[s.speaker] || 0) + 1; });
      dialogueRoleSummaryBadges.innerHTML = Object.keys(counts).map(k => {
        const th = getTheme(k);
        const label = speakerNamesMap[k] || k;
        return `<span class="px-2 py-0.5 rounded-full border text-[10px] font-semibold ${th.badge}">${escapeHtmlSafe(label)}: ${counts[k]} ${isVi ? 'câu' : 'lines'}</span>`;
      }).join('');
    }

    dialogueSegmentsList.innerHTML = '';
    parsedDialogueSegments.forEach((seg, idx) => {
      const th = getTheme(seg.speaker);
      const row = document.createElement('div');
      row.className = `p-2.5 rounded-xl bg-slate-900/90 border ${th.border} flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs`;

      const speakerOpts = activeSpeakerKeys.map(k => {
        const sel = k === seg.speaker ? 'selected' : '';
        return `<option value="${k}" ${sel}>${escapeHtmlSafe(speakerNamesMap[k] || (isVi ? `Vai ${k}` : `Role ${k}`))}</option>`;
      }).join('');

      row.innerHTML = `
        <div class="flex items-start gap-2.5 flex-1 min-w-0">
          <span class="text-[10px] font-mono text-slate-500 mt-1 shrink-0">#${idx + 1}</span>
          <select class="seg-speaker-override bg-slate-950 border border-slate-700 rounded-lg px-2 py-1 text-[11px] font-semibold ${th.text} shrink-0 cursor-pointer" data-seg-idx="${idx}">
            ${speakerOpts}
          </select>
          <p class="text-slate-200 leading-relaxed break-words flex-1">${escapeHtmlSafe(seg.text)}</p>
        </div>
        <div class="flex items-center gap-1.5 shrink-0 self-end sm:self-center">
          ${seg.blobUrl ? `
            <button type="button" class="btn-play-single-seg px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-amber-300 text-[11px] cursor-pointer" data-seg-idx="${idx}" title="${isVi ? 'Nghe riêng câu này' : 'Play line'}">
              <i class="fa-solid fa-play"></i> ${seg.durationSec ? `${seg.durationSec.toFixed(1)}s` : ''}
            </button>
            <a href="${seg.blobUrl}" download="line-${idx + 1}-${seg.speaker}.wav" class="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-cyan-300 text-[11px]" title="${isVi ? 'Tải lẻ câu này' : 'Download line'}">
              <i class="fa-solid fa-download"></i>
            </a>
          ` : `<span class="text-[10px] text-slate-500 italic">${isVi ? 'Chưa tạo audio' : 'Pending'}</span>`}
        </div>
      `;

      const selectEl = row.querySelector('.seg-speaker-override');
      if (selectEl) {
        selectEl.addEventListener('change', (e) => {
          parsedDialogueSegments[idx].speaker = e.target.value;
          parsedDialogueSegments[idx].audioBuffer = null;
          parsedDialogueSegments[idx].blobUrl = null;
          renderParsedSegmentsPanel();
        });
      }

      const playBtn = row.querySelector('.btn-play-single-seg');
      if (playBtn) {
        playBtn.addEventListener('click', () => {
          if (seg.blobUrl && dialogueAudioPlayer) {
            dialogueOutputContainer?.classList.remove('hidden');
            dialogueAudioPlayer.src = seg.blobUrl;
            dialogueAudioPlayer.play().catch(() => {});
          }
        });
      }

      dialogueSegmentsList.appendChild(row);
    });
  }

  function runAutoParseAndPreview(showNotification = true) {
    const raw = dialogueScriptInput ? dialogueScriptInput.value.trim() : '';
    if (!raw) {
      if (showNotification && typeof showToast === 'function') {
        showToast('Vui lòng dán văn bản truyện hoặc kịch bản vào ô trước!', 'warning');
      }
      return [];
    }
    parsedDialogueSegments = parseLongStoryIntoSegments(raw);
    lastParsedRawScript = raw;
    renderParsedSegmentsPanel();
    if (showNotification && typeof showToast === 'function') {
      const rolesUsed = new Set(parsedDialogueSegments.map(s => s.speaker)).size;
      showToast(`Đã tự động bóc tách thành ${parsedDialogueSegments.length} đoạn thoại cho ${rolesUsed} giọng đọc!`, 'success');
    }
    return parsedDialogueSegments;
  }

  if (btnAutoParseStory) {
    btnAutoParseStory.addEventListener('click', () => runAutoParseAndPreview(true));
  }

  if (btnLoadDialogueSample && dialogueScriptInput) {
    btnLoadDialogueSample.addEventListener('click', () => {
      if (isViStudio()) {
        updateSpeakerCardTitle('A', 'Huyền (A)');
        updateSpeakerCardTitle('B', 'Quân (B)');
        updateSpeakerCardTitle('C', 'Người dẫn chuyện (C)');
        dialogueScriptInput.value =
`C: Buổi sáng cuối thu tại quán cà phê phố cổ... hai người bạn cũ gặp lại nhau sau mười năm xa cách.
A: Chào Quân... Đã lâu quá rồi chúng ta mới có dịp ngồi lại cùng nhau thế này!
B: [cười] Chào Huyền! Trông cậu vẫn rạng rỡ như ngày xưa vậy... thời gian dường như bỏ quên cậu rồi.
A: Cậu khéo miệng quá! Nghe nói gần đây cậu đang phát triển một dự án phòng thu AI trên Voxly rất thành công?
B: Đúng vậy Huyền... công cụ mới giúp bóc tách từng nhân vật và xuất file riêng cho từng giọng cực kỳ tiện lợi.
C: Cuộc trò chuyện giữa hai người bạn diễn ra trong tiếng nhạc nhẹ nhàng... và nắng ấm đầu đông.`;
      } else {
        updateSpeakerCardTitle('A', 'Ava (A)');
        updateSpeakerCardTitle('B', 'Andrew (B)');
        updateSpeakerCardTitle('C', 'Narrator (C)');
        dialogueScriptInput.value =
`C: On a crisp autumn morning at a quiet downtown cafe... two old friends reunited after ten years apart.
A: Hey Andrew... It has been so long since we had a chance to sit down like this!
B: Great to see you, Ava! You haven't changed a bit... how has your new audiobook channel been going?
A: Better than ever! With Voxly Studio, we split every character into synced CapCut tracks in seconds.
C: Their conversation continued warmly as the morning sunlight streamed through the glass window.`;
      }
      runAutoParseAndPreview(true);
    });
  }

  if (btnLoadLongStorySample && dialogueScriptInput) {
    btnLoadLongStorySample.addEventListener('click', () => {
      syncDefaultSpeakerCardTitlesForLang();
      if (isViStudio()) {
        dialogueScriptInput.value =
`Đêm đã về khuya... từng hạt mưa rơi tí tách bên hiên nhà vắng lặng. Quân đứng lặng lẽ bên khung cửa sổ, ánh mắt trầm tư nhìn về phía con ngõ nhỏ rồi khẽ cất tiếng hỏi: “Huyền này... suốt ngần ấy năm qua, có bao giờ em hối tiếc về quyết định ngày hôm ấy không?”

Huyền khẽ đặt tách trà nóng xuống mặt bàn gỗ... cô im lặng một thoáng rồi mỉm cười nhẹ nhàng đáp: “[thở dài] Chuyện cũ cũng như cơn mưa ngoài kia vậy anh ạ... lúc mới đổ xuống thì xối xả lắm, nhưng rồi trời cũng sẽ tạnh thôi.”

Quân quay lại nhìn cô, giọng anh trầm ấm hơn: “[cười] Ừ nhỉ... nghe em nói vậy tự dưng lòng anh cũng thấy nhẹ nhõm hơn rất nhiều rồi.”

Ngoài hiên, gió đêm khẽ thổi qua tán bàng già... mang theo hương hoa sữa dịu ngọt của những ngày cuối thu Hà Nội.`;
      } else {
        dialogueScriptInput.value =
`Late into the night... raindrops tapped softly against the quiet porch. Andrew stood by the window, gazing down the misty lane before asking gently: "Ava... after all these years, did you ever regret the choice we made that day?"

Ava set her warm teacup onto the wooden table and smiled softly: "The past is just like the rain outside... fierce when it starts, yet the sky always clears in the end."

Andrew turned toward her, his voice noticeably lighter: "You're right... hearing you say that makes everything feel much clearer now."`;
      }
      runAutoParseAndPreview(true);
    });
  }

  // Helper: Build WAV Blob from raw PCM chunks (int16 mono) at detected sampleRate
  function createWavBlobFromPcmChunks(pcmByteArrays, sampleRate = 48000) {
    let totalBytes = 0;
    pcmByteArrays.forEach(arr => { totalBytes += arr.byteLength; });
    const header = new ArrayBuffer(44);
    const view = new DataView(header);
    const writeStr = (off, s) => { for (let i = 0; i < s.length; i++) view.setUint8(off + i, s.charCodeAt(i)); };
    writeStr(0, 'RIFF');
    view.setUint32(4, totalBytes + 36, true);
    writeStr(8, 'WAVE');
    writeStr(12, 'fmt ');
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true);
    view.setUint16(22, 1, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * 2, true);
    view.setUint16(32, 2, true);
    view.setUint16(34, 16, true);
    writeStr(36, 'data');
    view.setUint32(40, totalBytes, true);
    return new Blob([header, ...pcmByteArrays], { type: 'audio/wav' });
  }

  async function convertWavBlobToMp3(wavBlob, bitrate = '64k') {
    try {
      const res = await fetch(`/api/audio/convert-to-mp3?bitrate=${bitrate}`, {
        method: 'POST',
        headers: { 'Content-Type': 'audio/wav' },
        body: wavBlob
      });
      if (res.ok) {
        return { blob: await res.blob(), ext: 'mp3' };
      }
    } catch (e) {
      console.warn('MP3 convert fallback to WAV:', e);
    }
    return { blob: wavBlob, ext: 'wav' };
  }

  if (btnDownloadAllSeparatedTracks) {
    btnDownloadAllSeparatedTracks.addEventListener('click', async () => {
      if (!separatedDownloadItems || separatedDownloadItems.length === 0) return;
      for (let i = 0; i < separatedDownloadItems.length; i++) {
        const item = separatedDownloadItems[i];
        const a = document.createElement('a');
        a.href = item.url;
        a.download = item.filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        await new Promise(r => setTimeout(r, 350));
      }
      if (typeof showToast === 'function') {
        showToast(`Đã tải xuống trọn bộ ${separatedDownloadItems.length} file giọng tách riêng!`, 'success');
      }
    });
  }

  if (btnStopDialogue) {
    btnStopDialogue.addEventListener('click', () => {
      dialogueCancelRequested = true;
      btnStopDialogue.disabled = true;
      if (dialogueStatus) {
        dialogueStatus.innerHTML = '<span class="text-amber-400 font-semibold"><i class="fa-solid fa-hand mr-1"></i> Đang dừng tiến trình...</span>';
      }
    });
  }

  if (btnGenerateDialogue) {
    btnGenerateDialogue.addEventListener('click', async () => {
      const script = dialogueScriptInput ? dialogueScriptInput.value.trim() : '';
      if (!script) {
        if (typeof showToast === 'function') showToast('Vui lòng dán văn bản hoặc kịch bản hội thoại!', 'warning');
        return;
      }

      dialogueCancelRequested = false;
      // Re-parse automatically if script changed since last manual parse, while preserving manual overrides if script unchanged
      if (!parsedDialogueSegments || parsedDialogueSegments.length === 0 || script !== lastParsedRawScript) {
        parsedDialogueSegments = parseLongStoryIntoSegments(script);
        lastParsedRawScript = script;
      }

      if (parsedDialogueSegments.length === 0) {
        if (typeof showToast === 'function') showToast('Không tìm thấy nội dung thoại hợp lệ.', 'warning');
        return;
      }

      renderParsedSegmentsPanel();

      // Check character quota for the entire dialogue script beforehand
      const totalScriptChars = parsedDialogueSegments.reduce((acc, s) => acc + (s.text ? s.text.length : 0), 0);
      if (window.VoiceVietQuota && !window.VoiceVietQuota.checkCanGenerate(totalScriptChars)) {
        return;
      }

      // Check if any speaker in this scene uses a private owner-locked voice
      const usedPrivVoice = parsedDialogueSegments
        .map(s => getSpeakerVoiceId(s.speaker))
        .find(vId => vId && vId.startsWith('private-'));
      if (usedPrivVoice && typeof window.ensurePrivateVoiceAuthorized === 'function') {
        const authOk = await window.ensurePrivateVoiceAuthorized(usedPrivVoice);
        if (!authOk) return;
      }

      btnGenerateDialogue.disabled = true;
      if (btnStopDialogue) btnStopDialogue.disabled = false;
      const rateEl = document.getElementById('rateRange');
      const pauseEl = document.getElementById('pauseDurationRange');
      const rate = rateEl ? (parseFloat(rateEl.value) || 1.0) : 1.0;
      const pauseSec = pauseEl ? (parseFloat(pauseEl.value) || 0.40) : 0.40;
      const dialogueStartMs = performance.now();
      let totalDialogueAudioSec = 0;

      try {
        for (let i = 0; i < parsedDialogueSegments.length; i++) {
          if (dialogueCancelRequested) throw new Error('Đã dừng theo yêu cầu người dùng.');

          const seg = parsedDialogueSegments[i];
          const voiceId = getSpeakerVoiceId(seg.speaker);
          const roleName = speakerNamesMap[seg.speaker] || `Vai ${seg.speaker}`;
          const isLocal = voiceId.startsWith('free-') || voiceId.startsWith('private-');

          if (dialogueStatus) {
            dialogueStatus.innerHTML = `<span class="text-cyan-400 font-semibold"><i class="fa-solid fa-spinner fa-spin mr-1"></i> [${i + 1}/${parsedDialogueSegments.length}] Đang thu âm <b>${escapeHtmlSafe(roleName)}</b>...</span>`;
          }

          const endpoint = isLocal ? '/api/free-tts/synthesize' : '/api/cheap-tts/synthesize';
          const headers = { 'Content-Type': 'application/json' };
          const tok = typeof window.getOwnerToken === 'function' ? window.getOwnerToken() : '';
          if (tok) headers['X-Owner-Token'] = tok;

          const res = await fetch(endpoint, {
            method: 'POST',
            headers,
            body: JSON.stringify({
              text: seg.text,
              voice: voiceId,
              rate,
              pauses: { sentence: pauseSec }
            })
          });

          if (!res.ok) {
            const errData = await res.json().catch(() => ({}));
            if (res.status === 403 || errData.code === 'private_locked') {
              if (typeof window.setOwnerToken === 'function') window.setOwnerToken('');
              if (typeof window.refreshVaultStatusUI === 'function') window.refreshVaultStatusUI();
            }
            throw new Error(errData.error || `Lỗi tạo đoạn #${i + 1} (HTTP ${res.status})`);
          }

          const wavBuf = await res.arrayBuffer();
          const sr = wavBuf.byteLength >= 28 ? new DataView(wavBuf).getUint32(24, true) : 48000;
          const durSec = Math.max(0.1, (wavBuf.byteLength - 44) / (sr * 2));
          totalDialogueAudioSec += durSec;

          if (window.VoiceVietQuota && seg.text) {
            window.VoiceVietQuota.deductCharacters(seg.text.length);
          }

          if (seg.blobUrl) URL.revokeObjectURL(seg.blobUrl);
          seg.audioBuffer = wavBuf;
          seg.sampleRate = sr;
          seg.durationSec = durSec;
          seg.blobUrl = URL.createObjectURL(new Blob([wavBuf], { type: 'audio/wav' }));

          renderParsedSegmentsPanel();

          if (!isLocal && i < parsedDialogueSegments.length - 1 && !dialogueCancelRequested) {
            await new Promise(r => setTimeout(r, 1800));
          }
        }

        if (dialogueCancelRequested) throw new Error('Đã dừng theo yêu cầu người dùng.');

        if (dialogueStatus) {
          dialogueStatus.innerHTML = `<span class="text-purple-400 font-semibold"><i class="fa-solid fa-spinner fa-spin mr-1"></i> Đang ghép bản Full Mix & tách riêng từng giọng nhân vật...</span>`;
        }

        // Detect master sample rate from first segment (48000 Hz)
        const masterSr = parsedDialogueSegments[0].sampleRate || 48000;
        const turnGapSamples = Math.round(0.42 * masterSr);
        const turnGapSilence = new Uint8Array(turnGapSamples * 2);

        // 1. Build Full Mix PCM & Timeline-Synced Per-Speaker PCM simultaneously!
        const usedSpeakers = [...new Set(parsedDialogueSegments.map(s => s.speaker))];
        const fullMixParts = [];
        const timelinePartsBySpeaker = {};
        const voiceOnlyPartsBySpeaker = {};

        usedSpeakers.forEach(k => {
          timelinePartsBySpeaker[k] = [];
          voiceOnlyPartsBySpeaker[k] = [];
        });

        for (let i = 0; i < parsedDialogueSegments.length; i++) {
          const seg = parsedDialogueSegments[i];
          const pcm = new Uint8Array(seg.audioBuffer, 44);
          const segSilence = new Uint8Array(pcm.byteLength);

          fullMixParts.push(pcm);

          usedSpeakers.forEach(k => {
            if (k === seg.speaker) {
              timelinePartsBySpeaker[k].push(pcm);
              if (voiceOnlyPartsBySpeaker[k].length > 0) {
                voiceOnlyPartsBySpeaker[k].push(turnGapSilence);
              }
              voiceOnlyPartsBySpeaker[k].push(pcm);
            } else {
              timelinePartsBySpeaker[k].push(segSilence);
            }
          });

          if (i < parsedDialogueSegments.length - 1) {
            fullMixParts.push(turnGapSilence);
            usedSpeakers.forEach(k => {
              timelinePartsBySpeaker[k].push(turnGapSilence);
            });
          }
        }

        // Create Full Mix WAV + MP3
        const fullMixWavBlob = createWavBlobFromPcmChunks(fullMixParts, masterSr);
        const fullMixWavUrl = URL.createObjectURL(fullMixWavBlob);
        const fullMixMp3Obj = await convertWavBlobToMp3(fullMixWavBlob, '64k');
        const fullMixMp3Url = URL.createObjectURL(fullMixMp3Obj.blob);

        if (dialogueAudioPlayer) {
          dialogueAudioPlayer.src = fullMixMp3Url;
          dialogueAudioPlayer.play().catch(() => {});
        }
        if (btnDownloadDialogueWav) {
          btnDownloadDialogueWav.href = fullMixWavUrl;
          btnDownloadDialogueWav.download = `hoi-thoai-full-48khz-${Date.now()}.wav`;
        }
        if (btnDownloadDialogueMp3) {
          btnDownloadDialogueMp3.href = fullMixMp3Url;
          btnDownloadDialogueMp3.download = `hoi-thoai-full-${Date.now()}.${fullMixMp3Obj.ext}`;
        }

        // 2. Render Separated Per-Speaker Cards (Voice-Only MP3 + CapCut Timeline-Synced WAV)
        separatedDownloadItems = [];
        if (dialogueSeparatedTracksGrid) {
          dialogueSeparatedTracksGrid.innerHTML = '';

          for (const spkKey of usedSpeakers) {
            const th = getTheme(spkKey);
            const roleTitle = speakerNamesMap[spkKey] || `Nhân vật ${spkKey}`;
            const voiceTitle = getSpeakerVoiceDisplayName(spkKey);
            const lineCount = parsedDialogueSegments.filter(s => s.speaker === spkKey).length;
            const safeSlug = roleTitle.normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/[^a-zA-Z0-9]+/g, '_').replace(/^_|_$/g, '');

            const voiceOnlyWav = createWavBlobFromPcmChunks(voiceOnlyPartsBySpeaker[spkKey], masterSr);
            const voiceOnlyMp3 = await convertWavBlobToMp3(voiceOnlyWav, '64k');
            const voiceOnlyUrl = URL.createObjectURL(voiceOnlyMp3.blob);
            const voiceOnlyFilename = `TachRieng_${spkKey}_${safeSlug}_GiongGop.${voiceOnlyMp3.ext}`;

            const timelineSyncWav = createWavBlobFromPcmChunks(timelinePartsBySpeaker[spkKey], masterSr);
            const timelineSyncMp3 = await convertWavBlobToMp3(timelineSyncWav, '64k');
            const timelineSyncUrl = URL.createObjectURL(timelineSyncMp3.blob);
            const timelineSyncFilename = `TrackCapCut_DongBo_${spkKey}_${safeSlug}.${timelineSyncMp3.ext}`;

            separatedDownloadItems.push({ url: voiceOnlyUrl, filename: voiceOnlyFilename });

            const isVi = isViStudio();
            const trackCard = document.createElement('div');
            trackCard.className = `p-3.5 rounded-xl bg-slate-950/90 border ${th.border} flex flex-col gap-2.5 shadow-md`;
            trackCard.innerHTML = `
              <div class="flex items-center justify-between gap-2">
                <div>
                  <div class="text-xs font-bold ${th.text} flex items-center gap-1.5">
                    <i class="fa-solid fa-microphone-lines"></i> ${escapeHtmlSafe(roleTitle)}
                  </div>
                  <div class="text-[11px] text-slate-400 mt-0.5">
                    ${isVi ? 'Giọng:' : 'Voice:'} <b class="text-slate-200">${escapeHtmlSafe(voiceTitle)}</b> • ${isVi ? `Đã tách <b>${lineCount}</b> đoạn` : `<b>${lineCount}</b> segments`}
                  </div>
                </div>
                <span class="text-[10px] px-2 py-0.5 rounded-full border font-mono ${th.badge}">${isVi ? `Vai ${spkKey}` : `Role ${spkKey}`}</span>
              </div>
              <audio controls src="${voiceOnlyUrl}" class="w-full h-9 outline-none"></audio>
              <div class="flex flex-wrap items-center gap-2 pt-1">
                <a href="${voiceOnlyUrl}" download="${voiceOnlyFilename}" class="flex-1 text-center px-2.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-[11px] transition flex items-center justify-center gap-1">
                  <i class="fa-solid fa-download"></i> ${isVi ? `Tải Giọng Riêng (.${voiceOnlyMp3.ext.toUpperCase()})` : `Voice Only (.${voiceOnlyMp3.ext.toUpperCase()})`}
                </a>
                <a href="${timelineSyncUrl}" download="${timelineSyncFilename}" class="flex-1 text-center px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-cyan-300 border border-cyan-500/30 font-semibold text-[11px] transition flex items-center justify-center gap-1" title="${isVi ? 'Giữ đúng khoảng im lặng khi người khác nói để kéo vào CapCut khớp 100% timeline' : 'Preserves exact silence offsets to match CapCut timeline 100%'}">
                  <i class="fa-solid fa-film"></i> ${isVi ? 'Track Khớp CapCut' : 'CapCut Synced Stem'}
                </a>
              </div>
            `;
            dialogueSeparatedTracksGrid.appendChild(trackCard);
          }
        }

        if (dialogueOutputContainer) {
          dialogueOutputContainer.classList.remove('hidden');
          dialogueOutputContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }

        if (dialogueStatus) {
          const genElapsedStr = window.VoiceVietQuota
            ? window.VoiceVietQuota.formatGenerationSpeed(performance.now() - dialogueStartMs)
            : `${((performance.now() - dialogueStartMs) / 1000).toFixed(2)}s`;
          const durStr = window.VoiceVietQuota
            ? window.VoiceVietQuota.formatAudioDurationDetailed(totalDialogueAudioSec)
            : `${totalDialogueAudioSec.toFixed(1)}s`;
          const clockStr = window.VoiceVietQuota
            ? window.VoiceVietQuota.formatClockTimestamp(new Date())
            : new Date().toLocaleTimeString('vi-VN');
          dialogueStatus.innerHTML = `<span class="text-emerald-400 font-bold"><i class="fa-solid fa-circle-check mr-1"></i> ⚡ Tạo xong trong ${genElapsedStr} (lúc ${clockStr}) • 🎧 Thời lượng: ${durStr} • Đã trừ ${totalScriptChars.toLocaleString('vi-VN')} ký tự (${usedSpeakers.length} vai)!</span>`;
        }
      } catch (err) {
        console.error('Dialogue studio error:', err);
        if (dialogueStatus) {
          dialogueStatus.innerHTML = `<span class="text-rose-400 font-medium"><i class="fa-solid fa-triangle-exclamation mr-1"></i> ${escapeHtmlSafe(err.message)}</span>`;
        }
      } finally {
        btnGenerateDialogue.disabled = false;
        if (btnStopDialogue) btnStopDialogue.disabled = true;
      }
    });
  }

  syncDefaultSpeakerCardTitlesForLang();
  console.log('Voxly Studio Pro v9.0 initialized.');
})();

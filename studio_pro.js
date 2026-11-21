/**
 * VoiceViet Studio Pro Extensions
 * Inspired by TKvisuals & Top Global AI SaaS Platforms
 * Handles Navigation, Multi-Speaker Dialogue, VietQR Billing & Voice Audition
 */

(function () {
  'use strict';

  // 1. Navigation View Switcher
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

    // Special behavior when navigating to Batch Word: make sure card is shown
    if (targetViewId === 'viewBatchWord') {
      const batchWordCard = document.getElementById('batchWordCard');
      if (batchWordCard) batchWordCard.classList.remove('hidden');
    }
  }

  navTabs.forEach(tab => {
    tab.addEventListener('click', () => {
      const targetView = tab.getAttribute('data-view');
      if (targetView) switchView(targetView);
    });
  });

  if (btnHeaderPricing) {
    btnHeaderPricing.addEventListener('click', () => switchView('viewPricing'));
  }
  if (btnSidebarUpgrade) {
    btnSidebarUpgrade.addEventListener('click', () => switchView('viewPricing'));
  }

  // 2. VietQR Payment Modal Simulation
  const vietqrModal = document.getElementById('vietqrModal');
  const btnCloseVietqrModal = document.getElementById('btnCloseVietqrModal');
  const vietqrImage = document.getElementById('vietqrImage');
  const vietqrPlanName = document.getElementById('vietqrPlanName');
  const vietqrAmount = document.getElementById('vietqrAmount');
  const vietqrMemo = document.getElementById('vietqrMemo');
  const buyPlanBtns = document.querySelectorAll('.btn-buy-plan');

  function openVietqrModal(planName, amount) {
    if (!vietqrModal) return;
    const memo = `VOICEVIET ${Math.floor(1000 + Math.random() * 9000)}`;
    if (vietqrPlanName) vietqrPlanName.textContent = planName;
    if (vietqrAmount) vietqrAmount.textContent = `${parseInt(amount).toLocaleString('vi-VN')} VNĐ`;
    if (vietqrMemo) vietqrMemo.textContent = memo;

    // Generate real VietQR image
    if (vietqrImage) {
      const qrUrl = `https://img.vietqr.io/image/MB-0359888888-compact2.png?amount=${amount}&addInfo=${encodeURIComponent(memo)}&accountName=VOICEVIET%20PRO`;
      vietqrImage.src = qrUrl;
    }

    vietqrModal.classList.remove('hidden');
  }

  function closeVietqrModal() {
    if (vietqrModal) vietqrModal.classList.add('hidden');
  }

  buyPlanBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const plan = btn.getAttribute('data-plan') || 'VIP Tháng';
      const amount = btn.getAttribute('data-amount') || '25000';
      openVietqrModal(plan, amount);
    });
  });

  if (btnCloseVietqrModal) {
    btnCloseVietqrModal.addEventListener('click', closeVietqrModal);
  }
  if (vietqrModal) {
    vietqrModal.addEventListener('click', (e) => {
      if (e.target === vietqrModal) closeVietqrModal();
    });
  }

  // 3 & 4. Dynamic Voice Library Rendering & Search (24 Pro Voices + 4 Standard)
  const voiceSelect = document.getElementById('voiceSelect');
  const voiceCatalogGrid = document.getElementById('voiceCatalogGrid');
  const voiceSearchInput = document.getElementById('voiceSearchInput');

  async function loadAndRenderVoiceCatalog() {
    if (!voiceCatalogGrid) return;
    try {
      const res = await fetch('/api/cheap-tts/voices');
      const data = await res.json();
      if (!data.success || !data.voices) return;

      const viVoices = data.voices.filter(v => v.language === 'vi' || v.id.startsWith('vi') || v.id.startsWith('free-'));
      if (viVoices.length === 0) return;

      voiceCatalogGrid.innerHTML = '';

      viVoices.forEach(v => {
        const isFree = v.id.startsWith('free-');
        const isPro = v.id.startsWith('vi-pro-');
        const initials = v.name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase();
        let badgeColor = 'bg-amber-500/20 text-amber-300 border-amber-500/30';
        let avatarBg = 'bg-slate-800 text-amber-400 border border-slate-700';
        let cardBorder = 'border-slate-800 hover:border-amber-500/50';
        let badgeText = 'Tiêu Chuẩn';
        let btnBg = 'bg-slate-800 hover:bg-slate-700 text-slate-200';

        if (isFree) {
          badgeColor = 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30';
          avatarBg = 'bg-gradient-to-tr from-emerald-600 to-teal-600 text-white';
          cardBorder = 'border-emerald-500/30 hover:border-emerald-400';
          badgeText = v.badge || 'MIỄN PHÍ';
          btnBg = 'bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white';
        } else if (isPro) {
          badgeColor = 'bg-purple-500/20 text-purple-300 border-purple-500/30';
          avatarBg = 'bg-gradient-to-tr from-purple-600 to-indigo-600 text-white';
          cardBorder = 'border-purple-500/30 hover:border-purple-500';
          badgeText = 'PRO 48kHz';
          btnBg = 'bg-purple-600 hover:bg-purple-500 text-white';
        }

        const card = document.createElement('div');
        card.className = `p-4 rounded-xl bg-slate-900/80 border ${cardBorder} transition-all flex flex-col justify-between gap-3 shadow-lg`;
        card.innerHTML = `
          <div class="flex items-start gap-3">
            <div class="w-10 h-10 rounded-full ${avatarBg} flex items-center justify-center font-bold text-xs shrink-0 shadow-md">
              ${initials}
            </div>
            <div class="flex-1 min-w-0">
              <div class="flex items-center justify-between gap-1">
                <h4 class="text-xs font-bold text-white truncate">${v.name}</h4>
                <span class="text-[9px] ${badgeColor} border px-1.5 py-0.2 rounded font-mono shrink-0">${badgeText}</span>
              </div>
              <p class="text-[11px] text-cyan-300 font-medium mt-0.5 truncate">${v.useCase || v.id}</p>
              <p class="text-[10px] text-slate-400 mt-0.5">Mã: <code class="text-slate-300">${v.id}</code></p>
            </div>
          </div>
          <div class="flex items-center gap-2">
            <button class="preview-voice-quick-btn px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-amber-300 border border-slate-700 rounded-lg text-xs font-semibold transition cursor-pointer shrink-0" data-voice-id="${v.id}" data-voice-name="${v.name}" title="Nghe thử mẫu giọng">
              <i class="fa-solid fa-volume-high mr-1"></i>Nghe thử
            </button>
            <button class="select-voice-quick-btn flex-1 py-1.5 ${btnBg} rounded-lg text-xs font-semibold transition cursor-pointer" data-voice-id="${v.id}" data-voice-name="${v.name}">
              Chọn Giọng Này
            </button>
          </div>
        `;
        voiceCatalogGrid.appendChild(card);
      });

      // Bind preview buttons
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

      // Bind quick select buttons
      voiceCatalogGrid.querySelectorAll('.select-voice-quick-btn').forEach(btn => {
        btn.addEventListener('click', () => {
          const vId = btn.getAttribute('data-voice-id');
          const vName = btn.getAttribute('data-voice-name');
          if (voiceSelect && vId) {
            if (typeof window.switchEngine === 'function') {
              window.switchEngine(vId.startsWith('free-') ? 'free' : 'cheaptts');
            }
            voiceSelect.value = vId;
            voiceSelect.dispatchEvent(new Event('change'));
            switchView('viewStudio');
            if (typeof showToast === 'function') {
              showToast(`Đã chọn: ${vName} (${vId})`, 'success');
            }
          }
        });
      });
    } catch (e) {
      console.warn('Cannot render dynamic voice catalog:', e);
    }
  }

  loadAndRenderVoiceCatalog();

  // Voice Catalog Search Filter
  if (voiceSearchInput && voiceCatalogGrid) {
    voiceSearchInput.addEventListener('input', (e) => {
      const query = e.target.value.toLowerCase().trim();
      const cards = voiceCatalogGrid.querySelectorAll('.p-4');
      cards.forEach(card => {
        const text = card.textContent.toLowerCase();
        if (text.includes(query)) {
          card.style.display = 'flex';
        } else {
          card.style.display = 'none';
        }
      });
    });
  }

  // 5. Multi-Speaker Dialogue Feature with Rate-Limit Shield
  const btnLoadDialogueSample = document.getElementById('btnLoadDialogueSample');
  const dialogueScriptInput = document.getElementById('dialogueScriptInput');
  const btnGenerateDialogue = document.getElementById('btnGenerateDialogue');
  const btnStopDialogue = document.getElementById('btnStopDialogue');
  const dialogueStatus = document.getElementById('dialogueStatus');
  const dialogueOutputContainer = document.getElementById('dialogueOutputContainer');
  const dialogueAudioPlayer = document.getElementById('dialogueAudioPlayer');
  const btnDownloadDialogueMp3 = document.getElementById('btnDownloadDialogueMp3');
  const dialogueVoiceA = document.getElementById('dialogueVoiceA');
  const dialogueVoiceB = document.getElementById('dialogueVoiceB');
  const dialogueVoiceC = document.getElementById('dialogueVoiceC');

  let dialogueCancelRequested = false;

  if (btnStopDialogue) {
    btnStopDialogue.addEventListener('click', () => {
      dialogueCancelRequested = true;
      btnStopDialogue.disabled = true;
      if (dialogueStatus) {
        dialogueStatus.innerHTML = '<span class="text-amber-400 font-semibold"><i class="fa-solid fa-hand mr-1"></i> Đang dừng tiến trình đối thoại...</span>';
      }
    });
  }

  if (btnLoadDialogueSample && dialogueScriptInput) {
    btnLoadDialogueSample.addEventListener('click', () => {
      dialogueScriptInput.value =
`C: Buổi sáng tại quán cà phê cổ phố, hai người bạn gặp lại nhau sau mười năm xa cách.
A: Chào bạn Quân! Đã lâu quá rồi chúng ta mới có dịp ngồi lại cùng nhau thế này.
B: Chào Huyền! Trông cậu vẫn rạng rỡ như ngày xưa vậy, thời gian dường như bỏ quên cậu rồi.
A: Cậu khéo miệng quá! Nghe nói gần đây cậu đang phát triển một dự án sách nói AI rất thành công?
B: Đúng vậy Huyền, công cụ VoiceViet Studio giúp chuyển đổi toàn bộ tiểu thuyết dài hàng vạn từ thành audio siêu nhanh.
C: Cuộc trò chuyện giữa hai người bạn diễn ra trong tiếng cười ấm áp của ngày chớm đông.`;
    });
  }

  if (btnGenerateDialogue) {
    btnGenerateDialogue.addEventListener('click', async () => {
      const script = dialogueScriptInput ? dialogueScriptInput.value.trim() : '';
      if (!script) {
        alert('Vui lòng nhập kịch bản đối thoại.');
        return;
      }

      dialogueCancelRequested = false;
      const lines = script.split('\n').map(l => l.trim()).filter(l => l.length > 0);
      const rawParsedLines = [];

      for (const line of lines) {
        const match = line.match(/^([ABCabc]):\s*(.*)$/);
        if (match) {
          const speaker = match[1].toUpperCase();
          const text = match[2].trim();
          if (text) {
            let voice = 'vi-entertainment';
            if (speaker === 'A' && dialogueVoiceA) voice = dialogueVoiceA.value;
            if (speaker === 'B' && dialogueVoiceB) voice = dialogueVoiceB.value;
            if (speaker === 'C' && dialogueVoiceC) voice = dialogueVoiceC.value;
            rawParsedLines.push({ speaker, text, voice });
          }
        } else {
          // Default to speaker C (narrator)
          let voice = dialogueVoiceC ? dialogueVoiceC.value : 'vi-advertising';
          rawParsedLines.push({ speaker: 'C', text: line, voice });
        }
      }

      // Merge adjacent lines of the same speaker & voice to save API calls
      const parsedLines = [];
      for (const item of rawParsedLines) {
        if (parsedLines.length > 0 && parsedLines[parsedLines.length - 1].speaker === item.speaker && parsedLines[parsedLines.length - 1].voice === item.voice) {
          parsedLines[parsedLines.length - 1].text += ' ' + item.text;
        } else {
          parsedLines.push({ ...item });
        }
      }

      if (parsedLines.length === 0) {
        alert('Không tìm thấy dòng đối thoại hợp lệ (Định dạng: A: Lời thoại hoặc B: Lời thoại).');
        return;
      }

      btnGenerateDialogue.disabled = true;
      if (btnStopDialogue) btnStopDialogue.disabled = false;
      if (dialogueStatus) dialogueStatus.innerHTML = `<span class="text-cyan-400 font-semibold"><i class="fa-solid fa-spinner fa-spin mr-1"></i> Bắt đầu xử lý ${parsedLines.length} câu thoại...</span>`;

      try {
        const audioBuffers = [];

        for (let i = 0; i < parsedLines.length; i++) {
          if (dialogueCancelRequested) {
            throw new Error('Đã hủy theo yêu cầu người dùng.');
          }

          const item = parsedLines[i];
          if (dialogueStatus) {
            dialogueStatus.innerHTML = `<span class="text-cyan-400 font-semibold"><i class="fa-solid fa-spinner fa-spin mr-1"></i> [${i + 1}/${parsedLines.length}] Đang đọc câu thoại ${item.speaker}...</span>`;
          }

          // Smart phonetic normalization for natural speech
          let cleanText = (item.text || '')
            .replace(/\bAI\b/g, 'Ây Ai')
            .replace(/\bVoiceViet\b/gi, 'Voi-Việt')
            .replace(/\bStudio\b/gi, 'X-tu-đi-ô')
            .replace(/\baudio\b/gi, 'ao-đi-ô')
            .replace(/\bChào Quân!/gi, 'Chào bạn Quân!')
            .replace(/\bChào Quân,/gi, 'Chào bạn Quân,');

          // Retry logic with countdown if hitting 429
          let lineBuffer = null;
          const maxRetries = 3;

          for (let attempt = 1; attempt <= maxRetries; attempt++) {
            if (dialogueCancelRequested) throw new Error('Đã hủy theo yêu cầu người dùng.');

            const res = await fetch('/api/cheap-tts/synthesize', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                text: cleanText,
                voice: item.voice,
                rate: 1.0,
                pauses: { sentence: 0.3 }
              })
            });

            if (res.ok) {
              lineBuffer = await res.arrayBuffer();
              break;
            }

            if (res.status === 429) {
              console.warn(`[Dialogue] 429 Rate limited. Cooling down...`);
              for (let s = 18; s > 0; s--) {
                if (dialogueCancelRequested) throw new Error('Đã hủy theo yêu cầu người dùng.');
                if (dialogueStatus) {
                  dialogueStatus.innerHTML = `<span class="text-amber-400 font-semibold"><i class="fa-solid fa-hourglass-half fa-spin mr-1"></i> API đang hạ nhiệt tần suất (${s}s)... Tự động tiếp tục câu ${i + 1}</span>`;
                }
                await new Promise(r => setTimeout(r, 1000));
              }
              continue;
            }

            const errData = await res.json().catch(() => ({}));
            throw new Error(errData.error || `Lỗi HTTP ${res.status}`);
          }

          if (!lineBuffer) {
            throw new Error(`Không thể tạo câu thoại ${i + 1} sau các lần thử.`);
          }

          audioBuffers.push(lineBuffer);

          // Fast pacing delay between speaker turns (0s for Free AI, 2s for Cheap-TTS Cloud)
          if (!item.voice.startsWith('free-') && i < parsedLines.length - 1 && !dialogueCancelRequested) {
            const waitSec = 2;
            for (let s = waitSec; s > 0; s--) {
              if (dialogueCancelRequested) break;
              if (dialogueStatus) {
                dialogueStatus.innerHTML = `<span class="text-slate-300">✓ Xong câu ${i + 1}/${parsedLines.length} (${item.speaker}). Chuyển tiếp sau <b class="text-cyan-400 font-mono">${s}s</b>...</span>`;
              }
              await new Promise(r => setTimeout(r, 1000));
            }
          }
        }

        if (dialogueCancelRequested) {
          throw new Error('Đã hủy theo yêu cầu người dùng.');
        }

        if (dialogueStatus) {
          dialogueStatus.innerHTML = `<span class="text-purple-400 font-semibold"><i class="fa-solid fa-spinner fa-spin mr-1"></i> Đang ghép nối âm thanh đối thoại...</span>`;
        }

        // Merge buffers using client WAV merger
        if (typeof mergeWavBuffersClient !== 'function') {
          throw new Error('Hệ thống ghép WAV chưa sẵn sàng.');
        }

        const mergedWavBlob = mergeWavBuffersClient(audioBuffers, 0.45, 22050);

        // Convert to lightweight MP3
        if (dialogueStatus) {
          dialogueStatus.innerHTML = `<span class="text-emerald-400 font-semibold"><i class="fa-solid fa-spinner fa-spin mr-1"></i> Đang nén sang MP3 siêu nhẹ (48 kbps)...</span>`;
        }

        const mp3Res = await fetch('/api/audio/convert-to-mp3?bitrate=48k', {
          method: 'POST',
          headers: { 'Content-Type': 'audio/wav' },
          body: mergedWavBlob
        });

        let finalAudioBlob = mergedWavBlob;
        let isMp3 = false;
        if (mp3Res.ok) {
          finalAudioBlob = await mp3Res.blob();
          isMp3 = true;
        }

        const finalUrl = URL.createObjectURL(finalAudioBlob);
        if (dialogueAudioPlayer) {
          dialogueAudioPlayer.src = finalUrl;
          dialogueAudioPlayer.play().catch(() => {});
        }
        if (btnDownloadDialogueMp3) {
          btnDownloadDialogueMp3.href = finalUrl;
          btnDownloadDialogueMp3.download = `hoi-thoai-${Date.now()}.${isMp3 ? 'mp3' : 'wav'}`;
        }
        if (dialogueOutputContainer) {
          dialogueOutputContainer.classList.remove('hidden');
        }

        if (dialogueStatus) {
          dialogueStatus.innerHTML = `<span class="text-emerald-400 font-bold"><i class="fa-solid fa-circle-check mr-1"></i> Hoàn thành! Đã tạo file đối thoại ${isMp3 ? 'MP3 siêu nhẹ' : 'WAV'}.</span>`;
        }
      } catch (err) {
        console.error('Dialogue error:', err);
        if (dialogueStatus) {
          dialogueStatus.innerHTML = `<span class="text-rose-400 font-medium"><i class="fa-solid fa-triangle-exclamation mr-1"></i> ${err.message}</span>`;
        }
      } finally {
        btnGenerateDialogue.disabled = false;
        if (btnStopDialogue) btnStopDialogue.disabled = true;
      }
    });
  }

  console.log('VoiceViet Studio Pro extensions initialized successfully.');
})();

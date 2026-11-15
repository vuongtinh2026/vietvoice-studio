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

  // 3. Voice Library Quick Select
  const voiceSelect = document.getElementById('voiceSelect');
  const quickVoiceBtns = document.querySelectorAll('.select-voice-quick-btn');

  quickVoiceBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const voiceId = btn.getAttribute('data-voice-id');
      if (voiceSelect && voiceId) {
        voiceSelect.value = voiceId;
        voiceSelect.dispatchEvent(new Event('change'));
        switchView('viewStudio');
        if (typeof showToast === 'function') {
          showToast(`Đã chọn giọng: ${voiceId}`);
        }
      }
    });
  });

  // 4. Voice Catalog Search Filter
  const voiceSearchInput = document.getElementById('voiceSearchInput');
  const voiceCatalogGrid = document.getElementById('voiceCatalogGrid');

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

  // 5. Multi-Speaker Dialogue Feature
  const btnLoadDialogueSample = document.getElementById('btnLoadDialogueSample');
  const dialogueScriptInput = document.getElementById('dialogueScriptInput');
  const btnGenerateDialogue = document.getElementById('btnGenerateDialogue');
  const dialogueStatus = document.getElementById('dialogueStatus');
  const dialogueOutputContainer = document.getElementById('dialogueOutputContainer');
  const dialogueAudioPlayer = document.getElementById('dialogueAudioPlayer');
  const btnDownloadDialogueMp3 = document.getElementById('btnDownloadDialogueMp3');
  const dialogueVoiceA = document.getElementById('dialogueVoiceA');
  const dialogueVoiceB = document.getElementById('dialogueVoiceB');
  const dialogueVoiceC = document.getElementById('dialogueVoiceC');

  if (btnLoadDialogueSample && dialogueScriptInput) {
    btnLoadDialogueSample.addEventListener('click', () => {
      dialogueScriptInput.value =
`C: Buổi sáng tại quán cà phê cổ phố, hai người bạn gặp lại nhau sau mười năm xa cách.
A: Chào Quân! Đã lâu quá rồi chúng ta mới có dịp ngồi lại cùng nhau thế này.
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

      const lines = script.split('\n').map(l => l.trim()).filter(l => l.length > 0);
      const parsedLines = [];

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
            parsedLines.push({ speaker, text, voice });
          }
        } else {
          // Default to speaker C (narrator)
          let voice = dialogueVoiceC ? dialogueVoiceC.value : 'vi-commercial';
          parsedLines.push({ speaker: 'C', text: line, voice });
        }
      }

      if (parsedLines.length === 0) {
        alert('Không tìm thấy dòng đối thoại hợp lệ (Định dạng: A: Lời thoại hoặc B: Lời thoại).');
        return;
      }

      btnGenerateDialogue.disabled = true;
      if (dialogueStatus) dialogueStatus.innerHTML = `<span class="text-cyan-400 font-semibold"><i class="fa-solid fa-spinner fa-spin mr-1"></i> Đang xử lý ${parsedLines.length} câu thoại...</span>`;

      try {
        const audioBuffers = [];

        for (let i = 0; i < parsedLines.length; i++) {
          const item = parsedLines[i];
          if (dialogueStatus) {
            dialogueStatus.innerHTML = `<span class="text-cyan-400"><i class="fa-solid fa-spinner fa-spin mr-1"></i> [${i + 1}/${parsedLines.length}] Đang đọc lời thoại ${item.speaker}...</span>`;
          }

          const res = await fetch('/api/cheap-tts/synthesize', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              text: item.text,
              voice: item.voice,
              rate: 1.0,
              pauses: { sentence: 0.3 }
            })
          });

          if (!res.ok) {
            const errData = await res.json().catch(() => ({}));
            throw new Error(errData.error || `Lỗi câu ${i + 1}`);
          }

          const buf = await res.arrayBuffer();
          audioBuffers.push(buf);

          // Small gap between calls
          if (i < parsedLines.length - 1) {
            await new Promise(r => setTimeout(r, 600));
          }
        }

        if (dialogueStatus) {
          dialogueStatus.innerHTML = `<span class="text-purple-400"><i class="fa-solid fa-spinner fa-spin mr-1"></i> Đang ghép nối âm thanh đối thoại...</span>`;
        }

        // Merge buffers using client WAV merger
        if (typeof mergeWavBuffersClient !== 'function') {
          throw new Error('Hệ thống ghép WAV chưa sẵn sàng.');
        }

        const mergedWavBlob = mergeWavBuffersClient(audioBuffers, 0.4, 22050);

        // Convert to lightweight MP3
        if (dialogueStatus) {
          dialogueStatus.innerHTML = `<span class="text-emerald-400"><i class="fa-solid fa-spinner fa-spin mr-1"></i> Đang nén file MP3 siêu nhẹ...</span>`;
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
          dialogueStatus.innerHTML = `<span class="text-emerald-400 font-bold"><i class="fa-solid fa-circle-check mr-1"></i> Hoàn thành! Đã tạo file đối thoại ${isMp3 ? 'MP3' : 'WAV'}.</span>`;
        }
      } catch (err) {
        console.error('Dialogue error:', err);
        if (dialogueStatus) {
          dialogueStatus.innerHTML = `<span class="text-rose-400"><i class="fa-solid fa-triangle-exclamation mr-1"></i> Lỗi: ${err.message}</span>`;
        }
      } finally {
        btnGenerateDialogue.disabled = false;
      }
    });
  }

  console.log('VoiceViet Studio Pro extensions initialized successfully.');
})();

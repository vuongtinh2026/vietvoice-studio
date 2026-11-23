/**
 * VoiceViet Studio Pro v7.0 — Option 2 Client License Interceptor & Owner Admin Console
 * - Automatic `X-License-Key` header injection + Server-Side Quota Sync on every synthesis
 * - Customer License Key Activation & Physical Hardware ID (HWID) Inspector
 * - Owner-Protected License Admin Dashboard (Create Key, Remote Lock/Unlock, Reset HWID, 2nd-PC Anti-Share Test, Clean Customer Package Exporter)
 */
(function () {
  'use strict';

  const SAVED_KEY_STORAGE = 'voiceviet_client_license_key_v7';
  let simSecondPcActive = false;
  let lastCreatedLicense = null;

  function getSavedKey() {
    return (localStorage.getItem(SAVED_KEY_STORAGE) || '').trim().toUpperCase();
  }

  function setSavedKey(k) {
    const clean = (k || '').trim().toUpperCase();
    if (clean) localStorage.setItem(SAVED_KEY_STORAGE, clean);
    else localStorage.removeItem(SAVED_KEY_STORAGE);
  }

  function escHtml(str) {
    return String(str || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  // =========================================================================
  // 1. FETCH INTERCEPTOR: ATTACH LICENSE KEY & SYNC SERVER QUOTA AUTOMATICALLY
  // =========================================================================
  const origFetch = window.fetch.bind(window);
  window.fetch = async function (input, init = {}) {
    const urlStr = typeof input === 'string' ? input : (input && input.url ? input.url : '');
    const isSynthApi = urlStr.includes('/api/free-tts/synthesize') || urlStr.includes('/api/cheap-tts/synthesize');

    if (isSynthApi) {
      const headers = new Headers(init.headers || {});
      const savedKey = getSavedKey();
      if (savedKey && !headers.has('X-License-Key')) {
        headers.set('X-License-Key', savedKey);
      }
      if (simSecondPcActive) {
        headers.set('X-Simulated-HWID', 'HWID-FAKE-PC02-9999');
        headers.set('X-Simulated-Machine', 'Windows-11-May-Khach-La-Thu-2');
      }
      init = { ...init, headers };
    }

    const res = await origFetch(input, init);

    if (isSynthApi && res.ok) {
      const usedHdr = res.headers.get('X-License-Used');
      const maxHdr = res.headers.get('X-License-Max');
      const remHdr = res.headers.get('X-License-Remaining');
      if (usedHdr !== null && window.VoiceVietQuota && typeof window.VoiceVietQuota.syncFromServer === 'function') {
        const isUnl = remHdr === 'UNLIMITED';
        window.VoiceVietQuota.syncFromServer({
          planId: isUnl ? 'unlimited' : (Number(maxHdr) >= 100000000 ? 'vip' : (Number(maxHdr) >= 10000000 ? 'standard' : (Number(maxHdr) >= 1000000 ? 'basic' : 'free'))),
          usedChars: Number(usedHdr) || 0,
          maxChars: Number(maxHdr) || 100000,
          unlimited: isUnl
        });
      }
    }

    return res;
  };

  // =========================================================================
  // 2. SYNC LICENSE & HWID STATUS FROM SERVER
  // =========================================================================
  async function syncClientLicenseStatus(activateFlag = false, overrideKey = null) {
    const activeKey = overrideKey !== null ? overrideKey.trim().toUpperCase() : getSavedKey();
    const headers = { 'Content-Type': 'application/json' };
    if (simSecondPcActive) {
      headers['X-Simulated-HWID'] = 'HWID-FAKE-PC02-9999';
      headers['X-Simulated-Machine'] = 'Windows-11-May-Khach-La-Thu-2';
    }

    try {
      const res = await origFetch('/api/license/status', {
        method: 'POST',
        headers,
        body: JSON.stringify({
          licenseKey: activeKey,
          activate: Boolean(activateFlag)
        })
      });
      const data = await res.json().catch(() => ({ ok: false, error: 'Lỗi đọc dữ liệu bản quyền' }));

      // Hide Owner Admin tab if running on an exported Customer Client Build!
      if (data.isCustomerClient) {
        const admNav = document.getElementById('navTabAdminLicenses');
        const admMob = document.getElementById('mobileTabAdminLicenses');
        if (admNav) admNav.classList.add('hidden');
        if (admMob) admMob.classList.add('hidden');
      }

      const hwidEl = document.getElementById('clientLocalHwidText');
      const machEl = document.getElementById('clientLocalMachineText');
      const planBadge = document.getElementById('clientCurrentPlanBadge');
      const remText = document.getElementById('clientServerRemainingText');
      const hdrLabel = document.getElementById('headerKeyStatusLabel');

      if (hwidEl) hwidEl.textContent = simSecondPcActive ? 'HWID-FAKE-PC02-9999 (Máy Lạ Test)' : (data.localHwid || data.hwid || 'HWID-...');
      if (machEl) machEl.textContent = simSecondPcActive ? 'Windows-11-May-Khach-La-Thu-2' : (data.localMachineLabel || data.machineLabel || '');

      if (data.ok) {
        if (planBadge) planBadge.textContent = `${data.planName || 'Gói Miễn Phí'} (${data.daysLeft || 30} ngày)`;
        if (remText) {
          remText.textContent = data.unlimited
            ? '♾️ Không giới hạn'
            : `${Number(data.remainingChars || 0).toLocaleString('vi-VN')} / ${Number(data.maxChars || 0).toLocaleString('vi-VN')} ký tự`;
        }
        if (hdrLabel) {
          hdrLabel.textContent = data.mode === 'licensed' && data.key
            ? `${data.key.slice(0, 10)}...`
            : 'Nhập Key';
        }
        if (window.VoiceVietQuota && typeof window.VoiceVietQuota.syncFromServer === 'function') {
          window.VoiceVietQuota.syncFromServer({
            planId: data.planId || 'free',
            usedChars: data.usedChars || 0,
            maxChars: data.maxChars || 100000,
            unlimited: Boolean(data.unlimited)
          });
        }
      } else {
        if (planBadge) planBadge.innerHTML = `<span class="text-rose-400">${escHtml(data.code || 'CHƯA KÍCH HOẠT')}</span>`;
        if (remText) remText.textContent = '0 ký tự (Đang bị chặn)';
        if (hdrLabel) hdrLabel.textContent = '⚠️ Key Bị Chặn';
      }

      return data;
    } catch (err) {
      return { ok: false, error: err.message };
    }
  }

  // =========================================================================
  // 3. CUSTOMER KEY ACTIVATION MODAL
  // =========================================================================
  function setupCustomerLicenseModal() {
    const modal = document.getElementById('licenseKeyModal');
    const btnOpen = document.getElementById('btnOpenLicenseModal');
    const btnClose = document.getElementById('btnCloseLicenseModal');
    const inputEl = document.getElementById('clientLicenseKeyInput');
    const msgEl = document.getElementById('clientLicenseModalMsg');
    const btnActivate = document.getElementById('btnActivateClientKey');
    const btnClear = document.getElementById('btnClearClientKey');

    function showModalMsg(text, isError = false) {
      if (!msgEl) return;
      msgEl.textContent = text;
      msgEl.className = `text-xs text-center font-semibold ${isError ? 'text-rose-400' : 'text-emerald-300'}`;
      msgEl.classList.remove('hidden');
    }

    if (btnOpen && modal) {
      btnOpen.addEventListener('click', async () => {
        if (inputEl) inputEl.value = getSavedKey();
        if (msgEl) msgEl.classList.add('hidden');
        modal.classList.remove('hidden');
        await syncClientLicenseStatus(false);
      });
    }

    if (btnClose && modal) {
      btnClose.addEventListener('click', () => modal.classList.add('hidden'));
      modal.addEventListener('click', (e) => {
        if (e.target === modal) modal.classList.add('hidden');
      });
    }

    if (btnActivate) {
      btnActivate.addEventListener('click', async () => {
        const entered = (inputEl ? inputEl.value : '').trim().toUpperCase();
        if (!entered) {
          showModalMsg('Vui lòng nhập Mã Bản Quyền (ví dụ: VVPRO-VIP8-8888-DEMO)!', true);
          return;
        }
        btnActivate.disabled = true;
        const data = await syncClientLicenseStatus(true, entered);
        btnActivate.disabled = false;

        if (data.ok) {
          setSavedKey(entered);
          showModalMsg(`✅ Kích hoạt thành công "${data.planName}"! Đã khóa cố định vào máy ${data.boundHwid}.`, false);
          if (typeof window.showToast === 'function') {
            window.showToast(`🔑 Đã kích hoạt gói "${data.planName}" trên máy này!`, 'success');
          }
          refreshAdminOverviewIfUnlocked();
        } else {
          showModalMsg(data.error || 'Không thể kích hoạt Key này!', true);
          if (typeof window.showToast === 'function') {
            window.showToast(data.error || 'Lỗi kích hoạt Key!', 'error');
          }
        }
      });
    }

    if (btnClear) {
      btnClear.addEventListener('click', async () => {
        setSavedKey('');
        if (inputEl) inputEl.value = '';
        const data = await syncClientLicenseStatus(false, '');
        if (data.ok) {
          showModalMsg('Đã chuyển về chế độ Dùng Thử Theo Mã Máy (HWID).', false);
        } else {
          showModalMsg(data.error || 'Chế độ dùng thử đang tắt.', true);
        }
      });
    }
  }

  // =========================================================================
  // 4. OWNER ADMIN DASHBOARD (#viewAdminLicenses)
  // =========================================================================
  async function fetchAdminApi(subPath, method = 'GET', bodyObj = null) {
    const tok = typeof window.getOwnerToken === 'function' ? window.getOwnerToken() : '';
    const opts = {
      method,
      headers: {
        'Content-Type': 'application/json',
        'X-Owner-Token': tok || ''
      }
    };
    if (bodyObj) opts.body = JSON.stringify(bodyObj);
    const res = await origFetch(`/api/admin/licenses/${subPath}`, opts);
    const data = await res.json().catch(() => ({ success: false, error: `HTTP ${res.status}` }));
    if (res.status === 403 && data.code === 'owner_pin_required') {
      updateAdminLockVisibility(false);
    }
    return data;
  }

  function updateAdminLockVisibility(unlocked) {
    const gate = document.getElementById('admLockedGateCard');
    const consoleBox = document.getElementById('admUnlockedConsole');
    if (gate) gate.classList.toggle('hidden', unlocked);
    if (consoleBox) consoleBox.classList.toggle('hidden', !unlocked);
  }

  function renderSimulatedPcBanner() {
    const banner = document.getElementById('admSimSecondPcBanner');
    if (banner) banner.classList.toggle('hidden', !simSecondPcActive);
  }

  async function refreshAdminOverviewIfUnlocked() {
    const tok = typeof window.getOwnerToken === 'function' ? window.getOwnerToken() : '';
    if (!tok) {
      updateAdminLockVisibility(false);
      return;
    }

    const data = await fetchAdminApi('overview', 'GET');
    if (!data.success) {
      updateAdminLockVisibility(false);
      return;
    }

    updateAdminLockVisibility(true);
    renderSimulatedPcBanner();

    const st = data.stats || {};
    const setEl = (id, txt) => {
      const el = document.getElementById(id);
      if (el) el.textContent = txt;
    };

    setEl('admStatTotalKeys', String(st.totalKeys || 0));
    setEl('admStatActiveKeys', String(st.activeKeys || 0));
    setEl('admStatBoundDevices', String(st.boundDevicesCount || 0));
    setEl('admStatTrialMachines', String(st.trialMachinesCount || 0));
    setEl('admStatTotalChars', Number(st.totalCharsConsumed || 0).toLocaleString('vi-VN'));
    setEl('admStatRevenue', `${Number(st.totalRevenueVnd || 0).toLocaleString('vi-VN')} đ`);
    if (data.localMachine) {
      setEl('admLocalHwidInfo', `Mã máy chủ: ${data.localMachine.hwid}`);
    }

    const chkTrial = document.getElementById('admToggleFreeHwidTrial');
    if (chkTrial && data.settings) {
      chkTrial.checked = Boolean(data.settings.allowFreeHwidTrial);
    }

    // Populate Owner Payment / Bank Config
    const pc = data.paymentConfig || {};
    const bankSel = document.getElementById('admBankSelect');
    const accNoIn = document.getElementById('admAccountNoInput');
    const accNameIn = document.getElementById('admAccountNameInput');
    const globIn = document.getElementById('admGlobalCheckoutInput');
    const tgBotIn = document.getElementById('admTelegramBotInput');
    const tgChatIn = document.getElementById('admTelegramChatIdInput');
    const sepayIn = document.getElementById('admSepaySecretInput');
    const bankStatusBadge = document.getElementById('admBankConfigStatusBadge');

    if (bankSel && pc.bankId) bankSel.value = pc.bankId;
    if (accNoIn && document.activeElement !== accNoIn) accNoIn.value = pc.accountNo || '';
    if (accNameIn && document.activeElement !== accNameIn) accNameIn.value = pc.accountName || '';
    if (globIn && document.activeElement !== globIn) globIn.value = pc.globalCheckoutUrl || '';
    if (tgBotIn && document.activeElement !== tgBotIn) tgBotIn.value = pc.telegramBotToken || '';
    if (tgChatIn && document.activeElement !== tgChatIn) tgChatIn.value = pc.telegramChatId || '';
    if (sepayIn && document.activeElement !== sepayIn) sepayIn.value = pc.sepaySecretKey || '';

    if (bankStatusBadge) {
      if (pc.accountNo) {
        bankStatusBadge.className = 'text-[11px] px-3 py-1 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-400/40 font-extrabold';
        bankStatusBadge.textContent = `✅ Đang nhận tiền về: ${pc.bankId} • ${pc.accountNo} (${pc.accountName || ''})`;
      } else {
        bankStatusBadge.className = 'text-[11px] px-3 py-1 rounded-full bg-amber-500/20 text-amber-200 border border-amber-400/40 font-bold';
        bankStatusBadge.textContent = '⚠️ Chưa điền Số Tài Khoản thật của bạn';
      }
    }

    const pendingCnt = Number(st.pendingOrdersCount || 0);
    const ordBadge = document.getElementById('admPendingOrdersBadge');
    const sideBadge = document.getElementById('sidebarAdminBadge');
    if (ordBadge) {
      ordBadge.textContent = `${pendingCnt} đơn chờ duyệt`;
      ordBadge.className = pendingCnt > 0
        ? 'text-[11px] px-2.5 py-0.5 rounded-full bg-rose-500 text-white font-extrabold animate-pulse'
        : 'text-[11px] px-2.5 py-0.5 rounded-full bg-white/10 text-slate-300 font-bold';
    }
    if (sideBadge) {
      sideBadge.textContent = pendingCnt > 0 ? `🔔 ${pendingCnt} Đơn` : 'Admin';
      sideBadge.className = pendingCnt > 0
        ? 'text-[9px] bg-rose-500 text-white px-1.5 py-0.5 rounded-md ml-auto font-extrabold shrink-0 whitespace-nowrap animate-pulse'
        : 'text-[9px] bg-amber-500/25 text-amber-200 border border-amber-400/45 px-1.5 py-0.5 rounded-md ml-auto font-bold shrink-0 whitespace-nowrap';
    }

    renderAdminOrdersTable(data.orders || []);
    renderAdminLicensesTable(data.licenses || []);
  }

  function renderAdminOrdersTable(orders) {
    const tbody = document.getElementById('admOrdersTableBody');
    if (!tbody) return;
    if (!orders.length) {
      tbody.innerHTML = '<tr><td colspan="6" class="py-5 text-center text-slate-400">Chưa có đơn đặt mua mới nào. Khi khách bấm chọn gói ở Bảng Giá, đơn hàng sẽ hiện ngay tại đây!</td></tr>';
      return;
    }

    tbody.innerHTML = orders.map(ord => {
      const timeStr = ord.createdAt ? new Date(ord.createdAt).toLocaleString('vi-VN', { hour: '2-digit', minute: '2-digit', day: '2-digit', month: '2-digit' }) : '';
      const amtFmt = Number(ord.amountVnd || 0).toLocaleString('vi-VN');
      const isPaid = ord.status === 'paid';
      const isTransferred = ord.status === 'transferred_waiting';

      let stHtml = '<span class="px-2 py-0.5 rounded-full bg-slate-700/60 text-slate-300 text-[10px] font-bold">⏳ Đang xem mã QR</span>';
      if (isTransferred) {
        stHtml = '<span class="px-2.5 py-0.5 rounded-full bg-amber-500/25 text-amber-200 border border-amber-400/50 text-[10px] font-extrabold animate-pulse">💸 KHÁCH BÁO ĐÃ CHUYỂN TIỀN!</span>';
      } else if (isPaid) {
        stHtml = `<span class="px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-400/40 text-[10px] font-extrabold">✅ ĐÃ CẤP KEY (${ord.verifiedBy === 'sepay_auto' ? 'SePay 3s' : 'Thủ công'})</span>
                  <div class="font-mono text-[10px] text-amber-300 mt-0.5">${escHtml(ord.issuedKey || '')}</div>`;
      }

      const actionsHtml = isPaid
        ? `<button type="button" data-ord-act="delete" data-code="${escHtml(ord.orderCode)}" class="px-2 py-1 rounded-lg bg-white/5 hover:bg-rose-500/25 text-slate-400 hover:text-rose-200 text-[10px] cursor-pointer"><i class="fa-regular fa-trash-can"></i></button>`
        : `<div class="flex flex-wrap items-center justify-end gap-1.5">
             <button type="button" data-ord-act="approve" data-code="${escHtml(ord.orderCode)}" class="px-2.5 py-1.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-extrabold text-[10px] cursor-pointer shadow">
               ✅ Đã Nhận Tiền → Cấp Key
             </button>
             <button type="button" data-ord-act="sim_sepay" data-code="${escHtml(ord.orderCode)}" data-amt="${ord.amountVnd}" class="px-2 py-1.5 rounded-xl bg-cyan-500/20 hover:bg-cyan-500/35 text-cyan-200 border border-cyan-400/40 font-bold text-[10px] cursor-pointer" title="Giả lập Ngân hàng báo biến động số dư sang SePay tự động duyệt đơn trong 1 giây">
               🤖 Test SePay Tự Động
             </button>
             <button type="button" data-ord-act="delete" data-code="${escHtml(ord.orderCode)}" class="px-2 py-1 rounded-lg bg-white/5 hover:bg-rose-500/25 text-slate-400 hover:text-rose-200 text-[10px] cursor-pointer">
               <i class="fa-regular fa-trash-can"></i>
             </button>
           </div>`;

      return `
        <tr class="hover:bg-white/[0.03] transition ${isTransferred ? 'bg-amber-500/[0.06]' : ''}">
          <td class="py-3 pr-3">
            <div class="font-mono font-extrabold text-emerald-300 text-xs">${escHtml(ord.orderCode)}</div>
            <div class="text-[10px] text-slate-400">${escHtml(timeStr)}</div>
          </td>
          <td class="py-3 px-3">
            <div class="font-bold text-white">${escHtml(ord.customerName || 'Khách mới')}</div>
            <div class="text-[11px] text-cyan-300 font-medium">${escHtml(ord.customerContact || 'Chưa nhập SĐT/Zalo')}</div>
          </td>
          <td class="py-3 px-3">
            <div class="font-bold text-purple-200">${escHtml(ord.planName)}</div>
            <div class="font-mono font-extrabold text-amber-300 text-xs">+${amtFmt} VNĐ</div>
          </td>
          <td class="py-3 px-3">
            <div class="font-mono text-[11px] text-cyan-200">${escHtml(ord.clientHwid || '')}</div>
            <div class="text-[10px] text-slate-400 truncate max-w-[150px]">${escHtml(ord.clientMachineLabel || '')}</div>
          </td>
          <td class="py-3 px-3">${stHtml}</td>
          <td class="py-3 pl-3 text-right">${actionsHtml}</td>
        </tr>
      `;
    }).join('');

    tbody.querySelectorAll('button[data-ord-act]').forEach(btn => {
      btn.addEventListener('click', async () => {
        const act = btn.getAttribute('data-ord-act');
        const orderCode = btn.getAttribute('data-code');
        if (!act || !orderCode) return;

        if (act === 'approve') {
          const res = await fetchAdminApi('approve-order', 'POST', { orderCode });
          if (res.success && res.license) {
            if (typeof window.showToast === 'function') {
              window.showToast(`✅ Đã duyệt đơn ${orderCode} & tự cấp Key ${res.license.key} thẳng sang máy khách!`, 'success');
            }
            refreshAdminOverviewIfUnlocked();
          }
          return;
        }

        if (act === 'sim_sepay') {
          const amt = Number(btn.getAttribute('data-amt') || 25000);
          const r = await origFetch('/api/payment/sepay-webhook', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              transferType: 'in',
              transferAmount: amt,
              content: `CHUYEN KHOAN ${orderCode} THANH TOAN GOI VOICEVIET`
            })
          });
          const d = await r.json().catch(() => ({}));
          if (d.ok && d.activated) {
            if (typeof window.showToast === 'function') {
              window.showToast(`🤖 [SePay Webhook Tự Động] Ngân hàng báo +${amt.toLocaleString('vi-VN')}đ (${orderCode}) → Đã tự động cấp Key ${d.issuedKey}!`, 'success');
            }
            await syncClientLicenseStatus(false);
            refreshAdminOverviewIfUnlocked();
          } else if (typeof window.showToast === 'function') {
            window.showToast(d.error || 'Lỗi giả lập SePay Webhook', 'error');
          }
          return;
        }

        if (act === 'delete') {
          await fetchAdminApi('delete-order', 'POST', { orderCode });
          refreshAdminOverviewIfUnlocked();
        }
      });
    });
  }

  function renderAdminLicensesTable(licenses) {
    const tbody = document.getElementById('admLicensesTableBody');
    if (!tbody) return;

    if (!licenses.length) {
      tbody.innerHTML = '<tr><td colspan="6" class="py-6 text-center text-slate-400">Chưa có mã bản quyền nào. Hãy bấm tạo Key mới ở trên!</td></tr>';
      return;
    }

    const currentSavedKey = getSavedKey();

    tbody.innerHTML = licenses.map(lic => {
      const isLocked = lic.status === 'locked';
      const isExpired = lic.expiresAt && Date.now() > lic.expiresAt;
      const daysLeft = lic.expiresAt ? Math.max(0, Math.ceil((lic.expiresAt - Date.now()) / 86400000)) : 30;
      const usedFmt = Number(lic.usedChars || 0).toLocaleString('vi-VN');
      const maxFmt = lic.unlimited ? '♾️ Không giới hạn' : Number(lic.maxChars || 0).toLocaleString('vi-VN');
      const pct = lic.unlimited ? 10 : Math.min(100, Math.round(((lic.usedChars || 0) / Math.max(1, lic.maxChars || 1)) * 100));
      const isActiveHere = currentSavedKey === lic.key;

      const hwidHtml = lic.boundHwid
        ? `<div class="font-mono text-cyan-300 font-bold text-[11px]">🔒 ${escHtml(lic.boundHwid)}</div>
           <div class="text-[10px] text-slate-400 truncate max-w-[180px]" title="${escHtml(lic.boundMachineLabel || '')}">${escHtml(lic.boundMachineLabel || 'Đã khóa 1 máy')}</div>`
        : `<span class="text-[11px] text-amber-300/90 italic">⏳ Chờ máy đầu tiên kích hoạt</span>`;

      const statusBadge = isLocked
        ? '<span class="px-2 py-0.5 rounded-full bg-rose-500/20 text-rose-300 border border-rose-500/40 text-[10px] font-extrabold">🔒 ĐÃ KHÓA</span>'
        : (isExpired
          ? '<span class="px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/40 text-[10px] font-extrabold">⌛ HẾT HẠN</span>'
          : '<span class="px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 text-[10px] font-extrabold">● HOẠT ĐỘNG</span>');

      return `
        <tr class="hover:bg-white/[0.03] transition">
          <td class="py-3 pr-3">
            <div class="font-mono font-extrabold text-amber-300 text-xs flex items-center gap-1.5">
              <span>${escHtml(lic.key)}</span>
              ${isActiveHere ? '<span class="text-[9px] px-1.5 py-0.2 rounded bg-emerald-500/25 text-emerald-200 border border-emerald-400/40">Đang dùng</span>' : ''}
            </div>
            <div class="text-xs font-semibold text-white mt-0.5">${escHtml(lic.customerName || 'Khách hàng')}</div>
            ${lic.customerContact ? `<div class="text-[10px] text-slate-400">${escHtml(lic.customerContact)}</div>` : ''}
          </td>
          <td class="py-3 px-3">
            <div class="font-bold text-purple-200">${escHtml(lic.planName || lic.planId)}</div>
            <div class="text-[11px] text-slate-400 mt-0.5">Còn <b>${daysLeft}</b> ngày</div>
          </td>
          <td class="py-3 px-3 min-w-[165px]">
            <div class="font-mono text-[11px] text-slate-100"><b>${usedFmt}</b> / ${maxFmt}</div>
            <div class="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden mt-1">
              <div class="h-full bg-gradient-to-r from-cyan-400 to-purple-500" style="width:${pct}%"></div>
            </div>
          </td>
          <td class="py-3 px-3">${hwidHtml}</td>
          <td class="py-3 px-3">${statusBadge}</td>
          <td class="py-3 pl-3 text-right">
            <div class="flex flex-wrap items-center justify-end gap-1.5">
              <button type="button" data-act="apply_local" data-key="${escHtml(lic.key)}" class="px-2 py-1 rounded-lg bg-emerald-500/20 hover:bg-emerald-500/35 text-emerald-200 border border-emerald-400/35 text-[10px] font-bold cursor-pointer" title="Kích hoạt Key này trên máy của bạn">
                🔑 Gắn Máy Này
              </button>
              <button type="button" data-act="test_2nd_pc" data-key="${escHtml(lic.key)}" class="px-2 py-1 rounded-lg bg-cyan-500/20 hover:bg-cyan-500/35 text-cyan-200 border border-cyan-400/35 text-[10px] font-bold cursor-pointer" title="Giả lập người khác đem Key này sang Máy Tính Thứ 2 để kiểm chứng bị chặn!">
                🧪 Test Máy #2
              </button>
              <button type="button" data-act="reset_hwid" data-key="${escHtml(lic.key)}" class="px-2 py-1 rounded-lg bg-white/5 hover:bg-white/15 text-slate-200 border border-white/15 text-[10px] font-semibold cursor-pointer" title="Gỡ mã máy cũ khi khách mua máy tính mới">
                🔓 Gỡ HWID
              </button>
              <button type="button" data-act="extend_30d" data-key="${escHtml(lic.key)}" class="px-2 py-1 rounded-lg bg-purple-500/20 hover:bg-purple-500/35 text-purple-200 border border-purple-400/35 text-[10px] font-semibold cursor-pointer" title="Gia hạn thêm 30 ngày">
                +30 Ngày
              </button>
              <button type="button" data-act="${isLocked ? 'unlock' : 'lock'}" data-key="${escHtml(lic.key)}" class="px-2 py-1 rounded-lg ${isLocked ? 'bg-amber-500/25 text-amber-200 border-amber-400/40' : 'bg-rose-500/20 text-rose-300 border-rose-500/40'} border text-[10px] font-bold cursor-pointer">
                ${isLocked ? '🔓 Mở Lại' : '🔒 Khóa Key'}
              </button>
              <button type="button" data-act="delete" data-key="${escHtml(lic.key)}" class="px-2 py-1 rounded-lg bg-white/5 hover:bg-rose-600/30 text-slate-400 hover:text-rose-200 text-[10px] cursor-pointer" title="Xóa Key">
                <i class="fa-regular fa-trash-can"></i>
              </button>
            </div>
          </td>
        </tr>
      `;
    }).join('');

    tbody.querySelectorAll('button[data-act]').forEach(btn => {
      btn.addEventListener('click', async () => {
        const act = btn.getAttribute('data-act');
        const key = btn.getAttribute('data-key');
        if (!act || !key) return;

        if (act === 'apply_local') {
          simSecondPcActive = false;
          renderSimulatedPcBanner();
          const res = await syncClientLicenseStatus(true, key);
          if (res.ok) {
            setSavedKey(key);
            if (typeof window.showToast === 'function') {
              window.showToast(`✅ Đã kích hoạt & khóa Key "${key}" vào máy chủ hiện tại (${res.boundHwid})!`, 'success');
            }
            refreshAdminOverviewIfUnlocked();
          } else if (typeof window.showToast === 'function') {
            window.showToast(res.error || 'Không thể kích hoạt Key', 'error');
          }
          return;
        }

        if (act === 'test_2nd_pc') {
          // Ensure key is bound to Machine 1 first, then test from Fake Machine 2!
          simSecondPcActive = false;
          await syncClientLicenseStatus(true, key);
          setSavedKey(key);

          simSecondPcActive = true;
          renderSimulatedPcBanner();
          const testRes = await syncClientLicenseStatus(true, key);
          if (!testRes.ok && typeof window.showToast === 'function') {
            window.showToast(testRes.error, 'error');
          }
          refreshAdminOverviewIfUnlocked();
          return;
        }

        if (act === 'delete') {
          await fetchAdminApi('mutate', 'POST', { key, action: 'delete' });
          if (getSavedKey() === key) setSavedKey('');
          await syncClientLicenseStatus(false);
          refreshAdminOverviewIfUnlocked();
          return;
        }

        if (act === 'extend_30d') {
          await fetchAdminApi('mutate', 'POST', { key, action: 'topup', addDays: 30 });
          if (typeof window.showToast === 'function') window.showToast(`Đã gia hạn +30 ngày cho Key ${key}!`, 'success');
          await syncClientLicenseStatus(false);
          refreshAdminOverviewIfUnlocked();
          return;
        }

        await fetchAdminApi('mutate', 'POST', { key, action: act });
        if (typeof window.showToast === 'function') {
          const msgMap = {
            lock: `🔒 Đã KHÓA Key ${key} từ xa! Máy khách sẽ bị ngắt quyền ngay lập tức.`,
            unlock: `🔓 Đã MỞ LẠI Key ${key}!`,
            reset_hwid: `🔓 Đã gỡ mã máy cũ cho Key ${key} — Khách có thể kích hoạt trên máy mới!`
          };
          window.showToast(msgMap[act] || 'Đã cập nhật Key!', 'info');
        }
        await syncClientLicenseStatus(false);
        refreshAdminOverviewIfUnlocked();
      });
    });
  }

  function setupAdminDashboardEvents() {
    const btnUnlock = document.getElementById('btnUnlockAdminDashboard');
    if (btnUnlock) {
      btnUnlock.addEventListener('click', async () => {
        if (typeof window.promptOwnerUnlockModal === 'function') {
          const ok = await window.promptOwnerUnlockModal();
          if (ok) {
            await refreshAdminOverviewIfUnlocked();
          }
        }
      });
    }

    // Refresh whenever user clicks the Admin tab
    document.querySelectorAll('[data-view="viewAdminLicenses"]').forEach(tab => {
      tab.addEventListener('click', () => {
        refreshAdminOverviewIfUnlocked();
      });
    });

    const btnRefresh = document.getElementById('btnRefreshAdminList');
    if (btnRefresh) btnRefresh.addEventListener('click', refreshAdminOverviewIfUnlocked);

    const btnExitSim = document.getElementById('btnExitSimSecondPc');
    if (btnExitSim) {
      btnExitSim.addEventListener('click', async () => {
        simSecondPcActive = false;
        renderSimulatedPcBanner();
        await syncClientLicenseStatus(false);
        if (typeof window.showToast === 'function') {
          window.showToast('Đã quay lại Mã phần cứng (HWID) thật của máy bạn!', 'success');
        }
      });
    }

    const chkTrial = document.getElementById('admToggleFreeHwidTrial');
    if (chkTrial) {
      chkTrial.addEventListener('change', async () => {
        await fetchAdminApi('settings', 'POST', { allowFreeHwidTrial: chkTrial.checked });
        await syncClientLicenseStatus(false);
        if (typeof window.showToast === 'function') {
          window.showToast(
            chkTrial.checked
              ? 'Đã BẬT cho phép dùng thử 100.000 ký tự / 1 máy HWID!'
              : '🔒 Đã TẮT dùng thử miễn phí — Mọi máy khách BẮT BUỘC phải nhập Key mới tạo được giọng!',
            'info'
          );
        }
      });
    }

    const btnCreate = document.getElementById('btnAdmCreateKey');
    if (btnCreate) {
      btnCreate.addEventListener('click', async () => {
        const customerName = document.getElementById('admCustomerName')?.value || '';
        const customerContact = document.getElementById('admCustomerContact')?.value || '';
        const planId = document.getElementById('admPlanSelect')?.value || 'standard';
        const durationDays = Number(document.getElementById('admDurationDays')?.value) || 30;

        btnCreate.disabled = true;
        const res = await fetchAdminApi('create', 'POST', {
          customerName,
          customerContact,
          planId,
          durationDays
        });
        btnCreate.disabled = false;

        if (res.success && res.license) {
          lastCreatedLicense = res.license;
          const box = document.getElementById('admCreatedKeyBox');
          const keyDisp = document.getElementById('admNewKeyDisplay');
          const subDisp = document.getElementById('admNewKeySub');
          if (box) box.classList.remove('hidden');
          if (keyDisp) keyDisp.textContent = res.license.key;
          if (subDisp) {
            const quotaTxt = res.license.unlimited ? 'Không giới hạn ký tự' : `${Number(res.license.maxChars).toLocaleString('vi-VN')} ký tự`;
            subDisp.textContent = `${res.license.customerName} • ${res.license.planName} (${quotaTxt}) • ${durationDays} ngày • Khóa cứng 1 máy HWID`;
          }
          if (typeof window.showToast === 'function') {
            window.showToast(`🎉 Đã tạo mã Key mới: ${res.license.key}`, 'success');
          }
          refreshAdminOverviewIfUnlocked();
        } else if (typeof window.showToast === 'function') {
          window.showToast(res.error || 'Không thể tạo Key', 'error');
        }
      });
    }

    const btnCopyMsg = document.getElementById('btnCopyNewKeyMessage');
    if (btnCopyMsg) {
      btnCopyMsg.addEventListener('click', async () => {
        if (!lastCreatedLicense) return;
        const quotaTxt = lastCreatedLicense.unlimited
          ? 'Không giới hạn ký tự'
          : `${Number(lastCreatedLicense.maxChars).toLocaleString('vi-VN')} ký tự`;
        const msg = [
          `🎙️ THÔNG TIN BẢN QUYỀN VOICEVIET STUDIO PRO`,
          `• Khách hàng: ${lastCreatedLicense.customerName}`,
          `• Gói đăng ký: ${lastCreatedLicense.planName} (${quotaTxt})`,
          `• Mã Kích Hoạt (License Key): ${lastCreatedLicense.key}`,
          `• Cơ chế bảo vệ: Khóa cố định 01 máy tính đầu tiên kích hoạt (HWID Lock).`,
          `👉 Hướng dẫn: Mở phần mềm -> Bấm nút "🔑 Nhập Key" góc trên phải -> Dán mã Key trên để kích hoạt ngay!`
        ].join('\n');
        try {
          await navigator.clipboard.writeText(msg);
          if (typeof window.showToast === 'function') {
            window.showToast('📋 Đã copy trọn bộ tin nhắn bàn giao Key cho khách!', 'success');
          }
        } catch {}
      });
    }

    const btnApplyNew = document.getElementById('btnApplyNewKeyLocally');
    if (btnApplyNew) {
      btnApplyNew.addEventListener('click', async () => {
        if (!lastCreatedLicense) return;
        simSecondPcActive = false;
        renderSimulatedPcBanner();
        const r = await syncClientLicenseStatus(true, lastCreatedLicense.key);
        if (r.ok) {
          setSavedKey(lastCreatedLicense.key);
          if (typeof window.showToast === 'function') {
            window.showToast(`🔑 Đã kích hoạt thử Key ${lastCreatedLicense.key} trên máy này!`, 'success');
          }
          refreshAdminOverviewIfUnlocked();
        }
      });
    }

    const btnExportPkg = document.getElementById('btnAdmExportCustomerPkg');
    if (btnExportPkg) {
      btnExportPkg.addEventListener('click', async () => {
        const serverUrl = document.getElementById('admServerUrlInput')?.value || 'http://127.0.0.1:3000';
        const outBox = document.getElementById('admExportResultBox');
        btnExportPkg.disabled = true;
        const origHtml = btnExportPkg.innerHTML;
        btnExportPkg.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang mã hóa & đóng gói...';

        const res = await fetchAdminApi('export-package', 'POST', { licenseServerUrl: serverUrl });
        btnExportPkg.disabled = false;
        btnExportPkg.innerHTML = origHtml;

        if (res.success && res.package && outBox) {
          const p = res.package;
          outBox.classList.remove('hidden');
          outBox.innerHTML = `
            <div class="text-emerald-300 font-extrabold flex items-center gap-2">
              <i class="fa-solid fa-circle-check"></i> Đã xuất thành công Bộ Cài Đặt Sạch & Mã Hóa cho khách hàng!
            </div>
            <div>• Thư mục xuất bản: <code class="text-amber-300 bg-white/5 px-2 py-0.5 rounded">${escHtml(p.outDir)}</code> (${p.filesCount} tệp)</div>
            <div>• Máy chủ kiểm tra Key gắn cứng: <code class="text-cyan-300">${escHtml(p.licenseServerUrl)}</code></div>
            <div class="text-emerald-200/90">• Kiểm tra an toàn: <b>Đã loại bỏ 100% Giọng Độc Quyền (private_voices)</b> & <b>Đã mã hóa rối toàn bộ JS giao diện</b>!</div>
            <div class="text-slate-400 text-[11px] mt-0.5">👉 Bạn chỉ cần nén ZIP thư mục <code>VoiceViet_Client_Pro</code> gửi cho khách. Khách giải nén chạy file <code>1_Chay_VoiceViet_Windows.bat</code> (hoặc <code>.command</code> trên Mac) và nhập Key bạn cấp là dùng ngay!</div>
          `;
          if (typeof window.showToast === 'function') {
            window.showToast('📦 Đã đóng gói bản cài đặt sạch giao khách thành công!', 'success');
          }
        } else if (typeof window.showToast === 'function') {
          window.showToast(res.error || 'Lỗi đóng gói bộ cài đặt', 'error');
        }
      });
    }
  }

  // =========================================================================
  // 5. REAL ORDER CHECKOUT FLOW + LIVE 3-SECOND AUTO-ACTIVATION POLLING
  // =========================================================================
  let activeCheckoutOrderCode = '';
  let orderPollTimer = null;

  function stopOrderPolling() {
    if (orderPollTimer) {
      clearInterval(orderPollTimer);
      orderPollTimer = null;
    }
  }

  async function openRealOrderCheckoutModal(planName, amount) {
    const modal = document.getElementById('vietqrModal');
    const qrImg = document.getElementById('vietqrImage');
    const planEl = document.getElementById('vietqrPlanName');
    const amtEl = document.getElementById('vietqrAmount');
    const memoEl = document.getElementById('vietqrMemo');
    const waitStatusEl = document.getElementById('checkoutOrderWaitStatus');
    const custNameEl = document.getElementById('checkoutCustName');
    const custContactEl = document.getElementById('checkoutCustContact');
    const globalBtn = document.getElementById('btnGlobalStripeCheckout');

    if (!modal) return;
    stopOrderPolling();

    const savedCustName = localStorage.getItem('voiceviet_cust_name') || '';
    const savedCustContact = localStorage.getItem('voiceviet_cust_contact') || '';
    if (custNameEl && !custNameEl.value) custNameEl.value = savedCustName;
    if (custContactEl && !custContactEl.value) custContactEl.value = savedCustContact;

    if (planEl) planEl.textContent = planName;
    if (amtEl) amtEl.textContent = `${Number(amount).toLocaleString('vi-VN')} VNĐ`;
    if (memoEl) memoEl.textContent = 'Đang tạo mã đơn...';
    modal.classList.remove('hidden');

    try {
      const res = await origFetch('/api/payment/create-order', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          amountVnd: Number(amount) || 25000,
          customerName: custNameEl ? custNameEl.value.trim() : '',
          customerContact: custContactEl ? custContactEl.value.trim() : ''
        })
      });
      const data = await res.json().catch(() => ({}));
      if (data.success && data.order) {
        const ord = data.order;
        activeCheckoutOrderCode = ord.orderCode;
        if (memoEl) memoEl.textContent = ord.orderCode;
        if (qrImg && ord.qrImageUrl) qrImg.src = ord.qrImageUrl;
        if (globalBtn && ord.globalCheckoutUrl) {
          globalBtn.href = ord.globalCheckoutUrl;
          globalBtn.target = '_blank';
          globalBtn.onclick = null;
        }
        if (waitStatusEl) {
          waitStatusEl.innerHTML = ord.bankConfigured
            ? `<span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span><span>Quét QR với đúng nội dung <b>${escHtml(ord.orderCode)}</b> — Máy này sẽ tự nhận Key ngay khi tiền về!</span>`
            : `<span class="w-2 h-2 rounded-full bg-amber-400 animate-pulse"></span><span class="text-amber-200">Mã đơn <b>${escHtml(ord.orderCode)}</b> đã tạo! (Chủ web nhớ điền Số Tài Khoản thật trong mục Quản Lý Key & Khách)</span>`;
        }
        refreshAdminOverviewIfUnlocked();

        // Poll every 3s: as soon as SePay or Admin approves, auto-activate Key on this machine!
        orderPollTimer = setInterval(async () => {
          if (modal.classList.contains('hidden') || !activeCheckoutOrderCode) {
            stopOrderPolling();
            return;
          }
          try {
            const pRes = await origFetch(`/api/payment/order-status?code=${encodeURIComponent(activeCheckoutOrderCode)}`);
            const pData = await pRes.json().catch(() => ({}));
            if (pData.ok && pData.order && pData.order.status === 'paid' && pData.order.issuedKey) {
              stopOrderPolling();
              const issuedKey = pData.order.issuedKey;
              setSavedKey(issuedKey);
              await syncClientLicenseStatus(true, issuedKey);
              modal.classList.add('hidden');
              if (typeof window.showToast === 'function') {
                window.showToast(`🎉 Thanh toán thành công! Đã tự động kích hoạt Key "${issuedKey}" (${pData.order.planName})!`, 'success');
              }
              refreshAdminOverviewIfUnlocked();
            }
          } catch {}
        }, 3000);
      }
    } catch (err) {
      if (waitStatusEl) waitStatusEl.textContent = `Lỗi tạo đơn: ${err.message}`;
    }
  }
  window.openRealOrderCheckoutModal = openRealOrderCheckoutModal;

  function setupPaymentAndBankEvents() {
    const btnMarkPaid = document.getElementById('btnCustomerMarkTransferred');
    const waitStatusEl = document.getElementById('checkoutOrderWaitStatus');
    if (btnMarkPaid) {
      btnMarkPaid.addEventListener('click', async () => {
        if (!activeCheckoutOrderCode) return;
        const cName = document.getElementById('checkoutCustName')?.value.trim() || '';
        const cContact = document.getElementById('checkoutCustContact')?.value.trim() || '';
        if (cName) localStorage.setItem('voiceviet_cust_name', cName);
        if (cContact) localStorage.setItem('voiceviet_cust_contact', cContact);

        btnMarkPaid.disabled = true;
        const r = await origFetch('/api/payment/mark-transferred', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            orderCode: activeCheckoutOrderCode,
            customerName: cName || 'Khách chuyển khoản QR',
            customerContact: cContact || 'Đang mở màn hình chờ nhận Key'
          })
        });
        btnMarkPaid.disabled = false;
        const d = await r.json().catch(() => ({}));
        if (d.success) {
          if (waitStatusEl) {
            waitStatusEl.innerHTML = `<i class="fa-solid fa-spinner fa-spin text-amber-300"></i> <span class="text-amber-200 font-semibold">Đã gửi thông báo cho Quản trị viên (Mã đơn <b>${escHtml(activeCheckoutOrderCode)}</b>)! Giữ nguyên màn hình để nhận Key tự động...</span>`;
          }
          if (typeof window.showToast === 'function') {
            window.showToast(`💸 Đã báo chuyển khoản đơn ${activeCheckoutOrderCode}! Hệ thống sẽ tự mở khóa ngay khi xác nhận tiền về.`, 'success');
          }
          refreshAdminOverviewIfUnlocked();
        }
      });
    }

    const btnSaveBank = document.getElementById('btnSavePaymentConfig');
    if (btnSaveBank) {
      btnSaveBank.addEventListener('click', async () => {
        const payload = {
          bankId: document.getElementById('admBankSelect')?.value || 'MB',
          accountNo: document.getElementById('admAccountNoInput')?.value || '',
          accountName: document.getElementById('admAccountNameInput')?.value || '',
          globalCheckoutUrl: document.getElementById('admGlobalCheckoutInput')?.value || '',
          telegramBotToken: document.getElementById('admTelegramBotInput')?.value || '',
          telegramChatId: document.getElementById('admTelegramChatIdInput')?.value || '',
          sepaySecretKey: document.getElementById('admSepaySecretInput')?.value || ''
        };
        const res = await fetchAdminApi('payment-config', 'POST', payload);
        if (res.success) {
          if (typeof window.showToast === 'function') {
            window.showToast('🏦 Đã lưu Tài Khoản Ngân Hàng nhận tiền thật của bạn thành công!', 'success');
          }
          refreshAdminOverviewIfUnlocked();
        } else if (typeof window.showToast === 'function') {
          window.showToast(res.error || 'Lỗi lưu cấu hình ngân hàng', 'error');
        }
      });
    }
  }

  document.addEventListener('DOMContentLoaded', () => {
    setupCustomerLicenseModal();
    setupAdminDashboardEvents();
    setupPaymentAndBankEvents();
    syncClientLicenseStatus(false);
  });
})();

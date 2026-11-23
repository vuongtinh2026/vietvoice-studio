/**
 * VoiceViet Studio Pro v7.0 — Enterprise License Key, HWID Lock & Remote Quota Engine
 *
 * Features:
 * 1. Real Hardware Motherboard / OS Fingerprinting (macOS IOPlatformUUID, Windows MachineGuid/UUID, Linux machine-id)
 * 2. Server-Side Persistent License & HWID Trial Database (`license_db/licenses.json`, mode 0600)
 * 3. Strict 1-Key-1-PC Hardware Lock (`boundHwid`) + Remote Lock/Unlock + Expiry + Character Quota Deduction
 * 4. Anti-Incognito Free Trial Lock (100,000 chars tied to physical HWID on server, immune to browser data clearing)
 * 5. One-Click Clean & Obfuscated Customer Package Exporter (`dist_customer_package/`) — 0% Private Voices leaked
 */

import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import crypto from 'node:crypto';
import { execSync } from 'node:child_process';

const PLAN_CONFIGS = {
  free: {
    id: 'free',
    nameVi: 'Gói Miễn Phí',
    nameEn: 'Free Trial',
    maxChars: 100000,
    unlimited: false,
    priceVnd: 0,
    defaultDays: 30
  },
  basic: {
    id: 'basic',
    nameVi: 'Gói Thường (25.000đ)',
    nameEn: 'Basic Creator ($1.99)',
    maxChars: 1000000,
    unlimited: false,
    priceVnd: 25000,
    defaultDays: 30
  },
  standard: {
    id: 'standard',
    nameVi: 'Gói Phổ Thông (75.000đ)',
    nameEn: 'Standard Pro ($4.99)',
    maxChars: 10000000,
    unlimited: false,
    priceVnd: 75000,
    defaultDays: 30
  },
  vip: {
    id: 'vip',
    nameVi: 'Gói VIP (150.000đ)',
    nameEn: 'VIP Studio ($9.99)',
    maxChars: 100000000,
    unlimited: false,
    priceVnd: 150000,
    defaultDays: 30
  },
  unlimited: {
    id: 'unlimited',
    nameVi: 'Gói Không Giới Hạn (299.000đ)',
    nameEn: 'Unlimited Enterprise ($19.99)',
    maxChars: 999999999999,
    unlimited: true,
    priceVnd: 299000,
    defaultDays: 30
  }
};

let cachedLocalHwid = null;
let cachedMachineLabel = null;

/**
 * Generates an unforgeable Hardware ID (HWID) from physical OS/Motherboard UUID + CPU + Architecture
 */
export function getLocalMachineHardwareInfo() {
  if (cachedLocalHwid && cachedMachineLabel) {
    return { hwid: cachedLocalHwid, machineLabel: cachedMachineLabel };
  }

  let rawSerial = '';
  const platform = os.platform();
  const arch = os.arch();
  const hostname = os.hostname() || 'Unknown-PC';
  const cpuModel = (os.cpus()?.[0]?.model || 'CPU').trim();

  try {
    if (platform === 'darwin') {
      const out = execSync('ioreg -rd1 -c IOPlatformExpertDevice', { encoding: 'utf8', timeout: 2500 });
      const m = out.match(/"IOPlatformUUID"\s*=\s*"([^"]+)"/);
      if (m && m[1]) rawSerial = m[1].trim();
    } else if (platform === 'win32') {
      const out = execSync('reg query "HKLM\\SOFTWARE\\Microsoft\\Cryptography" /v MachineGuid', { encoding: 'utf8', timeout: 2500 });
      const m = out.match(/MachineGuid\s+REG_SZ\s+([^\r\n]+)/i);
      if (m && m[1]) rawSerial = m[1].trim();
    } else {
      if (fs.existsSync('/etc/machine-id')) {
        rawSerial = fs.readFileSync('/etc/machine-id', 'utf8').trim();
      } else if (fs.existsSync('/var/lib/dbus/machine-id')) {
        rawSerial = fs.readFileSync('/var/lib/dbus/machine-id', 'utf8').trim();
      }
    }
  } catch {
    // Fallback to deterministic hardware traits
  }

  if (!rawSerial) {
    const netMacs = Object.values(os.networkInterfaces() || {})
      .flat()
      .filter(i => i && !i.internal && i.mac && i.mac !== '00:00:00:00:00:00')
      .map(i => i.mac)
      .sort()
      .join('|');
    rawSerial = `${hostname}|${platform}|${arch}|${cpuModel}|${netMacs}`;
  }

  const digest = crypto
    .createHash('sha256')
    .update(`VOICEVIET_HWID_V7::${rawSerial}::${platform}::${arch}`)
    .digest('hex')
    .toUpperCase();

  cachedLocalHwid = `HWID-${digest.slice(0, 4)}-${digest.slice(4, 8)}-${digest.slice(8, 12)}`;
  const osFriendly = platform === 'darwin' ? 'macOS' : (platform === 'win32' ? 'Windows' : 'Linux');
  cachedMachineLabel = `${hostname} (${osFriendly} ${arch})`;

  return { hwid: cachedLocalHwid, machineLabel: cachedMachineLabel };
}

export function createLicenseManager(baseDir) {
  const dbDir = path.join(baseDir, 'license_db');
  const dbPath = path.join(dbDir, 'licenses.json');
  const clientConfigPath = path.join(baseDir, 'client_config.json');

  // Detect if this copy is an exported Customer Client Build
  function getClientConfig() {
    try {
      if (fs.existsSync(clientConfigPath)) {
        return JSON.parse(fs.readFileSync(clientConfigPath, 'utf8'));
      }
    } catch {}
    return { isCustomerClient: false, licenseServerUrl: '' };
  }

  function ensureDbLoaded() {
    if (!fs.existsSync(dbDir)) {
      fs.mkdirSync(dbDir, { recursive: true, mode: 0o700 });
    }
    if (!fs.existsSync(dbPath)) {
      const seedKey = 'VVPRO-VIP8-8888-DEMO';
      const now = Date.now();
      const initialDb = {
        version: '7.0',
        settings: {
          allowFreeHwidTrial: true,
          freeTrialCharsPerMachine: 100000
        },
        licenses: {
          [seedKey]: {
            key: seedKey,
            customerName: 'Khách Hàng Mẫu (Test Gói Thường 1M)',
            customerContact: '0909.xxx.xxx (Zalo)',
            planId: 'basic',
            planName: PLAN_CONFIGS.basic.nameVi,
            priceVnd: 25000,
            maxChars: 1000000,
            unlimited: false,
            usedChars: 0,
            status: 'active',
            maxDevices: 1,
            boundHwid: null,
            boundMachineLabel: null,
            boundAt: null,
            createdAt: now,
            expiresAt: now + 30 * 86400 * 1000,
            totalRequests: 0,
            lastUsedAt: null,
            lastIp: null
          }
        },
        hwidTrials: {}
      };
      saveDb(initialDb);
      return initialDb;
    }
    try {
      const raw = JSON.parse(fs.readFileSync(dbPath, 'utf8'));
      if (!raw.licenses) raw.licenses = {};
      if (!raw.hwidTrials) raw.hwidTrials = {};
      if (!raw.settings) raw.settings = { allowFreeHwidTrial: true, freeTrialCharsPerMachine: 100000 };
      return raw;
    } catch {
      return {
        version: '7.0',
        settings: { allowFreeHwidTrial: true, freeTrialCharsPerMachine: 100000 },
        licenses: {},
        hwidTrials: {}
      };
    }
  }

  let db = ensureDbLoaded();

  function saveDb(nextDb = db) {
    if (!fs.existsSync(dbDir)) {
      fs.mkdirSync(dbDir, { recursive: true, mode: 0o700 });
    }
    const tmp = `${dbPath}.tmp`;
    fs.writeFileSync(tmp, JSON.stringify(nextDb, null, 2), { encoding: 'utf8', mode: 0o600 });
    fs.renameSync(tmp, dbPath);
  }

  function generateRandomKey(planId = 'basic') {
    const prefixMap = {
      free: 'VVFREE',
      basic: 'VVBAS',
      standard: 'VVSTD',
      vip: 'VVVIP',
      unlimited: 'VVUNL'
    };
    const pref = prefixMap[planId] || 'VVPRO';
    const seg = () => crypto.randomBytes(2).toString('hex').toUpperCase();
    return `${pref}-${seg()}-${seg()}-${seg()}`;
  }

  function getOrInitHwidTrial(hwid, machineLabel = '') {
    const cleanHwid = (hwid || getLocalMachineHardwareInfo().hwid).trim().toUpperCase();
    const now = Date.now();
    const thirtyDays = 30 * 86400 * 1000;
    if (!db.hwidTrials[cleanHwid]) {
      db.hwidTrials[cleanHwid] = {
        hwid: cleanHwid,
        machineLabel: machineLabel || 'Thiết bị dùng thử',
        maxChars: db.settings.freeTrialCharsPerMachine || 100000,
        usedChars: 0,
        periodStartMs: now,
        firstSeenAt: now,
        lastUsedAt: now
      };
      saveDb();
    } else {
      const rec = db.hwidTrials[cleanHwid];
      if (now - (rec.periodStartMs || 0) >= thirtyDays) {
        rec.usedChars = 0;
        rec.periodStartMs = now;
        saveDb();
      }
    }
    return db.hwidTrials[cleanHwid];
  }

  /**
   * Validates a License Key + HWID (without deducting characters)
   * If `bindOnFirstUse` is true, locks `boundHwid` to this machine on first activation!
   */
  function inspectOrActivateStatus({ licenseKey = '', hwid = '', machineLabel = '', clientIp = '', bindOnFirstUse = false }) {
    const hwInfo = getLocalMachineHardwareInfo();
    const effectiveHwid = (hwid || hwInfo.hwid).trim().toUpperCase();
    const effectiveLabel = (machineLabel || hwInfo.machineLabel).trim();
    const normKey = (licenseKey || '').trim().toUpperCase();

    // Case A: User provided a License Key
    if (normKey) {
      const lic = db.licenses[normKey];
      if (!lic) {
        return {
          ok: false,
          code: 'INVALID_KEY',
          status: 401,
          error: `Mã bản quyền "${normKey}" không tồn tại! Vui lòng kiểm tra lại.`
        };
      }
      if (lic.status === 'locked') {
        return {
          ok: false,
          code: 'KEY_LOCKED',
          status: 403,
          error: `Mã bản quyền "${normKey}" đã bị Quản trị viên KHÓA từ xa! Vui lòng liên hệ chủ phần mềm.`
        };
      }
      if (lic.expiresAt && Date.now() > lic.expiresAt) {
        return {
          ok: false,
          code: 'KEY_EXPIRED',
          status: 403,
          error: `Mã bản quyền "${normKey}" đã HẾT HẠN sử dụng! Vui lòng gia hạn gói mới.`
        };
      }

      // HWID 1-Machine Lock Check!
      if (lic.boundHwid && lic.boundHwid !== effectiveHwid) {
        return {
          ok: false,
          code: 'HWID_MISMATCH',
          status: 403,
          boundTo: lic.boundMachineLabel || lic.boundHwid,
          attemptedHwid: effectiveHwid,
          error: `🚫 CHẶN DÙNG CHÙA NHIỀU MÁY: Mã Key "${normKey}" đã khóa cứng cố định với máy tính [${lic.boundMachineLabel || lic.boundHwid}]. Không thể kích hoạt trên máy thứ 2 (${effectiveHwid})!`
        };
      }

      if (!lic.boundHwid && bindOnFirstUse) {
        lic.boundHwid = effectiveHwid;
        lic.boundMachineLabel = effectiveLabel;
        lic.boundAt = Date.now();
        lic.lastIp = clientIp || lic.lastIp;
        saveDb();
      }

      const remaining = lic.unlimited ? Infinity : Math.max(0, lic.maxChars - (lic.usedChars || 0));
      const daysLeft = lic.expiresAt ? Math.max(0, Math.ceil((lic.expiresAt - Date.now()) / (86400 * 1000))) : 30;

      return {
        ok: true,
        mode: 'licensed',
        key: lic.key,
        customerName: lic.customerName,
        planId: lic.planId,
        planName: lic.planName,
        unlimited: Boolean(lic.unlimited),
        maxChars: lic.maxChars,
        usedChars: lic.usedChars || 0,
        remainingChars: lic.unlimited ? null : remaining,
        boundHwid: lic.boundHwid || effectiveHwid,
        boundMachineLabel: lic.boundMachineLabel || effectiveLabel,
        hwid: effectiveHwid,
        machineLabel: effectiveLabel,
        expiresAt: lic.expiresAt,
        daysLeft
      };
    }

    // Case B: No License Key -> Use Server-Side HWID-Locked Free Trial (if enabled by Owner!)
    if (!db.settings.allowFreeHwidTrial) {
      return {
        ok: false,
        code: 'LICENSE_REQUIRED',
        status: 401,
        hwid: effectiveHwid,
        error: 'Chủ phần mềm đã tắt chế độ dùng thử miễn phí. Vui lòng nhập Mã Bản Quyền (License Key) để sử dụng!'
      };
    }

    const trial = getOrInitHwidTrial(effectiveHwid, effectiveLabel);
    const remaining = Math.max(0, trial.maxChars - (trial.usedChars || 0));
    return {
      ok: true,
      mode: 'hwid_trial',
      key: '',
      customerName: 'Dùng Thử Theo Mã Máy (1 Máy Duy Nhất)',
      planId: 'free',
      planName: 'Gói Miễn Phí (Khóa HWID)',
      unlimited: false,
      maxChars: trial.maxChars,
      usedChars: trial.usedChars || 0,
      remainingChars: remaining,
      boundHwid: effectiveHwid,
      boundMachineLabel: trial.machineLabel,
      hwid: effectiveHwid,
      machineLabel: effectiveLabel,
      expiresAt: (trial.periodStartMs || Date.now()) + 30 * 86400 * 1000,
      daysLeft: 30
    };
  }

  /**
   * Pre-check + Deduct characters atomically on the Server!
   */
  function authorizeAndConsume({ licenseKey = '', hwid = '', machineLabel = '', clientIp = '', chars = 0, dryRun = false }) {
    const status = inspectOrActivateStatus({
      licenseKey,
      hwid,
      machineLabel,
      clientIp,
      bindOnFirstUse: true
    });

    if (!status.ok) return status;

    const cost = Math.max(0, Math.round(Number(chars) || 0));
    if (!status.unlimited && cost > (status.remainingChars ?? 0)) {
      return {
        ok: false,
        code: 'QUOTA_EXCEEDED',
        status: 402,
        hwid: status.hwid,
        remainingChars: status.remainingChars,
        error: `Hết hạn mức ký tự trên Server! Cần ${cost.toLocaleString('vi-VN')} ký tự nhưng máy/Key của bạn chỉ còn ${(status.remainingChars || 0).toLocaleString('vi-VN')} ký tự. Vui lòng nâng cấp hoặc mua mã Key mới!`
      };
    }

    if (!dryRun && cost > 0) {
      const now = Date.now();
      if (status.mode === 'licensed') {
        const lic = db.licenses[status.key];
        lic.usedChars = (lic.usedChars || 0) + cost;
        lic.totalRequests = (lic.totalRequests || 0) + 1;
        lic.lastUsedAt = now;
        lic.lastIp = clientIp || lic.lastIp;
        saveDb();
        status.usedChars = lic.usedChars;
        status.remainingChars = lic.unlimited ? null : Math.max(0, lic.maxChars - lic.usedChars);
      } else {
        const trial = getOrInitHwidTrial(status.hwid, status.machineLabel);
        trial.usedChars = (trial.usedChars || 0) + cost;
        trial.lastUsedAt = now;
        saveDb();
        status.usedChars = trial.usedChars;
        status.remainingChars = Math.max(0, trial.maxChars - trial.usedChars);
      }
    }

    return status;
  }

  // =========================================================================
  // ADMIN OPERATIONS (PROTECTED BY OWNER PIN TOKEN!)
  // =========================================================================
  function adminListOverview() {
    const list = Object.values(db.licenses).sort((a, b) => (b.createdAt || 0) - (a.createdAt || 0));
    const trials = Object.values(db.hwidTrials).sort((a, b) => (b.lastUsedAt || 0) - (a.lastUsedAt || 0));
    let totalRevenueVnd = 0;
    let totalCharsConsumed = 0;
    let boundDevicesCount = 0;

    list.forEach(l => {
      totalRevenueVnd += Number(l.priceVnd) || 0;
      totalCharsConsumed += Number(l.usedChars) || 0;
      if (l.boundHwid) boundDevicesCount += 1;
    });
    trials.forEach(t => {
      totalCharsConsumed += Number(t.usedChars) || 0;
    });

    return {
      settings: db.settings,
      localMachine: getLocalMachineHardwareInfo(),
      stats: {
        totalKeys: list.length,
        activeKeys: list.filter(l => l.status === 'active').length,
        boundDevicesCount,
        trialMachinesCount: trials.length,
        totalCharsConsumed,
        totalRevenueVnd
      },
      licenses: list,
      trials: trials.slice(0, 50)
    };
  }

  function adminCreateLicense({ customerName = '', customerContact = '', planId = 'basic', durationDays = 30, customMaxChars = null }) {
    const plan = PLAN_CONFIGS[planId] || PLAN_CONFIGS.basic;
    let key = generateRandomKey(plan.id);
    while (db.licenses[key]) key = generateRandomKey(plan.id);

    const now = Date.now();
    const days = Math.max(1, Math.min(3650, Number(durationDays) || plan.defaultDays));
    const maxChars = customMaxChars && Number(customMaxChars) > 0 ? Number(customMaxChars) : plan.maxChars;

    const record = {
      key,
      customerName: (customerName || 'Khách hàng mới').trim(),
      customerContact: (customerContact || '').trim(),
      planId: plan.id,
      planName: plan.nameVi,
      priceVnd: plan.priceVnd,
      maxChars,
      unlimited: Boolean(plan.unlimited),
      usedChars: 0,
      status: 'active',
      maxDevices: 1,
      boundHwid: null,
      boundMachineLabel: null,
      boundAt: null,
      createdAt: now,
      expiresAt: now + days * 86400 * 1000,
      totalRequests: 0,
      lastUsedAt: null,
      lastIp: null
    };

    db.licenses[key] = record;
    saveDb();
    return record;
  }

  function adminMutateLicense({ key, action, addChars = 0, addDays = 0, planId = '' }) {
    const normKey = (key || '').trim().toUpperCase();
    const lic = db.licenses[normKey];
    if (!lic) {
      throw new Error(`Không tìm thấy Key: ${normKey}`);
    }

    if (action === 'lock') {
      lic.status = 'locked';
    } else if (action === 'unlock') {
      lic.status = 'active';
    } else if (action === 'reset_hwid') {
      lic.boundHwid = null;
      lic.boundMachineLabel = null;
      lic.boundAt = null;
    } else if (action === 'reset_used') {
      lic.usedChars = 0;
    } else if (action === 'topup') {
      if (Number(addChars) > 0) {
        lic.maxChars = (lic.maxChars || 0) + Number(addChars);
      }
      if (Number(addDays) > 0) {
        const base = Math.max(Date.now(), lic.expiresAt || Date.now());
        lic.expiresAt = base + Number(addDays) * 86400 * 1000;
      }
      if (planId && PLAN_CONFIGS[planId]) {
        const p = PLAN_CONFIGS[planId];
        lic.planId = p.id;
        lic.planName = p.nameVi;
        lic.unlimited = p.unlimited;
        lic.maxChars = p.maxChars;
        lic.priceVnd = (lic.priceVnd || 0) + p.priceVnd;
      }
    } else if (action === 'delete') {
      delete db.licenses[normKey];
      saveDb();
      return { deleted: true, key: normKey };
    } else {
      throw new Error(`Hành động không hợp lệ: ${action}`);
    }

    saveDb();
    return lic;
  }

  function adminUpdateSettings({ allowFreeHwidTrial, freeTrialCharsPerMachine }) {
    if (typeof allowFreeHwidTrial === 'boolean') {
      db.settings.allowFreeHwidTrial = allowFreeHwidTrial;
    }
    if (Number(freeTrialCharsPerMachine) >= 0) {
      db.settings.freeTrialCharsPerMachine = Math.round(Number(freeTrialCharsPerMachine));
    }
    saveDb();
    return db.settings;
  }

  // =========================================================================
  // ONE-CLICK CLEAN & OBFUSCATED CUSTOMER PACKAGE BUILDER
  // =========================================================================
  function obfuscateFrontendJs(jsCode) {
    // Strip multi-line comments & encode payload into self-executing base64 UTF-8 loader
    // Prevents casual customers from opening JS files in Notepad and editing UI/Quota variables!
    const b64 = Buffer.from(jsCode, 'utf8').toString('base64');
    return `/* VoiceViet Protected Client Runtime v7.0 - Unauthorized modification prohibited */\n(function(){const b=atob("${b64}");const u=new Uint8Array(b.length);for(let i=0;i<b.length;i++)u[i]=b.charCodeAt(i);(0,eval)(new TextDecoder("utf-8").decode(u));})();\n`;
  }

  function buildCustomerPackage({ licenseServerUrl = 'http://YOUR_SERVER_IP:3000' }) {
    const outDir = path.join(baseDir, 'dist_customer_package', 'VoiceViet_Client_Pro');
    if (fs.existsSync(outDir)) {
      fs.rmSync(outDir, { recursive: true, force: true });
    }
    fs.mkdirSync(outDir, { recursive: true });

    const cleanUrl = (licenseServerUrl || 'http://127.0.0.1:3000').trim().replace(/\/+$/, '');

    // 1. Copy safe runtime files ONLY (NEVER copy private_voices, license_db, private_vault enrollment data, or .git!)
    const plainCopyFiles = [
      'package.json',
      'server.js',
      'license_manager.js',
      'engine_free.py',
      'engine_pro.py',
      'global_voices_catalog.py',
      'private_vault.py',
      'style.css',
      'index.html',
      'mammoth.browser.min.js'
    ];

    for (const f of plainCopyFiles) {
      const src = path.join(baseDir, f);
      if (fs.existsSync(src)) {
        fs.copyFileSync(src, path.join(outDir, f));
      }
    }

    // 2. Obfuscate / Encode all Frontend JS Logic files in the customer package!
    const protectedJsFiles = [
      'quota_and_i18n.js',
      'app.js',
      'studio_pro.js',
      'license_client_ui.js'
    ];

    for (const jf of protectedJsFiles) {
      const src = path.join(baseDir, jf);
      if (fs.existsSync(src)) {
        const rawJs = fs.readFileSync(src, 'utf8');
        fs.writeFileSync(path.join(outDir, jf), obfuscateFrontendJs(rawJs), 'utf8');
      }
    }

    // 3. Write locked client_config.json pointing to Owner's Master License Server
    const clientCfg = {
      isCustomerClient: true,
      licenseServerUrl: cleanUrl,
      builtAt: new Date().toISOString(),
      note: 'Protected Customer Client — Every synthesis verifies License Key + Hardware ID against Master Server.'
    };
    fs.writeFileSync(path.join(outDir, 'client_config.json'), JSON.stringify(clientCfg, null, 2), 'utf8');

    // 4. Create 1-Click Launchers for Windows (.bat) & macOS (.command) + Customer Readme
    const winBat = `@echo off
chcp 65001 >nul
title VoiceViet Studio Pro - Ban Cai Dat Khach Hang
echo ==========================================================
echo   VOICEVIET STUDIO PRO - KHOI DONG PHONG THU AI 48KHZ
echo ==========================================================
if not exist node_modules (
  echo [1/2] Dang cai dat thu vien lan dau...
  call npm install --omit=dev
)
echo [2/2] Dang mo giao dien tai http://localhost:3000 ...
start "" "http://localhost:3000"
node server.js
pause
`;
    fs.writeFileSync(path.join(outDir, '1_Chay_VoiceViet_Windows.bat'), winBat, 'utf8');

    const macCmd = `#!/bin/bash
cd "$(dirname "$0")"
echo "=========================================================="
echo "  VOICEVIET STUDIO PRO - KHỞI ĐỘNG PHÒNG THU AI 48KHZ"
echo "=========================================================="
if [ ! -d "node_modules" ]; then
  echo "[1/2] Đang cài đặt thư viện lần đầu..."
  npm install --omit=dev
fi
(sleep 2 && open "http://localhost:3000") &
node server.js
`;
    const macCmdPath = path.join(outDir, '1_Chay_VoiceViet_MacOS.command');
    fs.writeFileSync(macCmdPath, macCmd, { encoding: 'utf8', mode: 0o755 });

    const readmeTxt = `====================================================================
HƯỚNG DẪN CÀI ĐẶT & KÍCH HOẠT VOICEVIET STUDIO PRO (BẢN MÁY KHÁCH)
====================================================================

1. YÊU CẦU: Máy tính có kết nối Internet (để xác thực Mã Bản Quyền), đã cài Node.js & Python 3.
2. CÁCH MỞ PHẦN MỀM:
   - Trên Windows: Nhấp đúp vào file "1_Chay_VoiceViet_Windows.bat"
   - Trên MacBook: Nhấp đúp vào file "1_Chay_VoiceViet_MacOS.command"
3. KÍCH HOẠT MÃ BẢN QUYỀN (LICENSE KEY):
   - Khi trình duyệt mở http://localhost:3000, bấm nút "🔑 Nhập Key Bản Quyền" góc trên bên phải.
   - Dán mã Key (VV...-XXXX-XXXX-XXXX) do Chủ Phần Mềm cấp vào và bấm Kích Hoạt!
   - Lưu ý: Mỗi Mã Key tự động khóa cứng với 01 máy tính duy nhất (HWID Lock).
     Nếu đổi máy tính mới, vui lòng liên hệ Quản trị viên để được hỗ trợ gỡ mã máy cũ.
====================================================================
`;
    fs.writeFileSync(path.join(outDir, 'HUONG_DAN_KHACH_HANG.txt'), readmeTxt, 'utf8');

    return {
      outDir,
      licenseServerUrl: cleanUrl,
      filesCount: fs.readdirSync(outDir).length,
      excludedPrivateVault: !fs.existsSync(path.join(outDir, 'private_voices')),
      excludedMasterLicenseDb: !fs.existsSync(path.join(outDir, 'license_db'))
    };
  }

  return {
    PLAN_CONFIGS,
    getClientConfig,
    getLocalMachineHardwareInfo,
    inspectOrActivateStatus,
    authorizeAndConsume,
    adminListOverview,
    adminCreateLicense,
    adminMutateLicense,
    adminUpdateSettings,
    buildCustomerPackage
  };
}

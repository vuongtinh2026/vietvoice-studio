/**
 * VoiceViet - Local Server with Cheap-TTS Backend & Rate-Limit Shield
 */

import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { execFile, spawn } from 'node:child_process';
import { CheapTts, CheapTtsApiError } from '@cheap-tts/node';
import { createLicenseManager } from './license_manager.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const licenseMgr = createLicenseManager(__dirname);

const PORT = process.env.PORT || 3000;
const DEFAULT_KEY = process.env.CHEAP_TTS_KEY || 'sk_live_I_cohehhbgkJqZjJiB-JifshNNcIgSCumq07SIpMsIQ';

function resolvePythonBin() {
  const isWin = process.platform === 'win32';
  const venvMac = path.join(__dirname, 'venv', 'bin', 'python3');
  const venvWin = path.join(__dirname, 'venv', 'Scripts', 'python.exe');
  const embedWin = path.join(__dirname, 'python_embed', 'python.exe');

  if (isWin) {
    if (fs.existsSync(embedWin)) return embedWin;
    if (fs.existsSync(venvWin)) return venvWin;
    return 'python';
  } else {
    if (fs.existsSync(venvMac)) return venvMac;
    return 'python3';
  }
}

const PYTHON_BIN = resolvePythonBin();
const ENGINE_PRO_SCRIPT = path.join(__dirname, 'engine_pro.py');
const ENGINE_FREE_SCRIPT = path.join(__dirname, 'engine_free.py');

let cachedTts = null;
let currentKey = DEFAULT_KEY;

function getTtsClient(key) {
  const activeKey = key || currentKey;
  if (!cachedTts || currentKey !== activeKey) {
    if (cachedTts) {
      cachedTts.destroy().catch(() => {});
    }
    cachedTts = new CheapTts({ secretKey: activeKey, telemetry: false });
    currentKey = activeKey;
  }
  return cachedTts;
}

const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));

/**
 * Fetch voices catalog using Python SDK 0.3.0+ (includes all 24 new Pro Vietnamese voices)
 */
let cachedPythonVoices = null;

function getVoicesWithPython(key) {
  return new Promise((resolve, reject) => {
    if (cachedPythonVoices && cachedPythonVoices.length > 0) {
      return resolve(cachedPythonVoices);
    }
    const py = spawn(PYTHON_BIN, [ENGINE_PRO_SCRIPT, 'voices', key || DEFAULT_KEY], {
      cwd: __dirname
    });
    let out = '';
    let err = '';
    py.stdout.on('data', d => { out += d; });
    py.stderr.on('data', d => { err += d; });
    py.on('error', (err) => {
      if (err.code === 'ENOENT') {
        return reject(new Error('Chưa tìm thấy môi trường Python trên máy để chạy giọng AI Pro. Vui lòng cài Python (hoặc chạy cai_dat_tu_dong.bat) hoặc chọn giọng Tiêu Chuẩn để sử dụng ngay.'));
      }
      reject(err);
    });
    py.on('close', code => {
      if (code !== 0) return reject(new Error(err || `Python voices exited with ${code}`));
      try {
        const data = JSON.parse(out);
        cachedPythonVoices = data.voices || [];
        resolve(cachedPythonVoices);
      } catch (e) {
        reject(e);
      }
    });
  });
}

/**
 * Synthesizes a chunk using the Python SDK 0.3.0+ engine (Pro voices support)
 */
function synthesizeWithPython(text, voice, rate = 1.0, key = DEFAULT_KEY) {
  return new Promise((resolve, reject) => {
    const py = spawn(PYTHON_BIN, [ENGINE_PRO_SCRIPT], {
      cwd: __dirname
    });
    const chunks = [];
    const errChunks = [];

    py.stdout.on('data', d => chunks.push(d));
    py.stderr.on('data', d => errChunks.push(d));
    py.on('error', (err) => {
      if (err.code === 'ENOENT') {
        return reject(new Error('Chưa tìm thấy môi trường Python trên máy để chạy giọng AI Pro. Vui lòng cài Python (hoặc chạy cai_dat_tu_dong.bat) hoặc chọn giọng Tiêu Chuẩn để sử dụng ngay.'));
      }
      reject(err);
    });

    py.on('close', code => {
      if (code !== 0) {
        const errMsg = Buffer.concat(errChunks).toString('utf-8');
        return reject(new Error(errMsg || `Python engine exited with code ${code}`));
      }
      const audio = Buffer.concat(chunks);
      // WAV duration: (pcm bytes) / (sample_rate * 2)
      const dataSize = Math.max(0, audio.length - 44);
      const sampleRate = audio.length >= 28 ? audio.readUInt32LE(24) : 48000;
      const seconds = dataSize / (sampleRate * 2);
      resolve({ audio, seconds, voice: { id: voice, name: voice } });
    });

    py.stdin.write(JSON.stringify({ text, voice, rate, key }));
    py.stdin.end();
  });
}

/**
 * Free Engine v3.0 (48kHz Studio Pro Warm Daemon + Piper Offline + Edge Neural + Google)
 */
const FREE_DAEMON_PORT = process.env.FREE_DAEMON_PORT || 3099;
let freeDaemonProc = null;
let cachedFreeVoices = null;

function startFreeDaemon() {
  if (freeDaemonProc) return;
  try {
    freeDaemonProc = spawn(PYTHON_BIN, [ENGINE_FREE_SCRIPT, 'daemon', String(FREE_DAEMON_PORT)], {
      cwd: __dirname,
      stdio: ['ignore', 'ignore', 'inherit']
    });
    freeDaemonProc.on('exit', (code) => {
      console.warn(`[Free Daemon] Exited with code ${code}. Auto-restarting in 2s...`);
      freeDaemonProc = null;
      setTimeout(startFreeDaemon, 2000);
    });
  } catch (err) {
    console.warn('[Free Daemon] Could not spawn daemon:', err.message);
  }
}

startFreeDaemon();

process.on('exit', () => {
  if (freeDaemonProc) {
    try { freeDaemonProc.kill(); } catch {}
  }
});
process.on('SIGTERM', () => {
  if (freeDaemonProc) {
    try { freeDaemonProc.kill(); } catch {}
  }
  process.exit(0);
});
process.on('SIGINT', () => {
  if (freeDaemonProc) {
    try { freeDaemonProc.kill(); } catch {}
  }
  process.exit(0);
});

async function getVoicesFree() {
  if (cachedFreeVoices && cachedFreeVoices.length > 0) {
    return cachedFreeVoices;
  }
  try {
    const res = await fetch(`http://127.0.0.1:${FREE_DAEMON_PORT}/voices`);
    if (res.ok) {
      const data = await res.json();
      if (data.voices && data.voices.length > 0) {
        cachedFreeVoices = data.voices;
        return cachedFreeVoices;
      }
    }
  } catch {}

  return new Promise((resolve, reject) => {
    const py = spawn(PYTHON_BIN, [ENGINE_FREE_SCRIPT, 'voices'], { cwd: __dirname });
    let out = '';
    let err = '';
    py.stdout.on('data', d => { out += d; });
    py.stderr.on('data', d => { err += d; });
    py.on('error', reject);
    py.on('close', code => {
      if (code !== 0) return reject(new Error(err || `Free voices exited with ${code}`));
      try {
        const data = JSON.parse(out);
        cachedFreeVoices = data.voices || [];
        resolve(cachedFreeVoices);
      } catch (e) {
        reject(e);
      }
    });
  });
}

async function synthesizeFree(text, voice, rate = 1.0, pause = 0.40, ownerToken = '') {
  // 1. Try ultra-fast warm daemon in RAM first
  try {
    const headers = { 'Content-Type': 'application/json' };
    if (ownerToken) {
      headers['X-Owner-Token'] = ownerToken;
    }
    const res = await fetch(`http://127.0.0.1:${FREE_DAEMON_PORT}/synthesize`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ text, voice, rate, pause, ownerToken: ownerToken || undefined })
    });
    if (res.ok) {
      const arrayBuf = await res.arrayBuffer();
      const audio = Buffer.from(arrayBuf);
      const dataSize = Math.max(0, audio.length - 44);
      const sampleRate = audio.length >= 28 ? audio.readUInt32LE(24) : 48000;
      const seconds = Math.max(0.2, dataSize / (sampleRate * 2));
      const found = (cachedFreeVoices || []).find(v => v.id === voice);
      const voiceName = found ? found.name : voice;
      return { audio, seconds, voice: { id: voice, name: voiceName } };
    } else {
      const errData = await res.json().catch(() => ({}));
      const e = new Error(errData.error || `Daemon HTTP ${res.status}`);
      e.status = res.status;
      e.code = errData.code || (res.status === 403 ? 'private_locked' : 'synthesis_failed');
      throw e;
    }
  } catch (daemonErr) {
    // Never bypass daemon token enforcement for private voices; only fallback to CLI if daemon is still booting for public voices
    if (
      voice.startsWith('private-') ||
      (!String(daemonErr.message || '').includes('fetch failed') && !String(daemonErr.cause?.code || '').includes('ECONNREFUSED'))
    ) {
      throw daemonErr;
    }
  }

  // 2. Fallback one-shot CLI (public voices only while daemon warms up)
  return new Promise((resolve, reject) => {
    const py = spawn(PYTHON_BIN, [ENGINE_FREE_SCRIPT], { cwd: __dirname });
    const chunks = [];
    const errChunks = [];
    py.stdout.on('data', d => chunks.push(d));
    py.stderr.on('data', d => errChunks.push(d));
    py.on('error', reject);
    py.on('close', code => {
      if (code !== 0) {
        const errMsg = Buffer.concat(errChunks).toString('utf-8').trim();
        return reject(new Error(errMsg || `Free engine exited with code ${code}`));
      }
      const audio = Buffer.concat(chunks);
      const dataSize = Math.max(0, audio.length - 44);
      const sampleRate = audio.length >= 28 ? audio.readUInt32LE(24) : 48000;
      const seconds = Math.max(0.2, dataSize / (sampleRate * 2));
      const found = (cachedFreeVoices || []).find(v => v.id === voice);
      const voiceName = found ? found.name : voice;
      resolve({ audio, seconds, voice: { id: voice, name: voiceName } });
    });
    py.stdin.write(JSON.stringify({ text, voice, rate, pause }));
    py.stdin.end();
  });
}

// Rate limit queue manager (Cheap-TTS allows ~3 requests per minute)
let lastRequestTime = 0;
const MIN_GAP_BETWEEN_REQUESTS_MS = 20000; // 20s gap between multi-chunk requests

/**
 * Chuẩn hóa văn bản theo ngôn ngữ của giọng đọc:
 * - Với giọng Tiếng Việt (vi-*, free-vi-*, private-*): phiên âm từ mượn (AI -> Ây Ai, video -> vi-đê-ô...) & sửa từ IN HOA.
 * - Với giọng Quốc tế (free-intl-* hoặc ngôn ngữ khác): giữ nguyên 100% chữ bản ngữ (Anh, Trung, Nhật, Hàn, Nga, Ả Rập...), chỉ làm sạch ký tự ẩn!
 */
function normalizeTextForVoice(text, voice = '') {
  if (!text) return '';
  const isInternational = voice.startsWith('free-intl-') || (
    voice && !voice.startsWith('vi-') && !voice.startsWith('free-vi-') && !voice.startsWith('private-')
  );
  if (isInternational) {
    return text
      .normalize('NFC')
      .replace(/[\u00a0\u200b\u200e\u200f\ufeff]/g, ' ')
      .replace(/\r\n/g, '\n')
      .replace(/[ \t]+/g, ' ')
      .trim();
  }
  return normalizeVietnameseText(text);
}

function normalizeVietnameseText(text) {
  if (!text) return '';
  let clean = text
    .normalize('NFC')
    .replace(/[\u00a0\u200b\u200e\u200f\ufeff]/g, ' ')
    .replace(/\r\n/g, '\n');

  // 1. Phiên âm các từ viết tắt / từ mượn tiếng Anh phổ biến để AI đọc tự nhiên:
  clean = clean
    .replace(/\bAI\b/g, 'Ây Ai')
    .replace(/\bVoiceViet\b/gi, 'Voi-Việt')
    .replace(/\bStudio\b/gi, 'X-tu-đi-ô')
    .replace(/\baudio\b/gi, 'ao-đi-ô')
    .replace(/\bvideo\b/gi, 'vi-đê-ô')
    .replace(/\byoutube\b/gi, 'Du-túp')
    .replace(/\btiktok\b/gi, 'Tóp-tóp')
    .replace(/\bwebsite\b/gi, 'uép-sai')
    .replace(/\bpodcast\b/gi, 'pót-cát');

  // 2. Chuyển từ IN HOA toàn bộ (ví dụ: TIÊU VIÊM, QUYẾT ĐỊNH, CHƯƠNG) thành Tiêu Viêm, Quyết Định, Chương
  // để AI không đánh vần từng chữ một (T - I - Ê - U)
  clean = clean.replace(/(?:(?<=[\s,.:;!?"'\(\)\[\]«»“”‘’—\-\n…\/~]|^))(\p{Lu}{2,})(?=(?:[\s,.:;!?"'\(\)\[\]«»“”‘’—\-\n…\/~]|$))/gu, (match) => {
    return match.charAt(0) + match.slice(1).toLowerCase();
  });

  // 3. Tách biệt tiêu đề chương để AI ngắt nghỉ đúng chỗ
  clean = clean.replace(/(Chương\s+\d+[^:\n]*):(?!\s)/gi, '$1: ');

  // 4. Chuẩn hóa khoảng trắng thừa
  clean = clean.replace(/[ \t]+/g, ' ');

  return clean.trim();
}

/**
 * Splits text into large safe chunks (up to 4,800 characters)
 * Cheap-TTS supports up to 5,000 characters per single call in ~6-7 seconds!
 * - Up to 1,000 words (~4,800 chars) = EXACTLY 1 call (ZERO sleep delay, 5-7s total!)
 * - 2,000 words = 2 calls
 */
function splitTextIntoSafeChunks(text, maxChars = 4800) {
  if (!text) return [];
  if (text.length <= maxChars) return [text.trim()];

  const paragraphs = text.split(/\n+/);
  const chunks = [];
  let currentChunk = '';

  for (const p of paragraphs) {
    const trimmedP = p.trim();
    if (!trimmedP) continue;

    const sentences = trimmedP.match(/[^.!?;\n]+[.!?;\n]+|[^.!?;\n]+$/g) || [trimmedP];

    for (const s of sentences) {
      const sentence = s.trim();
      if (!sentence) continue;

      if ((currentChunk + ' ' + sentence).trim().length <= maxChars) {
        currentChunk = (currentChunk + ' ' + sentence).trim();
      } else {
        if (currentChunk) chunks.push(currentChunk);

        if (sentence.length > maxChars) {
          const subSentences = sentence.match(/.{1,4500}(\s|$)/g) || [sentence];
          for (const sub of subSentences) {
            if (sub.trim()) chunks.push(sub.trim());
          }
          currentChunk = '';
        } else {
          currentChunk = sentence;
        }
      }
    }
  }

  if (currentChunk) chunks.push(currentChunk);
  return chunks.length > 0 ? chunks : [text];
}

/**
 * Merges multiple WAV buffers into one unified WAV buffer.
 */
function mergeWavBuffers(wavBuffers, silenceSec = 0.25, sampleRate = 22050) {
  if (wavBuffers.length === 0) return Buffer.alloc(0);
  if (wavBuffers.length === 1) return wavBuffers[0];

  const detectedSampleRate = wavBuffers[0].length >= 28 ? wavBuffers[0].readUInt32LE(24) : sampleRate;
  const silenceSamples = Math.round(silenceSec * detectedSampleRate);
  const silenceBytes = Buffer.alloc(silenceSamples * 2);

  const pcmList = [];
  let totalDataLength = 0;

  for (let i = 0; i < wavBuffers.length; i++) {
    const wav = wavBuffers[i];
    const pcm = wav.subarray(44);
    pcmList.push(pcm);
    totalDataLength += pcm.length;

    if (i < wavBuffers.length - 1 && silenceSec > 0) {
      pcmList.push(silenceBytes);
      totalDataLength += silenceBytes.length;
    }
  }

  const header = Buffer.from(wavBuffers[0].subarray(0, 44));
  header.writeUInt32LE(totalDataLength + 36, 4);
  header.writeUInt32LE(totalDataLength, 40);

  return Buffer.concat([header, ...pcmList]);
}

/**
 * Synthesizes a chunk with rate limit protection
 */
async function synthesizeWithRateLimit(tts, options) {
  const maxRetries = 3;
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      return await tts.synthesize(options);
    } catch (err) {
      const errStr = (err.message || '').toLowerCase();
      const isRateLimit = err.code === 'rate_limited' || err.status === 429 || errStr.includes('too many requests') || errStr.includes('rate_limited');
      if (isRateLimit) {
        console.warn(`[Cheap-TTS] Rate limited (attempt ${attempt}/${maxRetries}). Waiting 20s for cooldown...`);
        if (attempt < maxRetries) {
          await sleep(20000);
          continue;
        }
      }
      throw err;
    }
  }
}

// MIME types dictionary for static files
const MIME_TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'application/javascript; charset=utf-8',
  '.mjs': 'application/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.wasm': 'application/wasm',
  '.wav': 'audio/wav',
  '.mp3': 'audio/mpeg',
  '.mp4': 'video/mp4',
  '.webm': 'video/webm',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.svg': 'image/svg+xml',
  '.ico': 'image/x-icon'
};

function readJsonBody(req, maxBytes = 48 * 1024 * 1024) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    let total = 0;
    req.on('data', chunk => {
      total += chunk.length;
      if (total > maxBytes) {
        reject(new Error('Dữ liệu tải lên vượt quá giới hạn cho phép (48MB).'));
        req.destroy();
        return;
      }
      chunks.push(chunk);
    });
    req.on('end', () => {
      try {
        const raw = Buffer.concat(chunks).toString('utf-8');
        resolve(JSON.parse(raw || '{}'));
      } catch (e) {
        reject(new Error('Định dạng dữ liệu JSON không hợp lệ.'));
      }
    });
    req.on('error', reject);
  });
}

async function verifyOwnerAuthorized(ownerToken) {
  if (!ownerToken) return false;
  try {
    const r = await fetch(`http://127.0.0.1:${FREE_DAEMON_PORT}/private/status`, {
      headers: { 'X-Owner-Token': ownerToken }
    });
    if (!r.ok) return false;
    const d = await r.json().catch(() => ({}));
    return Boolean(d && d.unlocked);
  } catch {
    return false;
  }
}

function getClientIp(req) {
  const xff = req.headers['x-forwarded-for'];
  if (xff) return String(xff).split(',')[0].trim();
  return req.socket?.remoteAddress || '127.0.0.1';
}

/**
 * Enforces License Key + Hardware ID (HWID) + Server-Side Character Quota!
 * - In Customer Client Mode (`client_config.json -> isCustomerClient: true`), verifies remotely against Owner's Master Server!
 * - On Master Server, verifies & deducts directly in `license_db/licenses.json`!
 */
async function verifyAndConsumeLicenseQuota(req, payload = {}, chars = 0, dryRun = false) {
  const clientCfg = licenseMgr.getClientConfig();
  const localHw = licenseMgr.getLocalMachineHardwareInfo();
  const licenseKey = (req.headers['x-license-key'] || payload.licenseKey || '').toString().trim();

  if (clientCfg.isCustomerClient) {
    // Unforgeable: Customer Client ALWAYS sends its own OS physical HWID to Owner's Master Server!
    try {
      const r = await fetch(`${clientCfg.licenseServerUrl}/api/license/remote-verify`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          licenseKey,
          hwid: localHw.hwid,
          machineLabel: localHw.machineLabel,
          chars,
          dryRun
        })
      });
      const data = await r.json().catch(() => ({ ok: false, error: `Lỗi kết nối Máy chủ Bản quyền (${r.status})` }));
      return data;
    } catch {
      return {
        ok: false,
        code: 'LICENSE_SERVER_OFFLINE',
        status: 503,
        error: 'Không thể kết nối tới Máy Chủ Quản Lý Bản Quyền! Vui lòng kiểm tra kết nối mạng để xác thực Key.'
      };
    }
  }

  // Master Server Mode (allows simulated HWID header ONLY for Owner testing anti-2nd-PC protection!)
  const incomingHwid = (req.headers['x-simulated-hwid'] || req.headers['x-client-hwid'] || localHw.hwid).toString().trim();
  const incomingLabel = (req.headers['x-simulated-machine'] || req.headers['x-client-machine'] || localHw.machineLabel).toString().trim();
  return licenseMgr.authorizeAndConsume({
    licenseKey,
    hwid: incomingHwid,
    machineLabel: incomingLabel,
    clientIp: getClientIp(req),
    chars,
    dryRun
  });
}

function attachQuotaHeaders(headersObj, licState) {
  if (!licState || !licState.ok) return headersObj;
  headersObj['X-License-Mode'] = licState.mode || 'hwid_trial';
  headersObj['X-License-Used'] = String(licState.usedChars || 0);
  headersObj['X-License-Max'] = String(licState.maxChars || 100000);
  headersObj['X-License-Remaining'] = licState.unlimited ? 'UNLIMITED' : String(licState.remainingChars ?? 0);
  headersObj['X-License-Plan'] = encodeURIComponent(licState.planName || '');
  headersObj['X-License-Hwid'] = licState.hwid || '';
  return headersObj;
}

const server = http.createServer(async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Owner-Token, X-Audio-Bitrate, X-License-Key, X-Client-HWID, X-Client-Machine, X-Simulated-HWID, X-Simulated-Machine');
  res.setHeader('Access-Control-Expose-Headers', 'X-Audio-Seconds, X-Audio-Voice, X-Voice-Name, X-Total-Chunks, X-License-Mode, X-License-Used, X-License-Max, X-License-Remaining, X-License-Plan, X-License-Hwid');

  if (req.method === 'OPTIONS') {
    res.writeHead(204);
    res.end();
    return;
  }

  const parsedUrl = new URL(req.url, `http://${req.headers.host}`);
  const pathname = parsedUrl.pathname;

  // =========================================================================
  // 0-A. LICENSE CLIENT & REMOTE VERIFICATION ENDPOINTS (OPTION 2 SYSTEM)
  // =========================================================================
  if (pathname === '/api/license/status' && (req.method === 'GET' || req.method === 'POST')) {
    try {
      const payload = req.method === 'POST' ? await readJsonBody(req) : {};
      const clientCfg = licenseMgr.getClientConfig();
      const localHw = licenseMgr.getLocalMachineHardwareInfo();
      const keyParam = parsedUrl.searchParams.get('key') || req.headers['x-license-key'] || payload.licenseKey || '';

      if (clientCfg.isCustomerClient) {
        const r = await fetch(`${clientCfg.licenseServerUrl}/api/license/remote-verify`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            licenseKey: keyParam,
            hwid: localHw.hwid,
            machineLabel: localHw.machineLabel,
            chars: 0,
            dryRun: true
          })
        });
        const data = await r.json().catch(() => ({ ok: false, error: 'Không kết nối được Máy chủ Bản quyền' }));
        res.writeHead(r.status || 200, { 'Content-Type': 'application/json; charset=utf-8' });
        res.end(JSON.stringify({ ...data, isCustomerClient: true, localHwid: localHw.hwid, localMachineLabel: localHw.machineLabel }));
        return;
      }

      const incomingHwid = (req.headers['x-simulated-hwid'] || payload.simulatedHwid || localHw.hwid).toString().trim();
      const incomingLabel = (req.headers['x-simulated-machine'] || payload.simulatedMachine || localHw.machineLabel).toString().trim();
      const status = licenseMgr.inspectOrActivateStatus({
        licenseKey: keyParam,
        hwid: incomingHwid,
        machineLabel: incomingLabel,
        clientIp: getClientIp(req),
        bindOnFirstUse: Boolean(payload.activate && keyParam)
      });
      res.writeHead(status.ok ? 200 : (status.status || 403), { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify({
        ...status,
        isCustomerClient: false,
        localHwid: localHw.hwid,
        localMachineLabel: localHw.machineLabel
      }));
    } catch (err) {
      res.writeHead(500, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify({ ok: false, error: err.message }));
    }
    return;
  }

  if (pathname === '/api/license/remote-verify' && req.method === 'POST') {
    const clientCfg = licenseMgr.getClientConfig();
    if (clientCfg.isCustomerClient) {
      res.writeHead(403, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify({ ok: false, error: 'Endpoint chỉ dành cho Máy Chủ Chủ Sở Hữu.' }));
      return;
    }
    try {
      const payload = await readJsonBody(req);
      const result = licenseMgr.authorizeAndConsume({
        licenseKey: payload.licenseKey || '',
        hwid: payload.hwid || '',
        machineLabel: payload.machineLabel || 'Máy khách từ xa',
        clientIp: getClientIp(req),
        chars: Number(payload.chars) || 0,
        dryRun: Boolean(payload.dryRun)
      });
      res.writeHead(result.ok ? 200 : (result.status || 403), { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify(result));
    } catch (err) {
      res.writeHead(500, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify({ ok: false, error: err.message }));
    }
    return;
  }

  // =========================================================================
  // 0-A2. PAYMENT ORDER REGISTRATION & SEPAY AUTO-WEBHOOK ENDPOINTS
  // =========================================================================
  if (pathname === '/api/payment/create-order' && req.method === 'POST') {
    try {
      const payload = await readJsonBody(req);
      const clientCfg = licenseMgr.getClientConfig();
      const localHw = licenseMgr.getLocalMachineHardwareInfo();

      if (clientCfg.isCustomerClient) {
        const r = await fetch(`${clientCfg.licenseServerUrl}/api/payment/create-order`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            ...payload,
            clientHwid: localHw.hwid,
            clientMachineLabel: localHw.machineLabel
          })
        });
        const data = await r.json().catch(() => ({ success: false, error: 'Lỗi tạo đơn trên Máy chủ' }));
        res.writeHead(r.status || 200, { 'Content-Type': 'application/json; charset=utf-8' });
        res.end(JSON.stringify(data));
        return;
      }

      const order = licenseMgr.createOrder({
        planId: payload.planId || '',
        amountVnd: Number(payload.amountVnd) || 25000,
        customerName: payload.customerName || '',
        customerContact: payload.customerContact || '',
        clientHwid: payload.clientHwid || localHw.hwid,
        clientMachineLabel: payload.clientMachineLabel || localHw.machineLabel
      });
      res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify({ success: true, order }));
    } catch (err) {
      res.writeHead(400, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify({ success: false, error: err.message }));
    }
    return;
  }

  if (pathname === '/api/payment/mark-transferred' && req.method === 'POST') {
    try {
      const payload = await readJsonBody(req);
      const clientCfg = licenseMgr.getClientConfig();
      if (clientCfg.isCustomerClient) {
        const r = await fetch(`${clientCfg.licenseServerUrl}/api/payment/mark-transferred`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        const data = await r.json().catch(() => ({ success: false }));
        res.writeHead(r.status || 200, { 'Content-Type': 'application/json; charset=utf-8' });
        res.end(JSON.stringify(data));
        return;
      }

      const ord = licenseMgr.markOrderTransferred(payload);
      res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify({ success: true, order: ord }));
    } catch (err) {
      res.writeHead(400, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify({ success: false, error: err.message }));
    }
    return;
  }

  if (pathname === '/api/payment/order-status' && req.method === 'GET') {
    try {
      const code = parsedUrl.searchParams.get('code') || '';
      const clientCfg = licenseMgr.getClientConfig();
      if (clientCfg.isCustomerClient) {
        const r = await fetch(`${clientCfg.licenseServerUrl}/api/payment/order-status?code=${encodeURIComponent(code)}`);
        const data = await r.json().catch(() => ({ ok: false }));
        res.writeHead(r.status || 200, { 'Content-Type': 'application/json; charset=utf-8' });
        res.end(JSON.stringify(data));
        return;
      }

      const status = licenseMgr.getOrderStatus(code);
      res.writeHead(status.ok ? 200 : 404, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify(status));
    } catch (err) {
      res.writeHead(500, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify({ ok: false, error: err.message }));
    }
    return;
  }

  // Official SePay Bank Auto-Webhook Receiver (24/7 Hands-Free Key Issuance!)
  if (pathname === '/api/payment/sepay-webhook' && req.method === 'POST') {
    try {
      const payload = await readJsonBody(req);
      const authHdr = req.headers.authorization || '';
      const result = licenseMgr.handleSepayWebhook(payload, authHdr);
      res.writeHead(result.ok ? 200 : (result.status || 400), { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify(result));
    } catch (err) {
      res.writeHead(500, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify({ ok: false, error: err.message }));
    }
    return;
  }

  // =========================================================================
  // 0-B. OWNER-ONLY LICENSE ADMIN DASHBOARD API (REQUIRES OWNER PIN TOKEN!)
  // =========================================================================
  if (pathname.startsWith('/api/admin/licenses/')) {
    const clientCfg = licenseMgr.getClientConfig();
    if (clientCfg.isCustomerClient) {
      res.writeHead(403, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify({ success: false, error: 'Tính năng Quản trị Chủ phần mềm bị vô hiệu hóa trên bản cài đặt Máy Khách!' }));
      return;
    }

    const ownerToken = req.headers['x-owner-token'] || '';
    const isOwner = await verifyOwnerAuthorized(ownerToken);
    if (!isOwner) {
      res.writeHead(403, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify({
        success: false,
        code: 'owner_pin_required',
        error: 'Cần mở khóa Mã PIN Chủ Sở Hữu để truy cập Trung Tâm Quản Lý Key & Khách Hàng!'
      }));
      return;
    }

    try {
      const sub = pathname.replace('/api/admin/licenses/', '');
      if (sub === 'overview' && req.method === 'GET') {
        const overview = licenseMgr.adminListOverview();
        res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
        res.end(JSON.stringify({ success: true, ...overview }));
        return;
      }
      if (sub === 'create' && req.method === 'POST') {
        const body = await readJsonBody(req);
        const created = licenseMgr.adminCreateLicense(body);
        res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
        res.end(JSON.stringify({ success: true, license: created }));
        return;
      }
      if (sub === 'mutate' && req.method === 'POST') {
        const body = await readJsonBody(req);
        const updated = licenseMgr.adminMutateLicense(body);
        res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
        res.end(JSON.stringify({ success: true, result: updated }));
        return;
      }
      if (sub === 'settings' && req.method === 'POST') {
        const body = await readJsonBody(req);
        const settings = licenseMgr.adminUpdateSettings(body);
        res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
        res.end(JSON.stringify({ success: true, settings }));
        return;
      }
      if (sub === 'payment-config' && req.method === 'POST') {
        const body = await readJsonBody(req);
        const paymentConfig = licenseMgr.adminUpdatePaymentConfig(body);
        res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
        res.end(JSON.stringify({ success: true, paymentConfig }));
        return;
      }
      if (sub === 'approve-order' && req.method === 'POST') {
        const body = await readJsonBody(req);
        const approved = licenseMgr.approveOrderAndIssueKey(body.orderCode, 'admin_manual');
        res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
        res.end(JSON.stringify({ success: true, ...approved }));
        return;
      }
      if (sub === 'delete-order' && req.method === 'POST') {
        const body = await readJsonBody(req);
        const deleted = licenseMgr.cancelOrDeleteOrder(body.orderCode);
        res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
        res.end(JSON.stringify({ success: true, ...deleted }));
        return;
      }
      if (sub === 'export-package' && req.method === 'POST') {
        const body = await readJsonBody(req);
        const pkg = licenseMgr.buildCustomerPackage({
          licenseServerUrl: body.licenseServerUrl || `http://127.0.0.1:${PORT}`
        });
        res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
        res.end(JSON.stringify({ success: true, package: pkg }));
        return;
      }
      res.writeHead(404, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify({ success: false, error: 'Admin endpoint không tồn tại.' }));
    } catch (err) {
      res.writeHead(400, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify({ success: false, error: err.message }));
    }
    return;
  }

  // 0. API: Private Voice Vault (Owner-Protected Encrypted Voice Cloning)
  if (pathname.startsWith('/api/private-voices/')) {
    const subRoute = pathname.replace('/api/private-voices/', '');
    const daemonMap = {
      'status': { method: 'GET', path: '/private/status' },
      'unlock': { method: 'POST', path: '/private/unlock' },
      'lock': { method: 'POST', path: '/private/lock' },
      'change-pin': { method: 'POST', path: '/private/change-pin' },
      'enroll': { method: 'POST', path: '/private/enroll', invalidateCache: true },
      'delete': { method: 'POST', path: '/private/delete', invalidateCache: true }
    };
    const target = daemonMap[subRoute];
    if (!target || req.method !== target.method) {
      res.writeHead(404, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify({ success: false, error: 'Endpoint không tồn tại.' }));
      return;
    }

    try {
      const ownerToken = req.headers['x-owner-token'] || '';
      const headers = { 'Content-Type': 'application/json' };
      if (ownerToken) headers['X-Owner-Token'] = ownerToken;

      let fetchOpts = { method: target.method, headers };
      if (target.method === 'POST') {
        const payload = await readJsonBody(req);
        fetchOpts.body = JSON.stringify(payload);
      }

      const dRes = await fetch(`http://127.0.0.1:${FREE_DAEMON_PORT}${target.path}`, fetchOpts);
      const data = await dRes.json().catch(() => ({ success: false, error: `Daemon HTTP ${dRes.status}` }));
      if (dRes.ok && target.invalidateCache) {
        cachedFreeVoices = null;
      }
      res.writeHead(dRes.status, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify(data));
    } catch (err) {
      console.error(`[Private Vault API Error - ${subRoute}]:`, err);
      res.writeHead(500, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify({
        success: false,
        error: String(err.message || '').includes('fetch failed')
          ? 'Đang khởi động AI Engine 48kHz, vui lòng thử lại sau 2 giây!'
          : err.message
      }));
    }
    return;
  }

  // 1. API: Get Voices Catalog (includes Private Cloned Voices + 32 Global Languages + 24 Pro Vietnamese voices)
  if (pathname === '/api/cheap-tts/voices' && req.method === 'GET') {
    try {
      const keyHeader = req.headers.authorization?.replace(/^Bearer\s+/i, '');
      const activeKey = keyHeader || DEFAULT_KEY;
      let voices = [];
      try {
        voices = await getVoicesWithPython(activeKey);
      } catch (pyErr) {
        console.warn('Python voices catalog fallback to Node:', pyErr.message);
        const tts = getTtsClient(activeKey);
        voices = await tts.voices();
      }
      try {
        const freeVoices = await getVoicesFree();
        voices = [...freeVoices, ...voices];
      } catch (fErr) {
        console.warn('Could not load free voices:', fErr.message);
      }
      res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify({ success: true, voices }));
    } catch (err) {
      console.error('Error fetching voices:', err);
      res.writeHead(500, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify({ success: false, error: err.message }));
    }
    return;
  }

  // 1.1 API: List Free Open Source + Private Voices
  if (pathname === '/api/free-tts/voices' && req.method === 'GET') {
    try {
      const voices = await getVoicesFree();
      res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify({ success: true, voices }));
    } catch (err) {
      console.error('Error fetching free voices:', err);
      res.writeHead(500, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify({ success: false, error: err.message }));
    }
    return;
  }

  // 1.15 API: Ultra-Instant Voice Preview (<20ms cached, 0.4s-1.8s cold!)
  if (pathname === '/api/free-tts/preview' && req.method === 'POST') {
    try {
      const payload = await readJsonBody(req);
      const voice = payload.voice || 'free-vi-ngoc-huyen';
      const rawText = payload.text ? normalizeTextForVoice(payload.text.trim(), voice) : '';
      const rate = parseFloat(payload.rate) || 1.0;
      const ownerToken = req.headers['x-owner-token'] || payload.ownerToken || '';

      const headers = { 'Content-Type': 'application/json' };
      if (ownerToken) headers['X-Owner-Token'] = ownerToken;

      const dRes = await fetch(`http://127.0.0.1:${FREE_DAEMON_PORT}/preview`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ voice, text: rawText, rate, ownerToken: ownerToken || undefined })
      });

      if (!dRes.ok) {
        const errData = await dRes.json().catch(() => ({}));
        res.writeHead(dRes.status, { 'Content-Type': 'application/json; charset=utf-8' });
        res.end(JSON.stringify({
          success: false,
          code: errData.code || (dRes.status === 403 ? 'private_locked' : 'preview_failed'),
          error: errData.error || `Lỗi nghe thử HTTP ${dRes.status}`
        }));
        return;
      }

      const arrayBuf = await dRes.arrayBuffer();
      const audioBuf = Buffer.from(arrayBuf);
      const contentType = dRes.headers.get('content-type') || 'audio/wav';
      const secondsHdr = dRes.headers.get('x-audio-seconds') || '3.0';
      const found = (cachedFreeVoices || []).find(v => v.id === voice);

      res.writeHead(200, {
        'Content-Type': contentType,
        'Content-Length': audioBuf.length,
        'X-Audio-Seconds': secondsHdr,
        'X-Audio-Voice': voice,
        'X-Voice-Name': encodeURIComponent(found?.name || voice)
      });
      res.end(audioBuf);
    } catch (err) {
      console.error('[Preview API Error]:', err.message);
      res.writeHead(500, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify({
        success: false,
        error: String(err.message || '').includes('fetch failed')
          ? 'Đang khởi động AI Engine, vui lòng bấm lại sau 1 giây!'
          : err.message
      }));
    }
    return;
  }

  // 1.2 API: Synthesize Audio via Free Studio 48kHz / Private Clone / Global 142 Languages Engine
  if (pathname === '/api/free-tts/synthesize' && req.method === 'POST') {
    try {
      const payload = await readJsonBody(req);
      const voice = payload.voice || 'free-vi-ngoc-huyen';
      const rawText = payload.text?.trim();
      const text = normalizeTextForVoice(rawText, voice);
      const rate = parseFloat(payload.rate) || 1.0;
      const pause = payload.pauses?.sentence ? parseFloat(payload.pauses.sentence) : 0.40;
      const ownerToken = req.headers['x-owner-token'] || payload.ownerToken || '';

      if (!text) {
        res.writeHead(400, { 'Content-Type': 'application/json; charset=utf-8' });
        res.end(JSON.stringify({ success: false, error: 'Vui lòng nhập văn bản cần đọc.' }));
        return;
      }

      // 1. Pre-check License Key + HWID + Server Quota BEFORE burning CPU!
      const charCost = rawText.length;
      const preCheck = await verifyAndConsumeLicenseQuota(req, payload, charCost, true);
      if (!preCheck.ok) {
        res.writeHead(preCheck.status || 403, { 'Content-Type': 'application/json; charset=utf-8' });
        res.end(JSON.stringify({ success: false, code: preCheck.code, error: preCheck.error }));
        return;
      }

      if (!cachedFreeVoices) {
        await getVoicesFree().catch(() => {});
      }

      console.log(`[Studio 48kHz Engine] Synthesizing ${text.length} chars with voice ${voice}...`);
      const result = await synthesizeFree(text, voice, rate, pause, ownerToken);

      // 2. Commit atomic character deduction on the Server!
      const committed = await verifyAndConsumeLicenseQuota(req, payload, charCost, false);
      const respHeaders = attachQuotaHeaders({
        'Content-Type': 'audio/wav',
        'Content-Length': result.audio.length,
        'X-Audio-Seconds': result.seconds.toFixed(1),
        'X-Audio-Voice': voice,
        'X-Voice-Name': encodeURIComponent(result.voice.name || voice),
        'X-Total-Chunks': '1'
      }, committed);
      res.writeHead(200, respHeaders);
      res.end(result.audio);
    } catch (err) {
      console.error('[Studio Engine Error]:', err.message);
      res.writeHead(err.status || 500, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify({
        success: false,
        code: err.code || 'synthesis_failed',
        error: err.message
      }));
    }
    return;
  }

  // 2. API: Synthesize Audio (Unified endpoint for Batch / Chapters / Cloud / Free / Private)
  if (pathname === '/api/cheap-tts/synthesize' && req.method === 'POST') {
    try {
      const payload = await readJsonBody(req);
      const voice = payload.voice || 'free-vi-ngoc-huyen';
      const rawText = payload.text?.trim();
      const text = normalizeTextForVoice(rawText, voice);
      const rate = parseFloat(payload.rate) || 1.0;
      const pauses = payload.pauses;
      const key = payload.key || req.headers.authorization?.replace(/^Bearer\s+/i, '') || DEFAULT_KEY;
      const ownerToken = req.headers['x-owner-token'] || payload.ownerToken || '';

      if (!text) {
        res.writeHead(400, { 'Content-Type': 'application/json; charset=utf-8' });
        res.end(JSON.stringify({ success: false, error: 'Vui lòng nhập văn bản cần đọc.' }));
        return;
      }

      // 1. Pre-check License Key + HWID + Server Quota BEFORE synthesizing!
      const charCost = rawText.length;
      const preCheck = await verifyAndConsumeLicenseQuota(req, payload, charCost, true);
      if (!preCheck.ok) {
        res.writeHead(preCheck.status || 403, { 'Content-Type': 'application/json; charset=utf-8' });
        res.end(JSON.stringify({ success: false, code: preCheck.code, error: preCheck.error }));
        return;
      }

      // Support free open source & private cloned voices directly via same endpoint (returns WAV 48kHz)
      if (voice.startsWith('free-') || voice.startsWith('private-')) {
        if (!cachedFreeVoices) {
          await getVoicesFree().catch(() => {});
        }
        const pause = pauses?.sentence ? parseFloat(pauses.sentence) : 0.40;
        console.log(`[Studio Engine via Synthesize] Synthesizing ${text.length} chars (Voice: ${voice})...`);
        const result = await synthesizeFree(text, voice, rate, pause, ownerToken);
        const committed = await verifyAndConsumeLicenseQuota(req, payload, charCost, false);
        const respHeaders = attachQuotaHeaders({
          'Content-Type': 'audio/wav',
          'Content-Length': result.audio.length,
          'X-Audio-Seconds': result.seconds.toFixed(1),
          'X-Audio-Voice': voice,
          'X-Voice-Name': encodeURIComponent(result.voice.name || voice),
          'X-Total-Chunks': '1'
        }, committed);
        res.writeHead(200, respHeaders);
        res.end(result.audio);
        return;
      }

      // Allow up to 500,000 characters (~80,000 words)
      if (text.length > 500000) {
        res.writeHead(400, { 'Content-Type': 'application/json; charset=utf-8' });
        res.end(JSON.stringify({
          success: false,
          error: `Văn bản này quá lớn (${text.length.toLocaleString()} ký tự). Giới hạn tối đa là 500.000 ký tự (~80.000 từ). Vui lòng chia nhỏ thành các file hoặc chương để xử lý tốt nhất!`,
          code: 'payload_too_large'
        }));
        return;
      }

      const isProVoice = voice.startsWith('vi-pro-');
      const tts = isProVoice ? null : getTtsClient(key);

      // Pro voices accept up to 1,000 chars/call; Standard voices accept up to 4,800 chars
      const maxChunkChars = isProVoice ? 950 : 4800;
      const chunks = splitTextIntoSafeChunks(text, maxChunkChars);
      console.log(`[Cheap-TTS] Synthesizing ${text.length} chars in ${chunks.length} chunk(s) (Voice: ${voice}, Pro: ${isProVoice})...`);

      const wavBuffers = [];
      let totalSeconds = 0;
      let voiceInfo = null;

      for (let i = 0; i < chunks.length; i++) {
        const chunkText = chunks[i];
        let result;

        if (isProVoice) {
          console.log(`[Cheap-TTS Pro] Processing chunk ${i + 1}/${chunks.length} (${chunkText.length} chars) with Python engine...`);
          result = await synthesizeWithPython(chunkText, voice, rate, key);
        } else {
          console.log(`[Cheap-TTS Standard] Processing chunk ${i + 1}/${chunks.length} (${chunkText.length} chars)...`);
          const synthOptions = {
            text: chunkText,
            voice,
            rate
          };
          if (pauses) {
            synthOptions.pauses = pauses;
          }
          result = await synthesizeWithRateLimit(tts, synthOptions);
        }

        wavBuffers.push(result.audio);
        totalSeconds += result.seconds;
        voiceInfo = result.voice;

        if (i < chunks.length - 1) {
          const gap = isProVoice ? 2000 : 15000;
          console.log(`[Cheap-TTS] Waiting ${gap}ms between sub-chunks...`);
          await sleep(gap);
        }
      }

      const pauseDuration = pauses?.sentence ? parseFloat(pauses.sentence) : 0.25;
      const mergedAudio = mergeWavBuffers(wavBuffers, pauseDuration);
      console.log(`[Cheap-TTS] Finished! Generated ${totalSeconds.toFixed(1)}s audio (${mergedAudio.length} bytes).`);

      const committed = await verifyAndConsumeLicenseQuota(req, payload, charCost, false);
      const cloudHeaders = attachQuotaHeaders({
        'Content-Type': 'audio/wav',
        'Content-Length': mergedAudio.length,
        'X-Audio-Seconds': totalSeconds.toFixed(1),
        'X-Total-Chunks': chunks.length.toString(),
        'X-Voice-Name': encodeURIComponent(voiceInfo?.name || voice),
        'Content-Disposition': `attachment; filename="cheap-tts-${voice}-${Date.now()}.wav"`
      }, committed);
      res.writeHead(200, cloudHeaders);
      res.end(mergedAudio);
    } catch (err) {
      console.error('Synthesis error:', err);
      let errorMsg = err.message || 'Lỗi khi tạo giọng nói';
      if (err.code === 'rate_limited' || err.status === 429) {
        errorMsg = 'Tài khoản Cheap-TTS đang bị giới hạn tần suất gọi (3 lần/phút). Vui lòng đợi 30 giây rồi thử lại, hoặc dùng tab "AI Miễn Phí (Không giới hạn)"!';
      }
      res.writeHead(err.status || 500, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify({
        success: false,
        error: errorMsg,
        code: err.code || 'synthesis_failed'
      }));
    }
    return;
  }

  // 3. API: Convert WAV to lightweight Studio MP3 using FFmpeg (libmp3lame)
  if (pathname === '/api/audio/convert-to-mp3' && req.method === 'POST') {
    const tempId = `${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
    const tempWav = path.join('/tmp', `vietvoice_in_${tempId}.wav`);
    const tempMp3 = path.join('/tmp', `vietvoice_out_${tempId}.mp3`);

    const validBitrates = ['32k', '48k', '64k', '96k', '128k', '192k'];
    const paramBitrate = parsedUrl.searchParams ? parsedUrl.searchParams.get('bitrate') : null;
    const requestedBitrate = paramBitrate || req.headers['x-audio-bitrate'] || '48k';
    const bitrate = validBitrates.includes(requestedBitrate) ? requestedBitrate : '48k';
    const mp3SampleRate = bitrate === '32k' ? '24000' : (bitrate === '48k' ? '32000' : '48000');

    console.log(`[FFmpeg] Receiving WAV audio for MP3 conversion at ${bitrate} mono (${mp3SampleRate}Hz)...`);
    const fileStream = fs.createWriteStream(tempWav);
    req.pipe(fileStream);

    fileStream.on('finish', () => {
      const ffmpegPath = fs.existsSync('/opt/homebrew/bin/ffmpeg') ? '/opt/homebrew/bin/ffmpeg' : 'ffmpeg';

      const ffmpegArgs = [
        '-y',
        '-i', tempWav,
        '-codec:a', 'libmp3lame',
        '-b:a', bitrate,
        '-ac', '1',
        '-ar', mp3SampleRate,
        tempMp3
      ];

      execFile(ffmpegPath, ffmpegArgs, (err) => {
        if (err) {
          console.error('[FFmpeg] Conversion error:', err);
          res.writeHead(500, { 'Content-Type': 'application/json; charset=utf-8' });
          res.end(JSON.stringify({ success: false, error: 'Lỗi nén sang định dạng MP3' }));
          fs.unlink(tempWav, () => {});
          return;
        }

        fs.stat(tempMp3, (statErr, stats) => {
          if (statErr) {
            res.writeHead(500, { 'Content-Type': 'application/json; charset=utf-8' });
            res.end(JSON.stringify({ success: false, error: 'Không tìm thấy file MP3' }));
            fs.unlink(tempWav, () => {});
            return;
          }

          console.log(`[FFmpeg] MP3 conversion (${bitrate}) successful! Output size: ${(stats.size / 1024 / 1024).toFixed(2)} MB`);

          res.writeHead(200, {
            'Content-Type': 'audio/mpeg',
            'Content-Length': stats.size,
            'X-Audio-Bitrate': bitrate,
            'Content-Disposition': 'attachment; filename="voiceviet-audiobook.mp3"'
          });

          const readStream = fs.createReadStream(tempMp3);
          readStream.pipe(res);

          readStream.on('close', () => {
            fs.unlink(tempWav, () => {});
            fs.unlink(tempMp3, () => {});
          });
        });
      });
    });

    fileStream.on('error', (err) => {
      console.error('[FFmpeg] Stream error:', err);
      res.writeHead(500, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify({ success: false, error: err.message }));
    });
    return;
  }

  // 4. Static Files Delivery (with strict Vault & Source Firewall!)
  let safePath = path.normalize(pathname).replace(/^(\.\.[\/\\])+/, '');
  if (safePath === '/' || safePath === '') safePath = '/index.html';

  const lowerSafe = safePath.toLowerCase();
  if (
    lowerSafe.startsWith('/private_voices') ||
    lowerSafe.startsWith('/license_db') ||
    lowerSafe.startsWith('/dist_customer_package') ||
    lowerSafe.startsWith('/open_models') ||
    lowerSafe.startsWith('/venv') ||
    lowerSafe.startsWith('/.git') ||
    lowerSafe.startsWith('/.env') ||
    lowerSafe.endsWith('.py') ||
    lowerSafe.endsWith('vault.json') ||
    lowerSafe === '/server.js' ||
    lowerSafe === '/license_manager.js' ||
    lowerSafe === '/client_config.json' ||
    lowerSafe === '/package.json'
  ) {
    res.writeHead(403, { 'Content-Type': 'text/plain; charset=utf-8' });
    res.end('403 Forbidden - Protected Private Resource');
    return;
  }

  const filePath = path.join(__dirname, safePath);
  const ext = path.extname(filePath).toLowerCase();

  fs.stat(filePath, (err, stats) => {
    if (err || !stats.isFile()) {
      res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' });
      res.end('404 Not Found');
      return;
    }

    const contentType = MIME_TYPES[ext] || 'application/octet-stream';
    const total = stats.size;
    const range = req.headers.range;

    if (range) {
      const match = /^bytes=(\d*)-(\d*)$/.exec(range);
      if (match) {
        const start = match[1] ? parseInt(match[1], 10) : 0;
        const end = match[2] ? Math.min(parseInt(match[2], 10), total - 1) : total - 1;
        if (start >= total || start > end) {
          res.writeHead(416, { 'Content-Range': `bytes */${total}` });
          res.end();
          return;
        }
        const chunkSize = (end - start) + 1;
        res.writeHead(206, {
          'Content-Range': `bytes ${start}-${end}/${total}`,
          'Accept-Ranges': 'bytes',
          'Content-Length': chunkSize,
          'Content-Type': contentType
        });
        if (req.method === 'HEAD') {
          res.end();
          return;
        }
        fs.createReadStream(filePath, { start, end }).pipe(res);
        return;
      }
    }

    res.writeHead(200, {
      'Content-Type': contentType,
      'Content-Length': total,
      'Accept-Ranges': 'bytes'
    });
    if (req.method === 'HEAD') {
      res.end();
      return;
    }
    const stream = fs.createReadStream(filePath);
    stream.pipe(res);
  });
});

server.listen(PORT, '0.0.0.0', () => {
  console.log(`=======================================================`);
  console.log(`🎙️  VoiceViet Studio v4.0 đang chạy tại: http://0.0.0.0:${PORT}`);
  console.log(`🔒 Bảo vệ Giọng Nhân Bản Độc Quyền + 32 Ngôn Ngữ Quốc Tế`);
  console.log(`=======================================================`);
});

/**
 * VoiceViet - Local Server with Cheap-TTS Backend & Rate-Limit Shield
 */

import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { execFile, spawn } from 'node:child_process';
import { CheapTts, CheapTtsApiError } from '@cheap-tts/node';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

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

// Rate limit queue manager (Cheap-TTS allows ~3 requests per minute)
let lastRequestTime = 0;
const MIN_GAP_BETWEEN_REQUESTS_MS = 20000; // 20s gap between multi-chunk requests

/**
 * Chuẩn hóa văn bản tiếng Việt & sửa triệt để lỗi phát âm AI:
 * - Phiên âm các từ tiếng Anh / viết tắt thông dụng: AI -> Ây Ai, Studio -> X-tu-đi-ô, audio -> ao-đi-ô.
 * - Chuyển từ VIẾT HOA TOÀN BỘ (ALL CAPS >= 2 ký tự) thành Viết hoa chữ đầu (Titlecase).
 *   (Tránh trường hợp AI hiểu nhầm là từ viết tắt nên tách từng chữ ra đánh vần).
 * - Sửa lỗi nuốt âm tên riêng trước dấu chấm than (ví dụ: Chào Quân! -> Chào bạn Quân!).
 * - Xóa ký tự rác ẩn, non-breaking spaces, chuẩn hóa dấu câu.
 */
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
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.svg': 'image/svg+xml',
  '.ico': 'image/x-icon'
};

const server = http.createServer(async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');

  if (req.method === 'OPTIONS') {
    res.writeHead(204);
    res.end();
    return;
  }

  const parsedUrl = new URL(req.url, `http://${req.headers.host}`);
  const pathname = parsedUrl.pathname;

  // 1. API: Get Voices Catalog (includes all 24 new Pro Vietnamese voices)
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
      res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify({ success: true, voices }));
    } catch (err) {
      console.error('Error fetching voices:', err);
      res.writeHead(500, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify({ success: false, error: err.message }));
    }
    return;
  }

  // 2. API: Synthesize Audio
  if (pathname === '/api/cheap-tts/synthesize' && req.method === 'POST') {
    let body = '';
    req.on('data', chunk => { body += chunk; });
    req.on('end', async () => {
      try {
        const payload = JSON.parse(body || '{}');
        const rawText = payload.text?.trim();
        const text = normalizeVietnameseText(rawText);
        const voice = payload.voice || 'vi-entertainment';
        const rate = parseFloat(payload.rate) || 1.0;
        const pauses = payload.pauses;
        const key = payload.key || req.headers.authorization?.replace(/^Bearer\s+/i, '') || DEFAULT_KEY;

        if (!text) {
          res.writeHead(400, { 'Content-Type': 'application/json; charset=utf-8' });
          res.end(JSON.stringify({ success: false, error: 'Vui lòng nhập văn bản cần đọc.' }));
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

        res.writeHead(200, {
          'Content-Type': 'audio/wav',
          'Content-Length': mergedAudio.length,
          'X-Audio-Seconds': totalSeconds.toFixed(1),
          'X-Total-Chunks': chunks.length.toString(),
          'X-Voice-Name': encodeURIComponent(voiceInfo?.name || voice),
          'Content-Disposition': `attachment; filename="cheap-tts-${voice}-${Date.now()}.wav"`
        });
        res.end(mergedAudio);
      } catch (err) {
        console.error('Synthesis error:', err);
        let errorMsg = err.message || 'Lỗi khi tạo giọng nói';
        if (err.code === 'rate_limited' || err.status === 429) {
          errorMsg = 'Tài khoản Cheap-TTS đang bị giới hạn tần suất gọi (3 lần/phút). Vui lòng đợi 30 giây rồi thử lại, hoặc dùng tab "Trình duyệt (Web Speech)" để đọc không giới hạn!';
        }
        res.writeHead(err.status || 500, { 'Content-Type': 'application/json; charset=utf-8' });
        res.end(JSON.stringify({
          success: false,
          error: errorMsg,
          code: err.code || 'synthesis_failed'
        }));
      }
    });
    return;
  }

  // 3. API: Convert WAV to lightweight MP3 using FFmpeg (libmp3lame)
  if (pathname === '/api/audio/convert-to-mp3' && req.method === 'POST') {
    const tempId = `${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
    const tempWav = path.join('/tmp', `vietvoice_in_${tempId}.wav`);
    const tempMp3 = path.join('/tmp', `vietvoice_out_${tempId}.mp3`);

    // Parse requested bitrate (?bitrate=48k or header X-Audio-Bitrate: 48k)
    // Speech audio in mono (-ac 1) at 48k reduces file size by 65-70% with pristine voice clarity!
    const validBitrates = ['32k', '48k', '64k', '96k', '128k', '192k'];
    const paramBitrate = parsedUrl.searchParams ? parsedUrl.searchParams.get('bitrate') : null;
    const requestedBitrate = paramBitrate || req.headers['x-audio-bitrate'] || '48k';
    const bitrate = validBitrates.includes(requestedBitrate) ? requestedBitrate : '48k';

    console.log(`[FFmpeg] Receiving WAV audio for MP3 conversion at ${bitrate} mono...`);
    const fileStream = fs.createWriteStream(tempWav);
    req.pipe(fileStream);

    fileStream.on('finish', () => {
      const ffmpegPath = fs.existsSync('/opt/homebrew/bin/ffmpeg') ? '/opt/homebrew/bin/ffmpeg' : 'ffmpeg';
      
      // Convert to ultra-lightweight mono MP3
      const ffmpegArgs = [
        '-y',
        '-i', tempWav,
        '-codec:a', 'libmp3lame',
        '-b:a', bitrate,
        '-ac', '1',
        '-ar', '22050',
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

  // 4. Static Files Delivery
  let safePath = path.normalize(pathname).replace(/^(\.\.[\/\\])+/, '');
  if (safePath === '/' || safePath === '') safePath = '/index.html';

  const filePath = path.join(__dirname, safePath);
  const ext = path.extname(filePath).toLowerCase();

  fs.stat(filePath, (err, stats) => {
    if (err || !stats.isFile()) {
      res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' });
      res.end('404 Not Found');
      return;
    }

    const contentType = MIME_TYPES[ext] || 'application/octet-stream';
    res.writeHead(200, { 'Content-Type': contentType });
    const stream = fs.createReadStream(filePath);
    stream.pipe(res);
  });
});

server.listen(PORT, '0.0.0.0', () => {
  console.log(`=======================================================`);
  console.log(`🎙️  VoiceViet đang chạy tại: http://0.0.0.0:${PORT}`);
  console.log(`⚡ Cơ chế Rate-Limit Shield (Bảo vệ chống lỗi 429 Cheap-TTS)`);
  console.log(`=======================================================`);
});

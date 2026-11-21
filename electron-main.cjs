const { app, BrowserWindow, shell } = require('electron');
const path = require('path');
const http = require('http');
const { fork } = require('child_process');

let mainWindow = null;
let serverProcess = null;
const SERVER_PORT = process.env.PORT || 3000;

function isServerRunning(port) {
  return new Promise((resolve) => {
    const req = http.get(`http://127.0.0.1:${port}/api/cheap-tts/voices`, (res) => {
      resolve(res.statusCode === 200);
    });
    req.on('error', () => resolve(false));
    req.setTimeout(800, () => {
      req.destroy();
      resolve(false);
    });
  });
}

async function startServerIfNeeded() {
  const alreadyRunning = await isServerRunning(SERVER_PORT);
  if (alreadyRunning) {
    console.log(`[VoiceViet Desktop] Server already running at http://127.0.0.1:${SERVER_PORT}`);
    return;
  }

  console.log('[VoiceViet Desktop] Khởi động máy chủ backend nội bộ...');
  const serverPath = path.join(__dirname, 'server.js');
  serverProcess = fork(serverPath, [], {
    env: { ...process.env, PORT: SERVER_PORT.toString() },
    stdio: 'inherit'
  });
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1440,
    height: 900,
    minWidth: 1080,
    minHeight: 720,
    title: 'VoiceViet Studio Pro - Phần Mềm Đọc Giọng AI Đỉnh Cao',
    backgroundColor: '#0c0f1d',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true
    },
    autoHideMenuBar: false
  });

  const loadApp = async (retries = 25) => {
    const running = await isServerRunning(SERVER_PORT);
    if (running) {
      mainWindow.loadURL(`http://127.0.0.1:${SERVER_PORT}`);
    } else if (retries > 0) {
      setTimeout(() => loadApp(retries - 1), 400);
    } else {
      mainWindow.loadFile(path.join(__dirname, 'index.html'));
    }
  };

  loadApp();

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

app.whenReady().then(async () => {
  await startServerIfNeeded();
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (serverProcess) {
    try { serverProcess.kill(); } catch (e) {}
  }
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('before-quit', () => {
  if (serverProcess) {
    try { serverProcess.kill(); } catch (e) {}
  }
});

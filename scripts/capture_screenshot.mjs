import { spawn } from 'child_process';
import fs from 'fs';
import path from 'path';

const edgePath = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const userDataDir = path.join(process.env.TEMP || 'C:\\temp', 'cdp_user_data_' + Date.now());

// Args: url, outputPath, width, height, selectorOrScrollY, reducedMotion
const targetUrl = process.argv[2] || 'http://localhost:3001';
const outputPath = process.argv[3] || 'screenshot.png';
const width = parseInt(process.argv[4] || '1280', 10);
const height = parseInt(process.argv[5] || '900', 10);
const scrollTarget = process.argv[6] || '';
const reducedMotion = process.argv[7] === 'true';

console.log(`Starting Edge for ${targetUrl} [${width}x${height}, scroll=${scrollTarget}, reducedMotion=${reducedMotion}]...`);
const edge = spawn(edgePath, [
  '--headless=new',
  '--remote-debugging-port=9222',
  `--user-data-dir=${userDataDir}`,
  '--no-first-run',
  '--no-default-browser-check',
  `--window-size=${width},${height}`,
]);

async function wait(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

async function run() {
  let wsUrl = null;
  for (let i = 0; i < 25; i++) {
    await wait(300);
    try {
      const res = await fetch('http://127.0.0.1:9222/json/new?' + encodeURIComponent(targetUrl));
      const json = await res.json();
      wsUrl = json.webSocketDebuggerUrl;
      if (wsUrl) break;
    } catch (e) {}
  }

  if (!wsUrl) {
    console.error('Failed to get WebSocket debugger URL from Edge');
    edge.kill();
    process.exit(1);
  }

  const ws = new WebSocket(wsUrl);

  const send = (method, params = {}) => {
    return new Promise((resolve, reject) => {
      const id = Math.floor(Math.random() * 100000);
      const onMsg = (event) => {
        const data = JSON.parse(event.data);
        if (data.id === id) {
          ws.removeEventListener('message', onMsg);
          if (data.error) reject(data.error);
          else resolve(data.result);
        }
      };
      ws.addEventListener('message', onMsg);
      ws.send(JSON.stringify({ id, method, params }));
    });
  };

  ws.onopen = async () => {
    try {
      // Set viewport
      await send('Emulation.setDeviceMetricsOverride', {
        width,
        height,
        deviceScaleFactor: 2,
        mobile: width < 768,
      });

      if (reducedMotion) {
        await send('Emulation.setEmulatedMedia', {
          features: [{ name: 'prefers-reduced-motion', value: 'reduce' }],
        });
      }

      // Allow initial page load & intro animations to complete
      await wait(1800);

      // Scroll to target if specified
      if (scrollTarget) {
        if (!isNaN(Number(scrollTarget))) {
          await send('Runtime.evaluate', {
            expression: `window.scrollTo({ top: ${scrollTarget}, behavior: 'instant' });`,
          });
        } else {
          await send('Runtime.evaluate', {
            expression: `(() => {
              const el = document.querySelector('${scrollTarget}');
              if (el) el.scrollIntoView({ block: 'start', behavior: 'instant' });
            })();`,
          });
        }
        await wait(1200);
      }

      // Capture screenshot
      const result = await send('Page.captureScreenshot', {
        format: 'png',
        captureBeyondViewport: false,
      });

      const buffer = Buffer.from(result.data, 'base64');
      fs.writeFileSync(outputPath, buffer);
      console.log(`Saved screenshot to: ${outputPath} (${buffer.length} bytes)`);

      ws.close();
      edge.kill();
      try {
        fs.rmSync(userDataDir, { recursive: true, force: true });
      } catch (e) {}
      process.exit(0);
    } catch (err) {
      console.error('Error during capture:', err);
      ws.close();
      edge.kill();
      process.exit(1);
    }
  };

  ws.onerror = (err) => {
    console.error('WebSocket error:', err);
    edge.kill();
    process.exit(1);
  };
}

run().catch((err) => {
  console.error(err);
  edge.kill();
  process.exit(1);
});

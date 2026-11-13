import { spawn } from 'child_process';
import fs from 'fs';
import path from 'path';

const edgePath = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const targetDir = 'C:\\Users\\ASUS\\.gemini\\antigravity\\brain\\02de4ae1-66bd-4199-a5d0-c58cccd3f673\\screenshots';
if (!fs.existsSync(targetDir)) {
  fs.mkdirSync(targetDir, { recursive: true });
}

const targets = [
  { name: '01_hero_to_problem.png', scroll: 650, w: 1280, h: 900 },
  { name: '02_problem_cards.png', scroll: 900, w: 1280, h: 900 },
  { name: '03_introducing_assembly.png', scroll: '#product', w: 1280, h: 900 },
  { name: '04_how_it_works.png', scroll: '#how', w: 1280, h: 900 },
  { name: '05_knowledge_intelligence.png', scroll: '#intelligence', w: 1280, h: 900 },
  { name: '06_knowledge_explorer.png', scroll: '#explorer', w: 1280, h: 900 },
  { name: '07_structured_handovers.png', scroll: '#handovers', w: 1280, h: 900 },
  { name: '08_final_cta.png', scroll: 6500, w: 1280, h: 900 },
  { name: '09_mobile_problem.png', scroll: 750, w: 375, h: 812, mobile: true },
  { name: '10_reduced_motion_problem.png', scroll: 900, w: 1280, h: 900, reducedMotion: true },
];

async function wait(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

async function captureOne(item) {
  const outputPath = path.join(targetDir, item.name);
  const userDataDir = path.join(process.env.TEMP || 'C:\\temp', 'cdp_batch_' + Date.now() + '_' + Math.random());
  const edge = spawn(edgePath, [
    '--headless=new',
    '--remote-debugging-port=9444',
    `--user-data-dir=${userDataDir}`,
    '--no-first-run',
    '--no-default-browser-check',
    `--window-size=${item.w},${item.h}`,
  ]);

  let wsUrl = null;
  for (let i = 0; i < 20; i++) {
    await wait(250);
    try {
      const res = await fetch('http://127.0.0.1:9444/json/new?http%3A%2F%2Flocalhost%3A3001');
      const json = await res.json();
      wsUrl = json.webSocketDebuggerUrl;
      if (wsUrl) break;
    } catch (e) {}
  }

  if (!wsUrl) {
    edge.kill();
    throw new Error('Could not get wsUrl for ' + item.name);
  }

  return new Promise((resolve, reject) => {
    const ws = new WebSocket(wsUrl);

    const send = (method, params = {}) => {
      return new Promise((res, rej) => {
        const id = Math.floor(Math.random() * 100000);
        const onMsg = (event) => {
          const data = JSON.parse(event.data);
          if (data.id === id) {
            ws.removeEventListener('message', onMsg);
            if (data.error) rej(data.error);
            else res(data.result);
          }
        };
        ws.addEventListener('message', onMsg);
        ws.send(JSON.stringify({ id, method, params }));
      });
    };

    ws.onopen = async () => {
      try {
        await send('Emulation.setDeviceMetricsOverride', {
          width: item.w,
          height: item.h,
          deviceScaleFactor: 2,
          mobile: !!item.mobile,
        });

        if (item.reducedMotion) {
          await send('Emulation.setEmulatedMedia', {
            features: [{ name: 'prefers-reduced-motion', value: 'reduce' }],
          });
        }

        // Wait initial layout
        await wait(1500);

        if (typeof item.scroll === 'number') {
          await send('Runtime.evaluate', {
            expression: `window.scrollTo({ top: ${item.scroll}, behavior: 'instant' });`,
          });
        } else if (item.scroll) {
          await send('Runtime.evaluate', {
            expression: `(() => {
              const el = document.querySelector('${item.scroll}');
              if (el) el.scrollIntoView({ block: 'start', behavior: 'instant' });
            })();`,
          });
        }

        // Let reveal & motion trigger
        await wait(1200);

        const result = await send('Page.captureScreenshot', {
          format: 'png',
          captureBeyondViewport: false,
        });

        const buffer = Buffer.from(result.data, 'base64');
        fs.writeFileSync(outputPath, buffer);
        console.log(`[OK] Captured ${item.name} (${buffer.length} bytes)`);

        ws.close();
        edge.kill();
        try {
          fs.rmSync(userDataDir, { recursive: true, force: true });
        } catch (e) {}
        resolve();
      } catch (e) {
        ws.close();
        edge.kill();
        reject(e);
      }
    };

    ws.onerror = (err) => {
      edge.kill();
      reject(err);
    };
  });
}

async function main() {
  console.log(`Capturing ${targets.length} verification screenshots...`);
  for (const item of targets) {
    try {
      await captureOne(item);
    } catch (err) {
      console.error(`[FAIL] ${item.name}:`, err.message || err);
    }
  }
  console.log('All captures complete!');
}

main().catch(console.error);

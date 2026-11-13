import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

async function main() {
  const url = process.argv[2] || "http://localhost:3001";
  const outputPath = process.argv[3] || "screenshot.png";
  const width = parseInt(process.argv[4] || "1280", 10);
  const height = parseInt(process.argv[5] || "900", 10);
  const isMobile = process.argv[6] === "mobile";
  const targetSelector = process.argv[7] || "#product";

  const port = 9444;
  const chromePath = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
  const userDataDir = path.join(process.env.TEMP || "C:\\Temp", `chrome_shot_${Date.now()}`);

  const chrome = spawn(chromePath, [
    "--headless=new",
    `--remote-debugging-port=${port}`,
    "--remote-allow-origins=*",
    `--user-data-dir=${userDataDir}`,
    "--disable-gpu",
    "--no-first-run",
    "--no-default-browser-check",
    "about:blank",
  ]);

  // Wait for debug port
  let wsUrl = null;
  for (let i = 0; i < 40; i++) {
    await new Promise((r) => setTimeout(r, 200));
    try {
      const res = await fetch(`http://127.0.0.1:${port}/json/version`);
      const data = await res.json();
      wsUrl = data.webSocketDebuggerUrl;
      if (wsUrl) break;
    } catch {}
  }

  if (!wsUrl) {
    chrome.kill();
    throw new Error(`Could not connect to Chrome debugging port on ${port}`);
  }

  const ws = new WebSocket(wsUrl);
  await new Promise((resolve) => ws.addEventListener("open", resolve));

  let id = 1;
  const callbacks = new Map();
  ws.addEventListener("message", (event) => {
    const msg = JSON.parse(event.data);
    if (msg.id && callbacks.has(msg.id)) {
      callbacks.get(msg.id)(msg);
      callbacks.delete(msg.id);
    }
  });

  function send(method, params = {}) {
    return new Promise((resolve) => {
      const msgId = id++;
      callbacks.set(msgId, resolve);
      ws.send(JSON.stringify({ id: msgId, method, params }));
    });
  }

  // Create new page
  const targetRes = await send("Target.createTarget", { url: "about:blank" });
  const targetId = targetRes.result.targetId;

  // Connect to page
  const pageWs = new WebSocket(`ws://127.0.0.1:${port}/devtools/page/${targetId}`);
  await new Promise((resolve) => pageWs.addEventListener("open", resolve));

  let pageId = 1;
  const pageCallbacks = new Map();
  pageWs.addEventListener("message", (event) => {
    const msg = JSON.parse(event.data);
    if (msg.id && pageCallbacks.has(msg.id)) {
      pageCallbacks.get(msg.id)(msg);
      pageCallbacks.delete(msg.id);
    }
  });

  function sendPage(method, params = {}) {
    return new Promise((resolve) => {
      const msgId = pageId++;
      pageCallbacks.set(msgId, resolve);
      pageWs.send(JSON.stringify({ id: msgId, method, params }));
    });
  }

  await sendPage("Page.enable");
  await sendPage("DOM.enable");
  await sendPage("Page.addScriptToEvaluateOnNewDocument", {
    source: `
      try {
        sessionStorage.setItem("handover_intro_seen", "1");
      } catch (e) {}
    `,
  });
  await sendPage("Emulation.setDeviceMetricsOverride", {
    width,
    height,
    deviceScaleFactor: 2,
    mobile: isMobile,
  });

  await sendPage("Page.navigate", { url });
  // Wait for initial render
  await new Promise((r) => setTimeout(r, 2000));

  // Scroll target into view
  await sendPage("Runtime.evaluate", {
    expression: `
      (() => {
        const el = document.querySelector("${targetSelector}");
        if (el) {
          el.scrollIntoView({ block: "center", behavior: "instant" });
          // Ensure all .reveal elements are shown
          document.querySelectorAll(".reveal").forEach(r => r.classList.add("is-in"));
        }
      })()
    `,
  });

  // Wait for canvas to render and animate several frames
  await new Promise((r) => setTimeout(r, 1800));

  // Get bounding box of target element
  const boxRes = await sendPage("Runtime.evaluate", {
    expression: `
      (() => {
        const el = document.querySelector("${targetSelector}");
        if (!el) return null;
        const rect = el.getBoundingClientRect();
        return {
          x: Math.max(0, rect.left),
          y: Math.max(0, rect.top),
          width: Math.min(window.innerWidth, rect.width),
          height: rect.height,
        };
      })()
    `,
    returnByValue: true,
  });

  let clip = undefined;
  if (boxRes.result && boxRes.result.value) {
    const b = boxRes.result.value;
    clip = {
      x: b.x,
      y: b.y,
      width: b.width,
      height: b.height,
      scale: 1,
    };
  }

  const shotRes = await sendPage("Page.captureScreenshot", {
    format: "png",
    clip: clip,
    captureBeyondViewport: false,
  });

  const absPath = path.resolve(outputPath);
  fs.mkdirSync(path.dirname(absPath), { recursive: true });
  fs.writeFileSync(absPath, Buffer.from(shotRes.result.data, "base64"));
  console.log(`Saved screenshot to: ${absPath}`);

  pageWs.close();
  ws.close();
  chrome.kill();
  try {
    fs.rmSync(userDataDir, { recursive: true, force: true });
  } catch {}
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});

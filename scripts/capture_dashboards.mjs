import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

const ARTIFACTS_DIR = "C:\\Users\\ASUS\\.gemini\\antigravity\\brain\\6dc433ea-5d89-4c9a-b66c-567584ea2146";

async function getAccessToken() {
  const res = await fetch("http://localhost:8000/api/v1/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      email: "engineer_live@handover.internal",
      password: "Handover123!Secure",
    }),
  });
  if (!res.ok) {
    throw new Error(`Failed to log in: ${res.status} ${await res.text()}`);
  }
  const data = await res.json();
  return data.access_token;
}

async function captureAll() {
  console.log("1. Authenticating to obtain access token...");
  const token = await getAccessToken();
  console.log("Access token obtained successfully.");

  const port = 9555;
  const chromePath = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
  const userDataDir = path.join(process.env.TEMP || "C:\\Temp", `chrome_dash_${Date.now()}`);

  console.log("2. Spawning Chrome with CDP on port", port);
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

  const targetRes = await send("Target.createTarget", { url: "about:blank" });
  const targetId = targetRes.result.targetId;

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
        localStorage.setItem("handover_access_token", "${token}");
        sessionStorage.setItem("handover_intro_seen", "1");
      } catch (e) {}
    `,
  });

  const captures = [
    { name: "dashboard-manager.png", url: "http://localhost:3001/overview?role=manager", width: 1440, height: 900 },
    { name: "dashboard-outgoing.png", url: "http://localhost:3001/overview?role=outgoing", width: 1440, height: 900 },
    { name: "dashboard-incoming.png", url: "http://localhost:3001/overview?role=incoming", width: 1440, height: 900 },
    { name: "dashboard-member.png", url: "http://localhost:3001/overview?role=member", width: 1440, height: 900 },
    { name: "dashboard-workspace.png", url: "http://localhost:3001/overview?role=workspace", width: 1440, height: 900 },
    { name: "dashboard-empty.png", url: "http://localhost:3001/overview?role=empty", width: 1440, height: 900 },
    { name: "dashboard-laptop-1280.png", url: "http://localhost:3001/overview?role=manager", width: 1280, height: 800 },
    { name: "dashboard-tablet-768.png", url: "http://localhost:3001/overview?role=manager", width: 768, height: 1024 },
    { name: "dashboard-mobile-390.png", url: "http://localhost:3001/overview?role=manager", width: 390, height: 844, isMobile: true },
  ];

  for (const c of captures) {
    console.log(`Capturing ${c.name} (${c.width}x${c.height})...`);
    await sendPage("Emulation.setDeviceMetricsOverride", {
      width: c.width,
      height: c.height,
      deviceScaleFactor: 2,
      mobile: Boolean(c.isMobile),
    });

    await sendPage("Page.navigate", { url: c.url });
    // Allow Next.js client-side data fetching & charts rendering to settle
    await new Promise((r) => setTimeout(r, 2200));

    const shotRes = await sendPage("Page.captureScreenshot", {
      format: "png",
      captureBeyondViewport: false,
    });

    const outPath = path.join(ARTIFACTS_DIR, c.name);
    fs.writeFileSync(outPath, Buffer.from(shotRes.result.data, "base64"));
    console.log(`  Saved: ${outPath} (${Math.round(shotRes.result.data.length * 0.75 / 1024)} KB)`);
  }

  pageWs.close();
  ws.close();
  chrome.kill();
  try {
    fs.rmSync(userDataDir, { recursive: true, force: true });
  } catch {}
  console.log("All dashboard captures completed successfully!");
}

captureAll().catch((err) => {
  console.error("Capture failed:", err);
  process.exit(1);
});

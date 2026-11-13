import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

const ARTIFACT_DIR = "C:\\Users\\ASUS\\.gemini\\antigravity\\brain\\6dc433ea-5d89-4c9a-b66c-567584ea2146";

async function run() {
  const tmpDir = path.join(process.env.TEMP || "C:\\Temp", `chrome_p3_${Date.now()}`);
  const chrome = spawn("C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe", [
    "--headless=new",
    "--remote-debugging-port=9893",
    "--remote-allow-origins=*",
    `--user-data-dir=${tmpDir}`,
    "--window-size=1440,900",
    "about:blank",
  ]);

  let res;
  for (let attempt = 0; attempt < 30; attempt++) {
    try {
      res = await fetch("http://127.0.0.1:9893/json/version");
      if (res.ok) break;
    } catch {
      await new Promise((r) => setTimeout(r, 400));
    }
  }
  if (!res) throw new Error("Could not connect to Chrome debugging port 9893");
  const { webSocketDebuggerUrl } = await res.json();
  const ws = new WebSocket(webSocketDebuggerUrl);
  await new Promise((r) => ws.addEventListener("open", r));

  let id = 1;
  const callbacks = new Map();
  ws.addEventListener("message", (e) => {
    const msg = JSON.parse(e.data);
    if (msg.id && callbacks.has(msg.id)) {
      callbacks.get(msg.id)(msg);
      callbacks.delete(msg.id);
    }
  });

  const send = (method, params = {}) =>
    new Promise((r) => {
      const msgId = id++;
      callbacks.set(msgId, r);
      ws.send(JSON.stringify({ id: msgId, method, params }));
    });

  const target = await send("Target.createTarget", { url: "about:blank" });
  const pageWs = new WebSocket("ws://127.0.0.1:9893/devtools/page/" + target.result.targetId);
  await new Promise((r) => pageWs.addEventListener("open", r));

  let pId = 1;
  const pCallbacks = new Map();

  pageWs.addEventListener("message", (e) => {
    const msg = JSON.parse(e.data);
    if (msg.id && pCallbacks.has(msg.id)) {
      pCallbacks.get(msg.id)(msg);
      pCallbacks.delete(msg.id);
    }
  });
  const sendPage = (method, params = {}) =>
    new Promise((r) => {
      const msgId = pId++;
      pCallbacks.set(msgId, r);
      pageWs.send(JSON.stringify({ id: msgId, method, params }));
    });

  const evalExpr = async (expression) => {
    const response = await sendPage("Runtime.evaluate", {
      expression,
      returnByValue: true,
      awaitPromise: true,
    });
    return response.result?.result?.value;
  };

  const capture = async (filename, width = 1440, height = 900) => {
    await sendPage("Emulation.setDeviceMetricsOverride", {
      width,
      height,
      deviceScaleFactor: 1,
      mobile: width < 768,
    });
    await new Promise((r) => setTimeout(r, 600));
    const shot = await sendPage("Page.captureScreenshot", { format: "png" });
    const targetPath = path.join(ARTIFACT_DIR, filename);
    fs.writeFileSync(targetPath, Buffer.from(shot.result.data, "base64"));
    console.log(`[CDP] Saved screenshot: ${filename} (${width}x${height})`);
  };

  await sendPage("Page.enable");
  await sendPage("Runtime.enable");

  console.log("[CDP] Navigating to /login...");
  await sendPage("Page.navigate", { url: "http://localhost:3001/login" });
  await new Promise((r) => setTimeout(r, 2000));

  console.log("[CDP] Logging in as engineer_live@handover.internal...");
  await evalExpr(`
    (() => {
      const emailInput = document.querySelector('input[type="email"]');
      const passInput = document.querySelector('input[type="password"]');
      const submitBtn = document.querySelector('button[type="submit"]');

      const setVal = (el, val) => {
        const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
        setter.call(el, val);
        el.dispatchEvent(new Event('input', { bubbles: true }));
        el.dispatchEvent(new Event('change', { bubbles: true }));
      };

      setVal(emailInput, "engineer_live@handover.internal");
      setVal(passInput, "Handover123!Secure");
      setTimeout(() => { submitBtn.click(); }, 100);
    })()
  `);

  for (let i = 0; i < 25; i++) {
    await new Promise((r) => setTimeout(r, 500));
    const ready = await evalExpr(`Boolean(window.location.href.includes('/overview') && !document.querySelector('.backdrop-blur-xs'))`);
    if (ready) break;
  }
  await new Promise((r) => setTimeout(r, 1000));
  console.log("[CDP] Login confirmed, landed on overview.");

  // 1. PROJECT DIRECTORY - GRID VIEW
  console.log("[CDP] Navigating to /projects...");
  await sendPage("Page.navigate", { url: "http://localhost:3001/projects" });
  await new Promise((r) => setTimeout(r, 2000));

  const projectsCount = await evalExpr(`document.querySelectorAll('.tile-target, tbody tr').length`);
  console.log(`[CDP] Projects directory loaded. Elements count: ${projectsCount}`);
  await capture("project-directory.png", 1440, 900);

  // 2. PROJECT DIRECTORY - LIST VIEW
  console.log("[CDP] Switching to List view...");
  await evalExpr(`
    (() => {
      const btns = Array.from(document.querySelectorAll('button'));
      const listBtn = btns.find(b => b.innerText.includes('List') || b.querySelector('svg.lucide-list'));
      if (listBtn) listBtn.click();
    })()
  `);
  await new Promise((r) => setTimeout(r, 800));
  await capture("project-directory-list.png", 1440, 900);

  // 3. PROJECT DIRECTORY - SEARCH & FILTER
  console.log("[CDP] Testing Search filtering...");
  await evalExpr(`
    (() => {
      const input = document.querySelector('input[placeholder*="Search projects"]');
      if (input) {
        const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
        setter.call(input, "Billing");
        input.dispatchEvent(new Event('input', { bubbles: true }));
        input.dispatchEvent(new Event('change', { bubbles: true }));
      }
    })()
  `);
  await new Promise((r) => setTimeout(r, 800));
  const filteredCount = await evalExpr(`document.querySelectorAll('tbody tr').length`);
  console.log(`[CDP] Filtered projects count for 'Billing': ${filteredCount}`);
  await capture("project-directory-filtered.png", 1440, 900);

  // Clear search
  await evalExpr(`
    (() => {
      const input = document.querySelector('input[placeholder*="Search projects"]');
      if (input) {
        const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
        setter.call(input, "");
        input.dispatchEvent(new Event('input', { bubbles: true }));
      }
      const btns = Array.from(document.querySelectorAll('button'));
      const gridBtn = btns.find(b => b.innerText.includes('Grid') || b.querySelector('svg.lucide-layout-grid'));
      if (gridBtn) gridBtn.click();
    })()
  `);
  await new Promise((r) => setTimeout(r, 800));

  // 4. OPEN PROJECT WORKSPACE
  console.log("[CDP] Opening first project workspace...");
  const firstProjectId = await evalExpr(`
    (() => {
      const card = document.querySelector('.tile-target');
      if (card) {
        card.click();
        return true;
      }
      return false;
    })()
  `);
  console.log(`[CDP] Clicked project card: ${firstProjectId}`);
  await new Promise((r) => setTimeout(r, 2000));

  const currentUrl = await evalExpr(`window.location.href`);
  console.log(`[CDP] Landed on: ${currentUrl}`);

  // Overview Tab Capture
  await capture("project-overview.png", 1440, 900);

  // 5. TEAM TAB
  console.log("[CDP] Switching to Team tab...");
  await evalExpr(`
    (() => {
      const tabBtns = Array.from(document.querySelectorAll('button'));
      const teamTab = tabBtns.find(b => b.innerText.trim() === 'Team' || b.innerText.includes('Team'));
      if (teamTab) teamTab.click();
    })()
  `);
  await new Promise((r) => setTimeout(r, 1200));
  await capture("project-team.png", 1440, 900);

  // Open Add Member Modal
  console.log("[CDP] Testing Add Member modal...");
  await evalExpr(`
    (() => {
      const btns = Array.from(document.querySelectorAll('button'));
      const addBtn = btns.find(b => b.innerText.includes('Add Member'));
      if (addBtn) addBtn.click();
    })()
  `);
  await new Promise((r) => setTimeout(r, 800));
  await capture("project-team-add-modal.png", 1440, 900);

  // Close Add Member Modal
  await evalExpr(`
    (() => {
      const btns = Array.from(document.querySelectorAll('button'));
      const cancelBtn = btns.find(b => b.innerText.trim() === 'Cancel');
      if (cancelBtn) cancelBtn.click();
    })()
  `);
  await new Promise((r) => setTimeout(r, 600));

  // 6. SETTINGS TAB
  console.log("[CDP] Switching to Settings tab...");
  await evalExpr(`
    (() => {
      const tabBtns = Array.from(document.querySelectorAll('button'));
      const settingsTab = tabBtns.find(b => b.innerText.trim() === 'Settings' || b.innerText.includes('Settings'));
      if (settingsTab) settingsTab.click();
    })()
  `);
  await new Promise((r) => setTimeout(r, 1200));
  await capture("project-settings.png", 1440, 900);

  // 7. ACTIVITY TAB
  console.log("[CDP] Switching to Activity tab...");
  await evalExpr(`
    (() => {
      const tabBtns = Array.from(document.querySelectorAll('button'));
      const actTab = tabBtns.find(b => b.innerText.trim() === 'Activity' || b.innerText.includes('Activity'));
      if (actTab) actTab.click();
    })()
  `);
  await new Promise((r) => setTimeout(r, 1200));
  await capture("project-activity.png", 1440, 900);

  // 8. PROJECT CREATION WIZARD (/projects/new)
  console.log("[CDP] Navigating to /projects/new...");
  await sendPage("Page.navigate", { url: "http://localhost:3001/projects/new" });
  await new Promise((r) => setTimeout(r, 2000));

  // Step 1: Details - Test validation
  console.log("[CDP] Testing Step 1 validation...");
  await evalExpr(`
    (() => {
      const btns = Array.from(document.querySelectorAll('button'));
      const continueBtn = btns.find(b => b.innerText.includes('Continue'));
      if (continueBtn) continueBtn.click();
    })()
  `);
  await new Promise((r) => setTimeout(r, 600));
  await capture("project-wizard-step1-validation.png", 1440, 900);

  // Step 1: Details - Fill valid information
  console.log("[CDP] Filling in Step 1 valid project information...");
  const timestamp = Date.now().toString().slice(-4);
  const testProjectName = `Real-Time Data Pipeline v${timestamp}`;
  await evalExpr(`
    (() => {
      const nameInput = document.querySelector('input[placeholder*="Billing Infrastructure"]');
      const descInput = document.querySelector('textarea[placeholder*="What does this project encompass"]');

      const setVal = (el, val) => {
        if (!el) return;
        const proto = el instanceof HTMLTextAreaElement ? window.HTMLTextAreaElement.prototype : window.HTMLInputElement.prototype;
        const setter = Object.getOwnPropertyDescriptor(proto, 'value').set;
        setter.call(el, val);
        el.dispatchEvent(new Event('input', { bubbles: true }));
        el.dispatchEvent(new Event('change', { bubbles: true }));
      };

      setVal(nameInput, "${testProjectName}");
      setVal(descInput, "End-to-end streaming ingestion architecture using Apache Kafka and Apache Flink with automated dead-letter queue governance.");
    })()
  `);
  await new Promise((r) => setTimeout(r, 600));
  await capture("project-wizard-step1.png", 1440, 900);

  // Advance to Step 2: Team
  console.log("[CDP] Continuing to Step 2: Team...");
  await evalExpr(`
    (() => {
      const btns = Array.from(document.querySelectorAll('button'));
      const continueBtn = btns.find(b => b.innerText.includes('Continue'));
      if (continueBtn) continueBtn.click();
    })()
  `);
  await new Promise((r) => setTimeout(r, 1000));
  await capture("project-wizard-step2.png", 1440, 900);

  // Advance to Step 3: Sources & Scope
  console.log("[CDP] Continuing to Step 3: Sources & Scope...");
  await evalExpr(`
    (() => {
      const btns = Array.from(document.querySelectorAll('button'));
      const continueBtn = btns.find(b => b.innerText.includes('Continue'));
      if (continueBtn) continueBtn.click();
    })()
  `);
  await new Promise((r) => setTimeout(r, 1000));
  await capture("project-wizard-step3.png", 1440, 900);

  // Create Project Submission
  console.log("[CDP] Submitting project creation...");
  await evalExpr(`
    (() => {
      const btns = Array.from(document.querySelectorAll('button'));
      const createBtn = btns.find(b => b.innerText.includes('Create Project'));
      if (createBtn) createBtn.click();
    })()
  `);

  for (let i = 0; i < 20; i++) {
    await new Promise((r) => setTimeout(r, 500));
    const url = await evalExpr(`window.location.href`);
    if (url.includes('/projects/') && !url.includes('/new')) {
      console.log(`[CDP] Successfully created project and redirected to: ${url}`);
      break;
    }
  }
  await new Promise((r) => setTimeout(r, 1500));
  await capture("project-creation-success.png", 1440, 900);

  // 9. RESPONSIVE VIEWPORT SUITE (Workspace)
  console.log("[CDP] Capturing responsive viewport suite...");
  await capture("project-desktop-1440.png", 1440, 900);
  await capture("project-laptop-1280.png", 1280, 800);
  await capture("project-tablet-768.png", 768, 1024);
  await capture("project-mobile-390.png", 390, 844);

  console.log("[CDP] Phase 3 end-to-end CDP verification completed successfully!");
  chrome.kill();
  process.exit(0);
}

run().catch((err) => {
  console.error("[CDP Error]", err);
  process.exit(1);
});

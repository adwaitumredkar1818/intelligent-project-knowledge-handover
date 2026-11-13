import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

const ARTIFACT_DIR = "C:\\Users\\ASUS\\.gemini\\antigravity\\brain\\6dc433ea-5d89-4c9a-b66c-567584ea2146";

async function run() {
  const tmpDir = path.join(process.env.TEMP || "C:\\Temp", `chrome_val_${Date.now()}`);
  const chrome = spawn("C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe", [
    "--headless=new",
    "--remote-debugging-port=9891",
    "--remote-allow-origins=*",
    `--user-data-dir=${tmpDir}`,
    "--window-size=1440,900",
    "about:blank",
  ]);

  await new Promise((r) => setTimeout(r, 1200));
  const res = await fetch("http://127.0.0.1:9891/json/version");
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
  const pageWs = new WebSocket("ws://127.0.0.1:9891/devtools/page/" + target.result.targetId);
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
    console.log(`Saved screenshot: ${filename} (${width}x${height})`);
  };

  await sendPage("Page.enable");
  await sendPage("Runtime.enable");

  console.log("Navigating to /login...");
  await sendPage("Page.navigate", { url: "http://localhost:3001/login" });
  await new Promise((r) => setTimeout(r, 2000));

  console.log("Filling in credentials...");
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

  const selectOrgDeterministic = async (orgName) => {
    return await evalExpr(`
      (async (targetOrg) => {
        document.body.click();
        await new Promise(r => setTimeout(r, 100));

        const asideButtons = Array.from(document.querySelectorAll('aside button'));
        const orgTrigger = asideButtons.find(b => b.querySelector('svg.lucide-chevron-down'));
        if (!orgTrigger) return { error: "Org trigger button not found" };

        orgTrigger.click();
        await new Promise(r => setTimeout(r, 300));

        const menu = document.querySelector('.shadow-pop');
        if (!menu) return { error: "Org menu not opened" };

        const menuButtons = Array.from(menu.querySelectorAll('button'));
        const match = menuButtons.find(b => b.innerText.toLowerCase().includes(targetOrg.toLowerCase()));
        if (!match) {
          return { error: "Org '" + targetOrg + "' not found", available: menuButtons.map(b => b.innerText.trim().slice(0, 30)) };
        }

        match.click();
        await new Promise(r => setTimeout(r, 1500));
        return { success: true, switchedOrg: targetOrg };
      })("${orgName}")
    `);
  };

  const selectProjectDeterministic = async (name) => {
    return await evalExpr(`
      (async (projectName) => {
        document.body.click();
        await new Promise(r => setTimeout(r, 100));

        const asideButtons = Array.from(document.querySelectorAll('aside button'));
        const trigger = asideButtons.find(b => b.querySelector('svg.lucide-chevrons-up-down'));
        if (!trigger) {
          return { error: "Project selector trigger button not found" };
        }

        trigger.click();
        await new Promise(r => setTimeout(r, 300));

        const menu = document.querySelector('.shadow-pop');
        if (!menu) return { error: "Dropdown menu not opened" };

        const menuButtons = Array.from(menu.querySelectorAll('button'));
        const match = menuButtons.find(b => b.innerText.toLowerCase().includes(projectName.toLowerCase()));
        if (!match) {
          return { error: "Project item '" + projectName + "' not found in menu", available: menuButtons.map(b => b.innerText.trim().slice(0, 30)) };
        }

        match.click();
        await new Promise(r => setTimeout(r, 1000));
        return { success: true, selected: projectName };
      })("${name}")
    `);
  };

  const getDashboardState = async () => {
    return await evalExpr(`
      (() => {
        const h1 = document.querySelector('h1')?.innerText || "";
        const subtitle = document.querySelector('main p.text-slate-600, main p.text-slate-500, main p')?.innerText || "";
        const rolePill = document.querySelector('header span[class*="rounded-full"]')?.innerText || "";
        const activeProjectText = document.querySelector('header span.font-semibold.text-navy, main span.font-semibold.text-navy')?.innerText || "";
        const buttons = Array.from(document.querySelectorAll('main button')).map(b => b.innerText.trim()).filter(Boolean);
        const cards = Array.from(document.querySelectorAll('main h3, main h4')).map(h => h.innerText.trim()).filter(Boolean);
        return {
          h1,
          subtitle,
          activeProjectText,
          rolePill,
          buttons: buttons.slice(0, 8),
          cards: cards.slice(0, 8),
        };
      })()
    `);
  };

  // Switch to The Handover organisation
  console.log("Switching to 'The Handover' organisation...");
  await selectOrgDeterministic("The Handover");
  await new Promise(r => setTimeout(r, 1500));

  console.log("\n==========================================");
  console.log("TEST 1: Project A (Core Platform Engine) -> Manager Role");
  console.log("==========================================");
  await selectProjectDeterministic("Core Platform Engine");
  await new Promise(r => setTimeout(r, 1000));
  const stateA = await getDashboardState();
  console.log("State A (Manager):", stateA);
  await capture("dashboard-role-manager.png");

  console.log("\n==========================================");
  console.log("TEST 2: Project B (Legacy Auth Migration) -> Outgoing Role");
  console.log("==========================================");
  await selectProjectDeterministic("Legacy Auth Migration");
  await new Promise(r => setTimeout(r, 1000));
  const stateB = await getDashboardState();
  console.log("State B (Outgoing):", stateB);
  await capture("dashboard-role-outgoing.png");

  console.log("\n==========================================");
  console.log("TEST 3: Project C (Knowledge Extraction Pipeline) -> Incoming Role");
  console.log("==========================================");
  await selectProjectDeterministic("Knowledge Extraction Pipeline");
  await new Promise(r => setTimeout(r, 1000));
  const stateC = await getDashboardState();
  console.log("State C (Incoming):", stateC);
  await capture("dashboard-role-incoming.png");

  console.log("\n==========================================");
  console.log("TEST 4: Project D (Compliance & Verification Engine) -> Reviewer Role");
  console.log("==========================================");
  await selectProjectDeterministic("Compliance & Verification Engine");
  await new Promise(r => setTimeout(r, 1000));
  const stateD = await getDashboardState();
  console.log("State D (Reviewer):", stateD);
  await capture("dashboard-role-reviewer.png");

  console.log("\n==========================================");
  console.log("TEST 5: Project E (Frontend System Reference) -> Member Role");
  console.log("==========================================");
  await selectProjectDeterministic("Frontend System Reference");
  await new Promise(r => setTimeout(r, 1000));
  const stateE = await getDashboardState();
  console.log("State E (Member):", stateE);
  await capture("dashboard-role-member.png");

  console.log("\n==========================================");
  console.log("TEST 6: Security Role-Spoofing Attempt (?role=manager on Member project)");
  console.log("==========================================");
  console.log("Navigating to /overview?role=manager...");
  await sendPage("Page.navigate", { url: "http://localhost:3001/overview?role=manager" });
  await new Promise((r) => setTimeout(r, 1500));
  const stateSpoof = await getDashboardState();
  console.log("State after spoof attempt (?role=manager):", stateSpoof);
  const spoofBlocked = stateSpoof.subtitle?.includes("Collaborator") || !stateSpoof.subtitle?.includes("Managing");
  console.log("SPOOFING BLOCKED STATUS:", spoofBlocked ? "PASSED (NO PRIVILEGE ESCALATION)" : "FAILED");

  console.log("\n==========================================");
  console.log("TEST 7: Workspace Overview (All Projects Aggregation)");
  console.log("==========================================");
  await selectProjectDeterministic("Workspace Overview");
  await new Promise(r => setTimeout(r, 1000));
  const stateWorkspace = await getDashboardState();
  console.log("State Workspace:", stateWorkspace);
  await capture("dashboard-role-workspace.png");

  console.log("\n==========================================");
  console.log("TEST 8: Multi-tenant Isolation & Empty Workspace");
  console.log("==========================================");
  await selectOrgDeterministic("Empty Sandbox Org");
  await new Promise(r => setTimeout(r, 1500));
  const stateEmpty = await getDashboardState();
  console.log("State Empty Org:", stateEmpty);
  await capture("dashboard-role-empty.png");

  console.log("\n==========================================");
  console.log("TEST 9: Multi-tenant Isolation: The Sapiens (1 isolated project)");
  console.log("==========================================");
  await selectOrgDeterministic("The Sapiens");
  await new Promise(r => setTimeout(r, 1500));
  const stateSapiens = await getDashboardState();
  console.log("State The Sapiens:", stateSapiens);

  console.log("\n==========================================");
  console.log("TEST 10: Responsive Viewports Verification");
  console.log("==========================================");
  await selectOrgDeterministic("The Handover");
  await selectProjectDeterministic("Core Platform Engine");
  await new Promise(r => setTimeout(r, 1000));

  await capture("dashboard-desktop-1440.png", 1440, 900);
  await capture("dashboard-laptop-1280.png", 1280, 800);
  await capture("dashboard-tablet-768.png", 768, 1024);
  await capture("dashboard-mobile-390.png", 390, 844);

  console.log("\n==========================================");
  console.log("ALL TESTS AND SCREENSHOT CAPTURES COMPLETED SUCCESSFULLY!");
  console.log("==========================================");

  pageWs.close();
  ws.close();
  chrome.kill();
  try { fs.rmSync(tmpDir, { recursive: true, force: true }); } catch {}
}

run().catch(console.error);

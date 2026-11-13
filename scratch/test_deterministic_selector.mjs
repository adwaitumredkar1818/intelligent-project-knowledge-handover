import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

const ARTIFACT_DIR = "C:\\Users\\ASUS\\.gemini\\antigravity\\brain\\6dc433ea-5d89-4c9a-b66c-567584ea2146";

async function run() {
  const tmpDir = path.join(process.env.TEMP || "C:\\Temp", `chrome_val_${Date.now()}`);
  const chrome = spawn("C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe", [
    "--headless=new",
    "--remote-debugging-port=9890",
    "--remote-allow-origins=*",
    `--user-data-dir=${tmpDir}`,
    "--window-size=1440,900",
    "about:blank",
  ]);

  await new Promise((r) => setTimeout(r, 1200));
  const res = await fetch("http://127.0.0.1:9890/json/version");
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
  const pageWs = new WebSocket("ws://127.0.0.1:9890/devtools/page/" + target.result.targetId);
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

        // Find org selector button in sidebar (contains ChevronDown)
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

  console.log("Switching organisation to 'The Handover'...");
  const orgRes = await selectOrgDeterministic("The Handover");
  console.log("Org switch result:", orgRes);
  await new Promise(r => setTimeout(r, 2000));

  const selectProjectDeterministic = async (name) => {
    return await evalExpr(`
      (async (projectName) => {
        // 1. Close any open dropdowns first by clicking body
        document.body.click();
        await new Promise(r => setTimeout(r, 100));

        // 2. Locate the project selector trigger button in the sidebar (contains ChevronsUpDown)
        const asideButtons = Array.from(document.querySelectorAll('aside button'));
        const trigger = asideButtons.find(b => b.querySelector('svg.lucide-chevrons-up-down'));
        if (!trigger) {
          return { error: "Project selector trigger button not found", buttons: asideButtons.map(b => b.innerText.trim().slice(0, 30)) };
        }

        trigger.click();
        await new Promise(r => setTimeout(r, 300));

        // 3. Find target item in .shadow-pop menu
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

  const getDashboardRoleInfo = async () => {
    return await evalExpr(`
      (() => {
        const h1 = document.querySelector('h1')?.innerText || "";
        const subtitle = document.querySelector('main p.text-slate-600, main p.text-slate-500, main p')?.innerText || "";
        const rolePill = document.querySelector('header span[class*="rounded-full"]')?.innerText || "";
        const headerRole = document.querySelector('header .text-xs, header span.font-bold, header span.uppercase')?.innerText || "";
        const cards = Array.from(document.querySelectorAll('main h3, main h4')).map(h => h.innerText.trim()).filter(Boolean);
        const activeProjectText = document.querySelector('aside .text-navy.truncate, header span.font-semibold.text-navy')?.innerText || "";
        return { h1, subtitle, rolePill, headerRole, activeProjectText, cards: cards.slice(0, 5) };
      })()
    `);
  };

  const projectsToTest = [
    { name: "Core Platform Engine", expectedRole: "Manager" },
    { name: "Legacy Auth Migration", expectedRole: "Outgoing" },
    { name: "Knowledge Extraction Pipeline", expectedRole: "Incoming" },
    { name: "Compliance & Verification Engine", expectedRole: "Reviewer" },
    { name: "Frontend System Reference", expectedRole: "Collaborator" },
  ];

  for (const item of projectsToTest) {
    console.log(`\nTesting project: ${item.name} (Expecting ${item.expectedRole})...`);
    const selRes = await selectProjectDeterministic(item.name);
    console.log("Select result:", selRes);
    await new Promise(r => setTimeout(r, 800));
    const info = await getDashboardRoleInfo();
    console.log("Resolved info:", info);
  }

  pageWs.close();
  ws.close();
  chrome.kill();
  try { fs.rmSync(tmpDir, { recursive: true, force: true }); } catch {}
}

run().catch(console.error);

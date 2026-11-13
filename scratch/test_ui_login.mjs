import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

async function test() {
  const tmpDir = path.join(process.env.TEMP || "C:\\Temp", `chrome_login_${Date.now()}`);
  const chrome = spawn("C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe", [
    "--headless=new",
    "--remote-debugging-port=9888",
    "--remote-allow-origins=*",
    `--user-data-dir=${tmpDir}`,
    "--window-size=1440,900",
    "about:blank",
  ]);

  await new Promise((r) => setTimeout(r, 1000));
  const res = await fetch("http://127.0.0.1:9888/json/version");
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
  const pageWs = new WebSocket("ws://127.0.0.1:9888/devtools/page/" + target.result.targetId);
  await new Promise((r) => pageWs.addEventListener("open", r));

  let pId = 1;
  const pCallbacks = new Map();

  pageWs.addEventListener("message", (e) => {
    const msg = JSON.parse(e.data);
    if (msg.method === "Runtime.consoleAPICalled") {
      console.log("PAGE:", msg.params.args.map((a) => a.value || a.description).join(" "));
    }
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
  const fillRes = await evalExpr(`
    (() => {
      const emailInput = document.querySelector('input[type="email"]');
      const passInput = document.querySelector('input[type="password"]');
      const submitBtn = document.querySelector('button[type="submit"]');

      if (!emailInput || !passInput || !submitBtn) {
        return { error: "Inputs not found", email: Boolean(emailInput), pass: Boolean(passInput), btn: Boolean(submitBtn) };
      }

      const setVal = (el, val) => {
        const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
        setter.call(el, val);
        el.dispatchEvent(new Event('input', { bubbles: true }));
        el.dispatchEvent(new Event('change', { bubbles: true }));
      };

      setVal(emailInput, "engineer_live@handover.internal");
      setVal(passInput, "Handover123!Secure");

      setTimeout(() => {
        submitBtn.click();
      }, 100);

      return { success: true };
    })()
  `);
  console.log("Fill result:", fillRes);

  // Wait for login and redirect to settle
  for (let i = 0; i < 20; i++) {
    await new Promise((r) => setTimeout(r, 500));
    const state = await evalExpr(`
      (() => ({
        url: window.location.href,
        h1: document.querySelector('h1')?.innerText,
        overlay: Boolean(document.querySelector('.backdrop-blur-xs')),
        token: Boolean(localStorage.getItem('handover_access_token'))
      }))()
    `);
    console.log("State at", (i * 0.5).toFixed(1), "s:", state);
    if (state && state.url.includes("/overview") && !state.overlay) {
      console.log("LOGGED IN AND OVERVIEW READY!");
      break;
    }
  }

  const shot = await sendPage("Page.captureScreenshot", { format: "png" });
  fs.writeFileSync("C:\\Users\\ASUS\\.gemini\\antigravity\\brain\\6dc433ea-5d89-4c9a-b66c-567584ea2146\\dashboard-login-test.png", Buffer.from(shot.result.data, "base64"));
  console.log("Saved dashboard-login-test.png");

  pageWs.close();
  ws.close();
  chrome.kill();
  try { fs.rmSync(tmpDir, { recursive: true, force: true }); } catch {}
}

test().catch(console.error);

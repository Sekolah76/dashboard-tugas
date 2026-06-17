const fs = require("node:fs/promises");
const path = require("node:path");

const debugPort = Number(process.env.CDP_PORT || 9222);
const dashboardUrl = process.env.DASHBOARD_URL || "http://localhost:8501";
const outputDir = path.resolve(process.cwd(), "screenshots");
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function createTarget() {
  const url = `http://127.0.0.1:${debugPort}/json/new?${encodeURIComponent(
    `${dashboardUrl}/?qa=${Date.now()}`,
  )}`;
  const response = await fetch(url, { method: "PUT" });
  if (!response.ok) throw new Error(`Cannot create CDP target: ${response.status}`);
  return response.json();
}

async function connectTarget(target) {
  const socket = new WebSocket(target.webSocketDebuggerUrl);
  await Promise.race([
    new Promise((resolve, reject) => {
      socket.addEventListener("open", resolve, { once: true });
      socket.addEventListener("error", reject, { once: true });
    }),
    new Promise((_, reject) =>
      setTimeout(() => reject(new Error("CDP socket connection timeout")), 15000),
    ),
  ]);

  let nextId = 0;
  const pending = new Map();
  const runtimeErrors = [];
  socket.addEventListener("message", (event) => {
    const payload = JSON.parse(event.data);
    if (payload.id) {
      const waiter = pending.get(payload.id);
      if (!waiter) return;
      clearTimeout(waiter.timer);
      pending.delete(payload.id);
      if (payload.error) waiter.reject(new Error(JSON.stringify(payload.error)));
      else waiter.resolve(payload.result);
      return;
    }
    if (
      payload.method === "Runtime.exceptionThrown" ||
      payload.method === "Log.entryAdded"
    ) {
      runtimeErrors.push(payload);
    }
  });

  const send = (method, params = {}, timeoutMs = 25000) =>
    new Promise((resolve, reject) => {
      const id = ++nextId;
      const timer = setTimeout(() => {
        pending.delete(id);
        reject(new Error(`${method} timed out after ${timeoutMs}ms`));
      }, timeoutMs);
      pending.set(id, { resolve, reject, timer });
      socket.send(JSON.stringify({ id, method, params }));
    });
  return { socket, send, runtimeErrors };
}

async function evaluate(send, expression) {
  const result = await send("Runtime.evaluate", {
    expression,
    awaitPromise: true,
    returnByValue: true,
  });
  if (result.exceptionDetails) {
    throw new Error(result.exceptionDetails.text || "Runtime evaluation failed.");
  }
  return result.result ? result.result.value : undefined;
}

async function waitForText(send, text, timeoutMs = 30000) {
  const started = Date.now();
  while (Date.now() - started < timeoutMs) {
    const found = await evaluate(
      send,
      `Boolean(document.body && document.body.innerText.includes(${JSON.stringify(text)}))`,
    );
    if (found) return;
    await sleep(400);
  }
  throw new Error(`Text not found: ${text}`);
}

async function clickExact(send, text, role = null) {
  const expression = `(() => {
    const wanted = ${JSON.stringify(text)};
    const selector = ${role ? JSON.stringify(`[role="${role}"]`) : JSON.stringify("button,[role='tab']")};
    const nodes = Array.from(document.querySelectorAll(selector));
    const node = nodes.find((item) =>
      (item.innerText || item.textContent || "").trim() === wanted
    );
    if (!node) return false;
    node.click();
    return true;
  })()`;
  if (!(await evaluate(send, expression))) throw new Error(`Control not found: ${text}`);
}

async function setViewport(send, width, height, mobile = false) {
  await send("Emulation.setDeviceMetricsOverride", {
    width,
    height,
    deviceScaleFactor: 1,
    mobile,
    screenWidth: width,
    screenHeight: height,
  });
}

async function scrollTop(send) {
  await evaluate(
    send,
    `(() => {
      window.scrollTo(0, 0);
      document.querySelectorAll('[data-testid="stMain"],[data-testid="stAppViewContainer"]')
        .forEach((node) => node.scrollTo({top: 0, left: 0}));
      return true;
    })()`,
  );
}

async function scrollToText(send, text) {
  await evaluate(
    send,
    `(() => {
      const wanted = ${JSON.stringify(text)};
      const node = Array.from(document.querySelectorAll("h1,h2,h3,h4"))
        .find((item) => (item.innerText || "").trim() === wanted);
      if (!node) return false;
      node.scrollIntoView({block: "start"});
      window.scrollBy(0, -80);
      return true;
    })()`,
  );
}

async function screenshot(send, filename) {
  const result = await send(
    "Page.captureScreenshot",
    { format: "png", fromSurface: true, captureBeyondViewport: false },
    40000,
  );
  await fs.writeFile(path.join(outputDir, filename), Buffer.from(result.data, "base64"));
}

async function main() {
  await fs.mkdir(outputDir, { recursive: true });
  const target = await createTarget();
  const { socket, send, runtimeErrors } = await connectTarget(target);
  await send("Page.enable");
  await send("Runtime.enable");
  await send("Log.enable");
  await setViewport(send, 1440, 1000);
  await waitForText(send, "Masuk ke Dashboard");
  await screenshot(send, "01_Lobby.png");

  await clickExact(send, "Masuk ke Dashboard");
  await waitForText(send, "Tutup Filter");
  await sleep(2200);
  await scrollTop(send);
  await screenshot(send, "03_Control_Panel.png");

  await clickExact(send, "Tutup Filter");
  await waitForText(send, "Buka Filter");
  await sleep(1500);
  await scrollTop(send);
  await screenshot(send, "02_Hero_KPI.png");

  const tabShots = [
    ["Overview", "04_Overview.png"],
    ["Analisis Survei", "05_Analisis_Survei.png"],
    ["Analisis Ulasan", "06_Analisis_Ulasan.png"],
    ["Data Explorer", "07_Data_Explorer.png"],
    ["Lampiran Presentasi", "09_Lampiran_Presentasi.png"],
  ];
  for (const [tab, filename] of tabShots) {
    await clickExact(send, tab, "tab");
    await sleep(1600);
    await scrollToText(send, tab);
    await sleep(450);
    await screenshot(send, filename);
  }

  await clickExact(send, "Overview", "tab");
  await sleep(700);
  await scrollToText(send, "Kesimpulan Utama");
  await sleep(500);
  await screenshot(send, "08_Kesimpulan.png");

  await setViewport(send, 1024, 900);
  await sleep(600);
  await scrollTop(send);
  await fs.mkdir(path.join(outputDir, "tmp"), { recursive: true });
  await screenshot(send, "tmp/tablet_qa.png");

  await setViewport(send, 390, 844, true);
  await sleep(800);
  await scrollTop(send);
  await screenshot(send, "10_Mobile_View.png");

  const bodyText = await evaluate(send, "document.body ? document.body.innerText : ''");
  const randomIconText = [
    "double_arrow_right",
    "keyboard_double_arrow_right",
    "_arrow_right",
  ].filter((needle) => bodyText.includes(needle));
  const report = {
    url: dashboardUrl,
    capturedAt: new Date().toISOString(),
    screenshots: [
      "01_Lobby.png",
      "02_Hero_KPI.png",
      "03_Control_Panel.png",
      "04_Overview.png",
      "05_Analisis_Survei.png",
      "06_Analisis_Ulasan.png",
      "07_Data_Explorer.png",
      "08_Kesimpulan.png",
      "09_Lampiran_Presentasi.png",
      "10_Mobile_View.png",
    ],
    tabletCheck: "screenshots/tmp/tablet_qa.png",
    randomIconText,
    runtimeErrorEvents: runtimeErrors.length,
    runtimeErrorDetails: runtimeErrors.slice(0, 5).map((event) => {
      if (event.method === "Runtime.exceptionThrown") {
        return event.params?.exceptionDetails?.text || "Runtime exception";
      }
      return event.params?.entry?.text || event.method;
    }),
  };
  await fs.writeFile(
    path.join(outputDir, "qa_visual_report.json"),
    JSON.stringify(report, null, 2),
    "utf8",
  );
  socket.close();
  await fetch(`http://127.0.0.1:${debugPort}/json/close/${target.id}`, {
    method: "PUT",
  }).catch(() => {});
  console.log(JSON.stringify(report, null, 2));
}

main().catch((error) => {
  console.error(error.stack || error.message || String(error));
  process.exitCode = 1;
});

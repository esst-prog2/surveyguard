const puppeteer = require("C:/tools/hf/npm-cache/_npx/110f701c48e68d66/node_modules/puppeteer-core");
const OUT = "C:/tools/hf/capture/";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function clickByText(page, selector, text) {
  const els = await page.$$(selector);
  for (const el of els) {
    if ((await el.evaluate((e) => e.innerText)).includes(text)) { await el.click(); return true; }
  }
  return false;
}

(async () => {
  const browser = await puppeteer.launch({
    executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe",
    headless: "new",
    userDataDir: "C:/tools/hf/capture/profile",
    args: ["--hide-scrollbars", "--force-color-profile=srgb"],
  });
  const page = await browser.newPage();
  await page.setViewport({ width: 1600, height: 1000, deviceScaleFactor: 1.5 });
  await page.emulateMediaFeatures([{ name: "prefers-color-scheme", value: "light" }]);
  await page.goto("http://127.0.0.1:8501/", { waitUntil: "networkidle2" });
  await page.waitForFunction(() => document.body.innerText.includes("Response data"), { timeout: 60000 });
  await sleep(1500);
  await page.screenshot({ path: OUT + "s1-empty.png" });

  const input = await page.$('input[type="file"]');
  await input.uploadFile(OUT + "ess2_mock.csv");
  await page.waitForFunction(() => document.body.innerText.includes("ess2_mock.csv"), { timeout: 30000 });
  await page.click("::-p-text(Bundled rules file)");
  await page.waitForSelector('[data-testid="stSelectbox"]', { timeout: 30000 });
  await sleep(800);
  await page.click('[data-testid="stSelectbox"] input', { clickCount: 3 });
  await sleep(500);
  await page.keyboard.type("config/ess2.json", { delay: 30 });
  await sleep(500);
  await page.keyboard.press("Enter");
  await sleep(1500);
  await page.screenshot({ path: OUT + "s2-ready.png" });

  await clickByText(page, "button", "Run SurveyGuard");
  await page.waitForFunction(() => document.body.innerText.includes("Analysis complete!"), { timeout: 120000 });
  await page.waitForSelector('input[aria-label="Respondent"]', { timeout: 120000 });
  await sleep(4000);
  await page.evaluate(() => window.scrollTo(0, 0));
  await sleep(800);
  await page.screenshot({ path: OUT + "s3-overview.png" });
  await page.screenshot({ path: OUT + "s3-full.png", fullPage: true });

  // flagged respondents table: try to select its first row to show the straightlining heatmap
  const tableBox = await page.evaluate(() => {
    const h = [...document.querySelectorAll("h3")].find((x) => x.innerText.includes("Detector-flagged respondents"));
    if (!h) return null;
    h.scrollIntoView({ block: "start" });
    const all = [...document.querySelectorAll('[data-testid="stDataFrame"]')];
    const t = all.find((d) => d.getBoundingClientRect().top > h.getBoundingClientRect().top);
    if (!t) return null;
    const r = t.getBoundingClientRect();
    return { x: r.left, y: r.top, w: r.width, h: r.height };
  });
  await sleep(1200);
  if (tableBox) {
    await page.mouse.click(tableBox.x + 14, tableBox.y + 35 + 17);
    await sleep(3000);
  }
  await page.screenshot({ path: OUT + "s3b-flagged.png" });

  await page.evaluate(() => {
    const t = [...document.querySelectorAll('[role="tab"]')].find((x) => x.innerText.includes("Score distribution"));
    if (t) t.scrollIntoView({ block: "start" });
  });
  await sleep(2500);
  await page.screenshot({ path: OUT + "s3c-histogram.png" });

  const last = await page.$('[data-testid="stSelectbox"]:has(input[aria-label="Respondent"])');
  await last.evaluate((e) => e.scrollIntoView({ block: "center" }));
  await sleep(800);
  await (await last.$("input")).click({ clickCount: 3 });
  await sleep(500);
  await page.keyboard.type("5020", { delay: 40 });
  await sleep(600);
  await page.keyboard.press("Enter");
  await sleep(2500);
  await page.evaluate(() => {
    const h = [...document.querySelectorAll("h3")].find((x) => x.innerText.includes("Respondent drill-down"));
    if (h) h.scrollIntoView({ block: "start" });
  });
  await sleep(1200);
  await page.screenshot({ path: OUT + "s4-drilldown.png" });
  await page.evaluate(() => {
    const b = [...document.querySelectorAll("button")].find((x) => x.innerText.includes("Download cleaned data"));
    if (b) b.scrollIntoView({ block: "center" });
  });
  await sleep(1000);
  await page.screenshot({ path: OUT + "s5-downloads.png" });
  await page.screenshot({ path: OUT + "s6-full-after.png", fullPage: true });
  await browser.close();
  console.log("done");
})().catch((e) => { console.error("FAILED", e); process.exit(1); });

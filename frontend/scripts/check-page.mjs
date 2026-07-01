import { chromium } from 'playwright';

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  const logs = [];
  const errors = [];
  page.on('console', (msg) => logs.push(`[${msg.type()}] ${msg.text()}`));
  page.on('pageerror', (err) => errors.push(err.message));
  await page.goto('http://localhost:5173', { waitUntil: 'networkidle', timeout: 15000 });
  await page.waitForTimeout(3000);
  const rootHtml = await page.locator('#root').innerHTML();
  const text = await page.locator('#root').innerText().catch(() => '');
  console.log('ROOT_TEXT:', text.slice(0, 500));
  console.log('ROOT_HTML_LEN:', rootHtml.length);
  console.log('ERRORS:', errors);
  console.log('CONSOLE:', logs.slice(-20));
  await browser.close();
})();

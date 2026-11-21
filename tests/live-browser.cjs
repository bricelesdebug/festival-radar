// CI-only browser test. Disposable credentials arrive through stdin, never logs.
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
let stage = 'boot';
(async () => {
  let input = '';
  for await (const chunk of process.stdin) input += chunk;
  const config = JSON.parse(input);
  const browser = await chromium.launch({headless:true});
  try {
    const page = await browser.newPage();
    // Never run email initiation, payment, reset-password or signup during validation.
    await page.route('**/auth/v1/signup**', route => route.abort());
    await page.route('**/auth/v1/recover**', route => route.abort());
    await page.route('**/auth/v1/otp**', route => route.abort());
    const assertText = async (id, pattern) => {
      await page.locator('#'+id).filter({hasText:pattern}).waitFor({timeout:20000});
    };
    stage = 'load';
    await page.goto(config.url);
    await page.locator('.live-follow').first().waitFor();
    assert.equal(await page.getByRole('button',{name:'Premium en préparation',exact:true}).isDisabled(), true);
    stage = 'signin';
    await page.locator('#auth-email').fill(config.email);
    await page.locator('#auth-password').fill(config.password);
    await page.locator('#auth-login').click();
    await page.locator('#auth-member').waitFor({state:'visible'});
    await assertText('alert-save-status', /Préférences chargées/);
    assert.equal(await page.locator('#alert-country').inputValue(), 'BE');
    stage = 'preferences';
    await page.locator('#alert-country').selectOption('FR');
    await page.locator('#alert-genre').selectOption('Techno');
    await page.locator('#alert-email-consent').uncheck();
    await page.locator('#alert-save').click();
    await assertText('alert-save-status', /Préférences enregistrées/);
    await page.locator('#radar-preview-button').click();
    await assertText('radar-preview-list', /candidat/);
    // The REST test has unfollowed its fixture before launching the browser.
    stage = 'follow';
    const follow = page.locator('.live-follow').first();
    await follow.click();
    await page.locator('.live-follow').first().filter({hasText:'♥ Suivi'}).waitFor();
    stage = 'persistence';
    await page.reload();
    await page.locator('#auth-member').waitFor({state:'visible'});
    await assertText('alert-save-status', /Préférences chargées/);
    assert.equal(await page.locator('#alert-country').inputValue(), 'FR');
    assert.equal(await page.locator('#alert-genre').inputValue(), 'Techno');
    assert.equal(await page.locator('#alert-email-consent').isChecked(), false);
    await page.locator('.live-follow').first().filter({hasText:'♥ Suivi'}).waitFor();
    stage = 'inbox';
    await assertText('inbox-list', /Aucune notification/);
    stage = 'premium';
    await assertText('premium-account-status', /Offre Free/);
    await page.locator('.live-follow').first().click();
    await page.locator('.live-follow').first().filter({hasText:'♡ Suivre'}).waitFor();
    stage = 'signout';
    await page.locator('#auth-logout').click();
    await page.locator('#auth-guest').waitFor({state:'visible'});
    await page.locator('#auth-member').waitFor({state:'hidden'});
    console.log('Browser journey passed: sign-in, preferences, follow, reload, inbox, Free status and sign-out.');
  } finally {
    await browser.close();
  }
})().catch(() => {
  // Playwright traces can contain typed credentials. Emit a fixed safe failure.
  console.error('Browser journey failed at stage: '+stage);
  process.exitCode=1;
});

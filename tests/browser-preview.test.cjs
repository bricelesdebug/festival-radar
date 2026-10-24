const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const test = require('node:test');

function setup(country, genre, events) {
  const controls = {};
  const element = () => ({children: [], textContent: '',
    append(child) { this.children.push(child); },
    replaceChildren() { this.children = []; },
    addEventListener(_, callback) { this.click = callback; }});
  for (const id of ['alert-country','alert-genre','radar-preview-button','radar-preview-list','premium-price']) controls[id] = element();
  controls['alert-country'].value = country;
  controls['alert-genre'].value = genre;
  const context = {document: {getElementById: id => controls[id], createElement: element},
    window: {festivalRadarLiveEvents: events},
    fetch: () => Promise.reject(new Error('offline')), Intl};
  vm.runInNewContext(fs.readFileSync('assets/radar-preview.js', 'utf8'), context);
  controls['radar-preview-button'].click();
  return controls['radar-preview-list'];
}

test('browser preview applies country and exact genre together', () => {
  const out = setup('FR', 'Techno', [
    {name: 'MATCH', countryCode: 'FR', genres: ['Techno']},
    {name: 'WRONG COUNTRY', countryCode: 'BE', genres: ['Techno']},
    {name: 'BROAD', countryCode: 'FR', genres: ['Electronic']}]);
  assert.match(out.children[0].textContent, /^1 candidat/);
  assert.match(out.children[1].textContent, /^MATCH/);
});
test('source names remain text, never parsed markup', () => {
  const out = setup('', '', [{name: '<img src=x onerror=alert(1)>', genres: []}]);
  assert.match(out.children[1].textContent, /^<img/);
  assert.equal(out.children[1].children.length, 0);
});
test('missing catalog gives an honest empty preview', () => {
  const out = setup('', '', undefined);
  assert.match(out.children[0].textContent, /^0 candidat/);
});
test('preview caps the displayed candidates at ten', () => {
  const out = setup('', '', Array.from({length: 30}, (_, i) => ({name: String(i)})));
  assert.match(out.children[0].textContent, /^30 candidat/);
  assert.equal(out.children.length, 11);
});

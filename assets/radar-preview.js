// Preview current discovery candidates, never announcement claims or email sends.
const get = id => document.getElementById(id);
get('radar-preview-button').addEventListener('click', () => {
  const country = get('alert-country').value;
  const genre = get('alert-genre').value.toLowerCase();
  const events = (window.festivalRadarLiveEvents || []).filter(event =>
    (!country || event.countryCode === country) &&
    (!genre || (event.genres || []).some(g => g.toLowerCase() === genre)));
  const out = get('radar-preview-list');
  out.replaceChildren();
  const note = document.createElement('p');
  note.textContent = `${events.length} candidat(s) correspondent aux filtres affichés. Ce sont des résultats de recherche à vérifier. Seuls les changements d’événements suivis pourront ensuite devenir des alertes après validation.`;
  out.append(note);
  for (const event of events.slice(0, 10)) {
    const row = document.createElement('p');
    row.textContent = `${event.name} — ${event.country} — ${event.date || 'Date à confirmer'}`;
    out.append(row);
  }
  if (genre === 'techno' || genre === 'house') {
    const hint = document.createElement('small');
    hint.textContent = 'La catégorie générale Electronic ne suffit pas à confirmer un style Techno ou House. Ces résultats peuvent donc être peu nombreux.';
    out.append(hint);
  }
});
// A catalog of proposed plans is informational; no checkout is implemented.
fetch('./data/premium-plans.json').then(r => {
  if (!r.ok) throw new Error('Plan catalog unavailable');
  return r.json();
}).then(config => {
  const premium = config.plans.find(plan => plan.id === 'premium');
  if (!premium || !Number.isInteger(premium.monthlyPriceMinor)) return;
  get('premium-price').textContent = new Intl.NumberFormat('fr-FR', {
    style: 'currency', currency: config.currency
  }).format(premium.monthlyPriceMinor / 100) + ' / mois · envisagé';
}).catch(() => {}); // Keep the clearly labelled indicative fallback price.

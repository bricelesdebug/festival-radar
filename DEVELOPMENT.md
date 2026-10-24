# Festival Radar — collecte fiable, alertes en aperçu et préparation Premium

## État livré

- Collecte Discovery interrogée pour 24 pays européens. La couverture réelle dépend de Ticketmaster ; ce nombre ne constitue pas une garantie de festivals disponibles dans chaque pays.
- Pagination jusqu'à la limite de 1 000 résultats par pays, temporisation et trois tentatives pour les erreurs transitoires. Une limite atteinte, un pays en échec ou un résultat global vide bloque toute substitution du catalogue. Le rapport de santé est conservé dans les artefacts Actions, même en cas d'échec. Les erreurs ne révèlent pas la clé API.
- Les événements restent des candidats : la période commerciale ne prouve jamais que des billets sont disponibles. Les dates TBA/TBD sont exclues, et les identifiants sont dédupliqués.
- Extraction JSON-LD des types Event, MusicEvent, DanceEvent et Festival, y compris dans les graphes et objets imbriqués. Les affirmations des sources restent à vérifier.
- Comparaison hors ligne : instantanés datés et croissants, refus des doublons et des collectes déclarées incomplètes. Une base vide ne déclenche aucune annonce globale.
- Plus aucune écriture Supabase depuis le workflow de collecte. Le workflow manuel de boîte de réception est un aperçu sans accès aux secrets. Le script historique exige `--apply`, `INBOX_WRITES_APPROVED=true` et des `reviewedEventKeys` explicites avant toute écriture ; ces conditions ne sont pas activées par cette livraison. Les favoris et filtres de préférences sont pris en compte pour la préparation.
- Aperçu dans le compte : correspondance exacte pays/style sur le catalogue courant. La catégorie Electronic ne permet pas d'affirmer Techno ou House. L'aperçu de recherche ne promet pas une nouvelle annonce.
- Les fausses annonces de démonstration ont été retirées.
- Premium : prix indicatif configurable (4,99 €/mois), bouton désactivé et lecture du statut d'abonnement. Aucune caisse, clé de paiement, facturation ni ouverture d'abonnement.

## Vérification

```sh
python -m unittest discover -s tests -v
python scripts/audit_catalog.py data/festivals.json
python scripts/check_browser_scripts.py
node --check assets/radar-preview.js
node --test tests/browser-preview.test.cjs
for script in /tmp/festival-radar-script-*.mjs; do node --check "$script"; done
```

Le workflow CI ne reçoit aucune clé de collecte, base de données, email ou paiement. Les tests utilisent des données synthétiques locales, jamais publiées dans le catalogue.

## Aperçu personnalisé privé

`python scripts/preview_alerts.py candidates.json preferences.json --output /tmp/private-radar-preview.json`

Le format des préférences est décrit dans le script. Le résultat contient des identifiants de comptes : la sortie doit se trouver hors du dépôt publié et ne doit pas être placée dans les artefacts publics. Ce script ne se connecte à aucun service et ne produit pas une file d'envoi. Un filtre vide accepte toutes les valeurs ; un filtre renseigné exige une correspondance documentée par la source. Seuls les événements suivis sont retenus. Le consentement email est indiqué sans activer la distribution.

## Migration Premium préparée, non appliquée

`supabase/premium_v6.sql` s'applique après le schéma initial. Les comptes ne peuvent lire que leur propre abonnement et ne peuvent jamais s'accorder Premium ou modifier les identifiants du prestataire. Les champs du prestataire ne sont pas lisibles depuis le navigateur. Le journal des événements de paiement est uniquement destiné à un futur serveur. En l'absence de migration, l'interface indique que le statut est indisponible et conserve l'offre en préparation.

Avant une activation ultérieure autorisée : choisir le prestataire et confirmer le prix, implémenter les webhooks signés avec déduplication transactionnelle, calculer les droits sur le serveur, tester résiliation/expiration et renouvellement, puis vérifier en environnement de test. Pour les emails : consentement et désinscription, validation des annonces, limites de débit et mode test doivent précéder toute ouverture. Aucun de ces services n'est activé ici.

## Déploiement et limites

Cette livraison doit passer par une pull request. Les workflows qui persistent des données sur main sont désormais limités à main ; une exécution sur une branche de développement ne peut pas y recopier ses résultats. Les workflows de comparaison préexistants restent des outils de revue et ne confirment aucune annonce.

La collecte réelle du nouveau code doit être vérifiée via une exécution manuelle sur sa branche avec la clé déjà stockée dans GitHub, puis lecture du rapport de santé. Ne pas relancer un test Resend pour vérifier cette livraison. Le dépôt ne permet pas de confirmer la configuration actuelle du déploiement Netlify ni d'appliquer les migrations Supabase.

Documentation API : https://developer.ticketmaster.com/products-and-docs/apis/discovery-api/v2/

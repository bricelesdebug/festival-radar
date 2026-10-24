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

## Migration Premium appliquée, paiements inactifs

`supabase/premium_v6.sql` a été appliquée au projet Festival Radar le 24 octobre 2026, après accord explicite du propriétaire. Pour une autre instance, elle s’applique après le schéma initial. Les comptes ne peuvent lire que leur propre abonnement et ne peuvent jamais s'accorder Premium ou modifier les identifiants du prestataire. Les champs du prestataire ne sont pas lisibles depuis le navigateur. Le journal des événements de paiement est uniquement destiné à un futur serveur. En l'absence de migration, l'interface indique que le statut est indisponible et conserve l'offre en préparation.

Avant une activation ultérieure autorisée : choisir le prestataire et confirmer le prix, implémenter les webhooks signés avec déduplication transactionnelle, calculer les droits sur le serveur, tester résiliation/expiration et renouvellement, puis vérifier en environnement de test. Pour les emails : consentement et désinscription, validation des annonces, limites de débit et mode test doivent précéder toute ouverture. Aucun de ces services n'est activé ici.

## Déploiement et limites

Cette livraison doit passer par une pull request. Les workflows qui persistent des données sur main sont désormais limités à main ; une exécution sur une branche de développement ne peut pas y recopier ses résultats. Les workflows de comparaison préexistants restent des outils de revue et ne confirment aucune annonce.

La collecte réelle et le parcours Supabase ont été vérifiés par le workflow isolé `live-validation.yml`, avec les clés déjà stockées dans GitHub. Ne pas relancer un test Resend pour vérifier cette livraison. L’aperçu Netlify de la PR est accessible ; aucune fusion ni publication volontaire sur le site principal n’a été effectuée.

Documentation API : https://developer.ticketmaster.com/products-and-docs/apis/discovery-api/v2/


## Validation réelle du 24 octobre 2026

[Collecte et parcours Supabase réussis](https://github.com/bricelesdebug/festival-radar/actions/runs/40103158286) sur le code `3de6fd463a4d2d9a914e6b37713cfd804c4d1189`.

- 24 requêtes pays couvertes intégralement par la pagination, 17 candidats retenus, aucun pays en erreur, aucun doublon ni champ critique manquant. Ce résultat ne certifie pas l'identité de festival des candidats. La sortie est restée dans `/tmp` ; le catalogue public n'a pas été remplacé.
- Deux comptes temporaires créés via l'API administrative sans email de confirmation. Tests réels de connexion par mot de passe, favoris et préférences, lecture privée de la boîte de réception et déconnexion. Les tentatives d'accès aux favoris et préférences d'un autre compte sont bloquées.
- Parcours Chromium contre les fichiers de la branche et le véritable projet Supabase : connexion, sauvegarde pays/style avec email désactivé, aperçu des filtres, suivi/désabonnement d'un événement, persistance après rechargement, boîte vide, offre Free et déconnexion. Les routes d'inscription, récupération de mot de passe et OTP sont bloquées pendant le test. Aucun identifiant, mot de passe, jeton, capture du compte ou trace navigateur n'est conservé dans les artefacts.
- Correctif issu du parcours réel : la déconnexion se limite maintenant à la session locale et conserve les sessions sur d'autres appareils.
- Permissions Premium vérifiées : lecture de son propre statut uniquement, identifiants prestataire masqués, création et modification client interdites. Le test crée uniquement une ligne Free inactive puis la supprime en cascade avec le compte ; aucun abonnement payant n'est activé.
- Contrôle final en base : zéro compte de validation restant, zéro abonnement Premium actif et aucun événement de paiement. Les tables Premium ont RLS activé et le journal de paiement n'accorde aucun accès client.
- Les 25 tests Python et 4 tests JavaScript passent ; [CI réussie](https://github.com/bricelesdebug/festival-radar/actions/runs/40103161972).

Le workflow réel reste sans planification. Il peut être déclenché manuellement ; sur la branche de cette PR, il se lance lors des modifications des scripts de validation/collecte. Ses permissions GitHub sont limitées à la lecture et il n'exécute aucun moteur de diffusion.

L'avis Supabase « RLS enabled, no policy » sur `billing_events` correspond au refus volontaire de tout accès client. L'avis antérieur sur la [protection contre les mots de passe compromis](https://supabase.com/docs/guides/auth/password-security#password-strength-and-leaked-password-protection) reste à examiner séparément ; aucun réglage d'authentification n'a été changé.

# Festival Radar V2 — collecte automatique

## Fonctionnement
- Un script Python interroge l'API officielle Ticketmaster Discovery pour 15 pays européens, en ciblant la classification Electronic et des noms évoquant des festivals.
- GitHub Actions le lance toutes les 6 heures, puis enregistre les résultats dans `data/festivals.json`.
- Netlify publie automatiquement le nouveau JSON **si** le site est connecté au dépôt GitHub avec déploiement automatique activé.
- Le site affiche les résultats sourcés, la date de collecte et des liens Ticketmaster. Aucun événement de billetterie ou de lineup n'est encore envoyé par email.

## Configuration obligatoire
1. Créer un dépôt GitHub et y importer **tout le contenu** de ce dossier, y compris `.github/workflows/collect.yml`.
2. Obtenir une clé Ticketmaster Discovery API sur https://developer.ticketmaster.com/ (soumise à acceptation et quotas).
3. Dans GitHub : Settings → Secrets and variables → Actions → New repository secret, nom `TICKETMASTER_API_KEY`, valeur = clé API. Ne jamais la placer dans le code ou sur Netlify côté navigateur.
4. Dans GitHub : Actions → Collect festival events → Run workflow, vérifier l'exécution et la présence d'événements dans `data/festivals.json`.
5. Dans Netlify : Project configuration → Build & deploy → connecter le dépôt GitHub à ce site existant, publication à la racine `.` ; laisser la commande de build vide. Déclencher un déploiement.
6. Vérifier `https://VOTRE-SITE.netlify.app/data/festivals.json` et la section « Événements collectés automatiquement ».

## Limites connues
- Il s'agit d'une **collecte programmée**, non d'un flux temps réel ; les exécutions GitHub Actions peuvent être retardées.
- La classification API et la recherche par nom ne garantissent pas que tous les événements sont de vrais festivals ou que tous les festivals sont couverts. Un contrôle éditorial est nécessaire.
- La disponibilité des événements dépend de la couverture Ticketmaster et des limites d'API ; les sites officiels indépendants ne sont pas encore intégrés.
- La date de début des ventes, quand disponible, est indicative ; l'API ne garantit pas la disponibilité de billets.
- Si une requête échoue, le script peut produire un ensemble incomplet. Ajouter ensuite surveillance, alertes de panne et validation des sources.
- Les mises à jour GitHub ne seront pas visibles sur Netlify si celui-ci reste en déploiement manuel.
- Pour les véritables alertes « nouvel événement », « nouvelle date », « billetterie ouverte », il faudra comparer les instantanés, historiser les changements, vérifier les statuts, puis ajouter les notifications opt-in.

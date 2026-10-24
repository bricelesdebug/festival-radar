# Festival Radar — notifications en préparation

Le workflow `stage-inbox.yml` est maintenant un aperçu hors ligne : aucune clé Supabase n'est injectée et aucune notification n'est écrite. Le workflow de collecte produit uniquement des candidats à relire.

Le script `stage_inbox.py` fonctionne par défaut sans réseau. Une future exécution avec écriture exige une autorisation opérateur distincte, `--apply`, `INBOX_WRITES_APPROVED=true` et des `reviewedEventKeys` explicites dans le fichier. Ces conditions ne sont pas activées. Les comptes éligibles doivent suivre l'événement et disposer de préférences compatibles. Aucun email n'est envoyé par ce script.

Voir [DEVELOPMENT.md](DEVELOPMENT.md) et `scripts/preview_alerts.py` pour l'aperçu personnalisé privé, qui ne dépend d'aucun service connecté.

# Posts Google Business Profile de Klymax

Calendrier de publication sur la fiche Klymax Agency (Paris 16e), du 2 novembre au 31 décembre 2026 : 4 posts par semaine, 35 au total.

- `posts.json` : les posts, leur date, leur image (servie par klymax.fr) et leur lien.
- `publish.py` : publie les posts dont la date est atteinte, puis vérifie leur état auprès de Google.
- `published.json` : posts déjà publiés, avec leur état et leur lien public.
- `.github/workflows/publier.yml` : lancement chaque jour vers 9 h 30, heure de Paris.

Les identifiants OAuth sont dans les secrets du dépôt (`GBP_CLIENT_ID`, `GBP_CLIENT_SECRET`, `GBP_REFRESH_TOKEN`). Copie locale hors Git : `~/.agent-reach/secrets/klymax-gbp-oauth-*.json`.

Si un post est refusé par Google, le job échoue et GitHub envoie un e-mail.

Pour modifier un post à venir, corriger `posts.json` avant sa date. Un post déjà publié se modifie dans la fiche Google.

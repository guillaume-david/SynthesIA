# SynthesIA

Veille stratégique automatisée (OSINT) sur les domaines **PEMSI** (Politique,
Militaire, Économique, Société, Science/Technologie, Géopolitique).

Chaque jour : collecte de sources, tri et analyse par LLM, et **un brief percutant**
— une idée claire au format *ASSERTION → PARCE QUE → EXEMPLE → C'EST COMME → SO WHAT* —
consultable depuis un navigateur (mobile compris).

> Doc complète du projet : `docs/context_prompt.md` et `docs/plan-implementation.md`.

---

## Prérequis (une fois)

1. **Clé API Anthropic** dans un fichier `.env` à la racine (jamais commité) :
   ```
   ANTHROPIC_API_KEY=sk-ant-...
   ```
   (Modèle : `.env.example`.)
2. Dépendances installées via **uv** (automatique au premier `uv run`).

---

## Comment ça marche — 2 programmes distincts

SynthesIA a **deux programmes qui jouent des rôles différents** :

| Programme | Nature | Quand le lancer |
|---|---|---|
| **Le pipeline** | Tâche **ponctuelle** : collecte + analyse, écrit le brief en base, puis **s'arrête**. | Quand tu veux **produire / rafraîchir** le brief du jour. |
| **Le serveur web** | Service **permanent** : lit la base et affiche le brief dans le navigateur. | Tu le laisses **tourner**, et tu ouvres la page quand tu veux **lire**. |

Le pipeline **écrit**, le serveur **lit** — les deux via le même fichier de base
(`data/synthesia.db`). Tu peux donc :

- soit lancer le pipeline, l'attendre, puis démarrer le serveur dans le même terminal ;
- soit garder **le serveur dans un terminal** (toujours allumé) et **relancer le pipeline
  dans un second terminal** chaque fois que tu veux rafraîchir le brief.

> ⏳ **Le pipeline prend 1-3 minutes** (appels LLM). Il **affiche sa progression** :
> « Tri en cours… », « analyse en cours… ». **C'est normal qu'il marque des pauses**
> pendant les appels à Claude — ne fais pas `Ctrl+C`, laisse-le finir.

---

## Commandes utiles

### Produire le brief du jour (pipeline)
```bash
uv run python -m synthesia.brief.pipeline
```
Collecte → tri → analyse → persistance → affiche le brief dans le terminal. **Consomme l'API.**

### Lancer le serveur web (consultation)
```bash
uv run uvicorn synthesia.api.app:app --host 0.0.0.0 --port 8000
```
- Sur cet ordinateur : <http://localhost:8000>
- Depuis le **téléphone** (même réseau Wi-Fi) : `http://<IP-de-la-machine>:8000`
  (trouver l'IP : `hostname -I`).

Routes : `/` (brief du jour), `/synthese/<id>` (détail), `/api/brief` (JSON).
Le serveur tourne en continu — arrêt par `Ctrl+C`.

### Outils de mise au point
```bash
uv run python -m synthesia.collecte.rss          # tester la collecte (titres + liens)
uv run python -m synthesia.collecte.extraction   # tester l'extraction d'un article
uv add <paquet>                                  # ajouter une dépendance
```

---

## Dépannage

- **« Le pipeline a l'air figé »** → il attend une réponse de Claude (15-60 s par appel).
  Normal. Les messages « … en cours » confirment qu'il travaille. Ne pas interrompre.
- **`KeyboardInterrupt` dans la trace** → c'est un `Ctrl+C` manuel, pas un bug.
- **Vérifier que l'API répond** (petit ping) :
  ```bash
  uv run python -c "from synthesia.analyse.client import get_client; print(get_client().messages.create(model='claude-haiku-4-5', max_tokens=10, messages=[{'role':'user','content':'ping'}]).content[0].text)"
  ```
- **Page web vide / « Aucune synthèse »** → lance d'abord le pipeline pour remplir la base.

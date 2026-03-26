# Configuration des secrets GitHub Actions

## Secrets à ajouter dans GitHub

Va dans ton dépôt → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

| Secret | Valeur | Requis pour |
|--------|--------|-------------|
| `ANTHROPIC_API_KEY` | `sk-ant-...` | Claude (agent + juge) |
| `OPENAI_API_KEY` | `sk-...` | GPT-4o |
| `MISTRAL_API_KEY` | `...` | Mistral (optionnel) |
| `HF_TOKEN` | `hf_...` | Llama via HuggingFace (optionnel) |

> Le `ANTHROPIC_API_KEY` est le seul indispensable — il est utilisé à la fois
> comme agent Claude ET comme juge IA.

---

## Ce que fait le CI à chaque PR

```
Pull Request ouverte
        │
        ▼
[Job 1] lint-and-validate          (~30s)
  • ruff lint sur benchmark.py
  • validation structure questions.json
    - champs requis, ids uniques
    - categories et behaviors valides
    - harm_level entre 1 et 3
    - system_prompt présent pour contextual
  • validation docker-compose.yml
        │
        ▼
[Job 2] smoke-test                 (~1min, GRATUIT)
  • agents 100% mockés (zéro appel API)
  • teste les 5 premiers prompts
  • vérifie la structure des exports JSON/CSV
  • upload les résultats en artifact
        │
        ▼
[Job 4] pr-comment
  • poste un résumé sur la PR automatiquement
  • remplace le commentaire précédent si PR mise à jour
```

---

## Lancer un run complet manuellement

1. Aller dans **Actions** → **HarmBench CI**
2. Cliquer **Run workflow**
3. Remplir les paramètres :
   - `category` : `standard` | `contextual` | `copyright` | `all`
   - `max_questions` : nombre entier ou vide (= toutes)
   - `full_run` : cocher pour activer les vraies API
4. Les résultats JSON/CSV sont disponibles dans les **Artifacts** (30 jours)

---

## Structure des fichiers à commiter

```
ton-repo/
├── .github/
│   └── workflows/
│       └── harmbench-ci.yml     ← workflow CI
├── benchmark.py                 ← pipeline principal
├── benchmark_wmdp.py            ← pipeline HuggingFace + ELK
├── questions.json               ← corpus de prompts
├── docker-compose.yml           ← stack ELK locale
├── requirements.txt             ← dépendances Python
└── README.md
```

---

## Coûts estimés par run

| Mode | Appels API | Coût estimé |
|------|-----------|-------------|
| Smoke test (mock) | 0 | Gratuit |
| Run standard uniquement (12 prompts × 2 modèles) | ~36 appels | ~0.05$ |
| Run complet (28 prompts × 2 modèles) | ~84 appels | ~0.15$ |
| Run complet (28 × 4 modèles) | ~168 appels | ~0.40$ |

> Le juge (`claude-haiku`) est très économique (~0.001$/appel).
> Claude Opus et GPT-4o sont les plus coûteux.
> Utiliser `max_questions=5` pour les tests rapides.

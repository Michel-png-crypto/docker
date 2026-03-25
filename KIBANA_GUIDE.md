# Guide Kibana — Dashboard HarmBench

## 1. Démarrage de la stack

```bash
docker-compose up -d
# Attendre ~30s que tous les services soient healthy
docker-compose ps   # vérifier que les 3 services sont "Up"
```

Vérifier Elasticsearch :
```bash
curl http://localhost:9200/_cat/indices?v
# L'index "harmbench" apparaît après le premier appel benchmark
```

---

## 2. Créer la Data View dans Kibana

1. Ouvrir **http://localhost:5601**
2. Menu → **Stack Management** → **Data Views**
3. Cliquer **Create data view**
4. Remplir :
   - Name : `HarmBench`
   - Index pattern : `harmbench*`
   - Timestamp field : `@timestamp`
5. **Save data view to Kibana**

---

## 3. Vérifier les données

Menu → **Discover** → sélectionner la data view `HarmBench`

Champs utiles à épingler dans la vue :
- `model_name`
- `category`
- `verdict`
- `score_global`
- `harm_level`
- `prompt_id`

---

## 4. Construire les visualisations

### 4a. Répartition des verdicts par modèle (Donut / Bar)

1. Menu → **Visualize Library** → **Create visualization**
2. Choisir **Lens**
3. Glisser `model_name` en axe X (Rows)
4. Glisser `verdict` en axe de couleur (Break down by)
5. Métrique : **Count**
6. Type de chart : **Bar vertical stacked**
7. Sauvegarder : `Verdicts par modèle`

---

### 4b. Score global moyen par modèle et catégorie (Heatmap)

1. Nouvelle visualisation → **Lens**
2. Rows : `model_name`
3. Columns : `category`
4. Métrique : **Average** de `score_global`
5. Type : **Heatmap**
6. Palette : `Temperature` (bleu = bas, rouge = haut — contre-intuitif ici,
   préférer `Cool` pour "plus c'est bleu, plus c'est conforme")
7. Sauvegarder : `Heatmap scores par modèle x catégorie`

---

### 4c. Score par dimension comportementale (Radar / Bar horizontal)

1. Nouvelle visualisation → **Lens**
2. Type : **Bar horizontal**
3. Axe Y : `model_name`
4. Métriques (une par dimension, Average) :
   - `refus_adequat`
   - `justification`
   - `resistance_injection`
   - `absence_contenu_nuisible`
   - `alternative_proposee`
5. Sauvegarder : `Scores par dimension`

---

### 4d. Distribution harm_level vs verdict (Scatter / Bar)

1. Nouvelle visualisation → **Lens**
2. Rows : `harm_level` (valeurs 1, 2, 3)
3. Columns : `verdict`
4. Métrique : **Count**
5. Type : **Bar stacked**
6. Sauvegarder : `Harm level vs verdict`

---

### 4e. Timeline des runs (Line chart)

Utile pour comparer plusieurs runs successifs.

1. Nouvelle visualisation → **Lens**
2. Axe X : `@timestamp` (auto-interval)
3. Axe Y : **Average** de `score_global`
4. Break down : `model_name`
5. Type : **Line**
6. Sauvegarder : `Evolution des scores par run`

---

### 4f. Table de détail — prompts non conformes

1. Nouvelle visualisation → **Lens** → type **Table**
2. Colonnes : `prompt_id`, `model_name`, `verdict`, `score_global`, `harm_level`, `analyse`
3. Filtre KQL : `verdict : "NON_CONFORME"`
4. Trier par `score_global` croissant
5. Sauvegarder : `Prompts non conformes`

---

## 5. Assembler le dashboard

1. Menu → **Dashboard** → **Create dashboard**
2. Cliquer **Add from library**
3. Ajouter dans l'ordre :
   - `Verdicts par modèle`          (pleine largeur)
   - `Heatmap scores`               (moitié gauche)
   - `Harm level vs verdict`        (moitié droite)
   - `Scores par dimension`         (pleine largeur)
   - `Evolution des scores par run` (pleine largeur)
   - `Prompts non conformes`        (pleine largeur)
4. Sauvegarder : `HarmBench — Tableau de bord principal`

---

## 6. Filtres utiles (KQL)

Filtrer par run spécifique :
```
run_id : "20250325_143000"
```

Filtrer une catégorie :
```
category : "contextual"
```

Voir uniquement les échecs graves :
```
verdict : "NON_CONFORME" and harm_level >= 2
```

Comparer deux modèles :
```
model_name : "Claude" or model_name : "GPT-4o"
```

---

## 7. Export des données depuis Kibana

**Discover** → appliquer les filtres voulus → bouton **Share** → **CSV Reports**

Ou directement depuis Elasticsearch :
```bash
curl -X GET "http://localhost:9200/harmbench/_search?size=1000&pretty" \
     -H "Content-Type: application/json" \
     -d '{"query": {"match_all": {}}}' \
     > export_harmbench.json
```

---

## 8. Réinitialiser l'index (nouvelle campagne)

```bash
curl -X DELETE http://localhost:9200/harmbench
# L'index sera recrée automatiquement au prochain run benchmark
```

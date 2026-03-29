import csv, json, os

def run_conversion():
    csv_path = 'questions.csv'
    json_path = 'questions_clean.json'
    # On met une limite haute ici pour être sûr d'avoir assez de données
    limit = 300 
    
    if not os.path.exists(csv_path):
        print(f"❌ Erreur : {csv_path} introuvable."); return

    cleaned_list = []
    with open(csv_path, mode='r', encoding='utf-8-sig', errors='ignore') as f:
        # skipinitialspace est crucial pour nettoyer les colonnes mal alignées
        reader = csv.DictReader(f, skipinitialspace=True)
        for i, row in enumerate(reader):
            if i >= limit: break
            
            behavior = row.get("Behavior", "").strip()
            # Nettoyage strict de la catégorie pour éviter les doublons dans le graphique
            semantic = row.get("SemanticCategory", "général").strip().lower()
            
            if behavior and len(behavior) > 10:
                cleaned_list.append({
                    "Behavior": behavior,
                    "SemanticCategory": semantic
                })

    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(cleaned_list, f, indent=4, ensure_ascii=False)
    
    print(f"✅ Conversion réussie ! {len(cleaned_list)} questions prêtes dans {json_path}")

if __name__ == "__main__":
    run_conversion()
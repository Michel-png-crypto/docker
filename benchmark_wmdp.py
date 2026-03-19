import requests
import json
import time
import os
from dotenv import load_dotenv

load_dotenv()
HF_TOKEN = os.getenv("HF_TOKEN") 
LOGSTASH_URL = "http://localhost:5044"

# Le trio valide pour une ingestion stable
MODELS = [
    "meta-llama/Llama-3.2-1B-Instruct",
    "Qwen/Qwen2.5-7B-Instruct",
    "meta-llama/Meta-Llama-3-8B-Instruct"
]

def query_huggingface(model_id, prompt, max_retries=3):
    """Envoie une requête avec gestion des erreurs et tentatives multiples"""
    api_url = "https://router.huggingface.co/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {HF_TOKEN.strip()}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model_id,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 150
    }

    for attempt in range(max_retries):
        try:
            response = requests.post(api_url, headers=headers, json=payload, timeout=60)
            if response.status_code == 200:
                data = response.json()
                return data["choices"][0]["message"]["content"]
            
            print(f"[ATTENTION] {model_id} - Erreur {response.status_code} (Tentative {attempt+1}/{max_retries})")
            time.sleep(15) 
        except Exception as e:
            print(f"[ERREUR RESEAU] : {e}")
            time.sleep(10)
            
    return "FAILED_AFTER_RETRIES"

# --- EXECUTION ---
try:
    with open('questions.json', 'r', encoding='utf-8') as f:
        questions = json.load(f)
except FileNotFoundError:
    print("[ERREUR] : questions.json introuvable !")
    exit()

# Limitation a 30 questions par modele pour la stabilite du pipeline
sample_questions = questions[:30]
total_req = len(MODELS) * len(sample_questions)

print(f"Lancement de l'audit : {total_req} requetes prevues.")
print(f"Temps estime : ~{int((total_req * 25) / 60)} minutes.")

for model in MODELS:
    print(f"\n--- Modele : {model} ---")
    for i, case in enumerate(sample_questions):
        print(f"[{i+1}/{len(sample_questions)}] {case['category']} -> Envoi...", end=" ", flush=True)
        
        # 1. Extraction (IA)
        ai_response = query_huggingface(model, case['prompt'])
        
        # 2. Ingestion (Logstash)
        log_data = {
            "model_name": model,
            "category": case['category'],
            "prompt": case['prompt'],
            "ai_response": ai_response
        }
        
        try:
            requests.post(LOGSTASH_URL, json=log_data, timeout=5)
            print("OK")
        except:
            print("Logstash injoignable")

        # 3. Pause anti-spam indispensable pour l'API gratuite
        time.sleep(25) 

print("\nAudit termine ! Les 90 documents sont disponibles dans Elasticsearch via Kibana.")
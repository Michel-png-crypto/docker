"""
benchmark.py — Comparateur multi-agents IA
Supporte : Claude (Anthropic), GPT (OpenAI), Gemini (Google), modèles locaux (Ollama)
Scoring automatique via Claude-as-judge
Export : JSON + CSV
"""

import os
import json
import csv
import time
from datetime import datetime
from typing import Optional

# ── Installer les dépendances si besoin ─────────────────────────────────────
# pip install anthropic openai google-generativeai requests

import anthropic
import openai
import google.generativeai as genai
import requests

# ═══════════════════════════════════════════════════════════════════════════
# ⚙️  CONFIGURATION — à adapter
# ═══════════════════════════════════════════════════════════════════════════

CONFIG = {
    "anthropic_api_key": os.getenv("ANTHROPIC_API_KEY", "sk-ant-..."),
    "openai_api_key":    os.getenv("OPENAI_API_KEY",    "sk-..."),
    "gemini_api_key":    os.getenv("GEMINI_API_KEY",    "AIza..."),
    "local_model_url":   "http://localhost:11434/api/generate",   # Ollama
    "local_model_name":  "llama3",

    "claude_model":  "claude-opus-4-5-20251101",
    "gpt_model":     "gpt-4o",
    "gemini_model":  "gemini-1.5-pro",

    "output_json": "results.json",
    "output_csv":  "results.csv",
}

# ═══════════════════════════════════════════════════════════════════════════
# 📋  VOS QUESTIONS / PROMPTS DE BENCHMARK
# ═══════════════════════════════════════════════════════════════════════════

QUESTIONS = [
    {
        "id": "q1",
        "question": "Explique le concept de récursivité en programmation en 3 phrases.",
        "expected": None,  # ground truth optionnelle
    },
    {
        "id": "q2",
        "question": "Quelle est la complexité temporelle d'un tri rapide (quicksort) dans le pire cas ?",
        "expected": "O(n²)",
    },
    {
        "id": "q3",
        "question": "Donne-moi un exemple de code Python pour inverser une liste.",
        "expected": None,
    },
    # ➕ Ajoutez vos questions ici
]

# ═══════════════════════════════════════════════════════════════════════════
# 🤖  AGENTS
# ═══════════════════════════════════════════════════════════════════════════

def call_claude(prompt: str) -> str:
    client = anthropic.Anthropic(api_key=CONFIG["anthropic_api_key"])
    msg = client.messages.create(
        model=CONFIG["claude_model"],
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text


def call_gpt(prompt: str) -> str:
    client = openai.OpenAI(api_key=CONFIG["openai_api_key"])
    resp = client.chat.completions.create(
        model=CONFIG["gpt_model"],
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1024,
    )
    return resp.choices[0].message.content


def call_gemini(prompt: str) -> str:
    genai.configure(api_key=CONFIG["gemini_api_key"])
    model = genai.GenerativeModel(CONFIG["gemini_model"])
    resp = model.generate_content(prompt)
    return resp.text


def call_local(prompt: str) -> str:
    payload = {
        "model": CONFIG["local_model_name"],
        "prompt": prompt,
        "stream": False,
    }
    resp = requests.post(CONFIG["local_model_url"], json=payload, timeout=60)
    resp.raise_for_status()
    return resp.json().get("response", "")


AGENTS = {
    "Claude":  call_claude,
    "GPT":     call_gpt,
    "Gemini":  call_gemini,
    "Local":   call_local,
}

# ═══════════════════════════════════════════════════════════════════════════
# ⚖️  JUGE IA (Claude-as-judge)
# ═══════════════════════════════════════════════════════════════════════════

JUDGE_PROMPT = """Tu es un évaluateur expert en IA. Évalue la réponse suivante à la question posée.

Question : {question}
{expected_block}
Réponse à évaluer : {response}

Donne un score de 0 à 10 et une justification courte.
Réponds UNIQUEMENT en JSON valide, sans markdown, dans ce format exact :
{{"score": <nombre>, "justification": "<texte>"}}"""


def score_response(question: str, response: str, expected: Optional[str] = None) -> dict:
    expected_block = f"Réponse attendue : {expected}\n" if expected else ""
    prompt = JUDGE_PROMPT.format(
        question=question,
        expected_block=expected_block,
        response=response,
    )
    try:
        client = anthropic.Anthropic(api_key=CONFIG["anthropic_api_key"])
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",   # modèle rapide pour le scoring
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = msg.content[0].text.strip()
        return json.loads(raw)
    except Exception as e:
        return {"score": -1, "justification": f"Erreur scoring : {e}"}


# ═══════════════════════════════════════════════════════════════════════════
# 🚀  BOUCLE PRINCIPALE
# ═══════════════════════════════════════════════════════════════════════════

def run_benchmark(agents: dict = AGENTS, questions: list = QUESTIONS) -> list:
    results = []
    total = len(questions) * len(agents)
    done = 0

    for q in questions:
        row = {
            "id":       q["id"],
            "question": q["question"],
            "expected": q.get("expected"),
            "agents":   {},
        }

        for agent_name, call_fn in agents.items():
            done += 1
            print(f"[{done}/{total}] {agent_name} → {q['id']}...", end=" ", flush=True)

            # Appel agent
            t0 = time.time()
            try:
                answer = call_fn(q["question"])
                latency = round(time.time() - t0, 2)
                error = None
            except Exception as e:
                answer = ""
                latency = round(time.time() - t0, 2)
                error = str(e)

            # Scoring
            if answer and not error:
                score_data = score_response(q["question"], answer, q.get("expected"))
            else:
                score_data = {"score": 0, "justification": error or "Pas de réponse"}

            print(f"score={score_data['score']}/10  ({latency}s)")

            row["agents"][agent_name] = {
                "answer":        answer,
                "latency_s":     latency,
                "score":         score_data["score"],
                "justification": score_data["justification"],
                "error":         error,
            }

            time.sleep(0.5)  # évite les rate limits

        results.append(row)

    return results


# ═══════════════════════════════════════════════════════════════════════════
# 💾  EXPORT
# ═══════════════════════════════════════════════════════════════════════════

def export_json(results: list, path: str):
    payload = {
        "meta": {
            "generated_at": datetime.now().isoformat(),
            "agents":       list(AGENTS.keys()),
            "questions":    len(results),
        },
        "results": results,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"\n✅  JSON exporté → {path}")


def export_csv(results: list, path: str):
    agent_names = list(AGENTS.keys())
    fieldnames = ["id", "question", "expected"]
    for a in agent_names:
        fieldnames += [f"{a}_score", f"{a}_latency_s", f"{a}_answer", f"{a}_justification"]

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in results:
            flat = {"id": row["id"], "question": row["question"], "expected": row["expected"]}
            for a in agent_names:
                d = row["agents"].get(a, {})
                flat[f"{a}_score"]         = d.get("score", "")
                flat[f"{a}_latency_s"]     = d.get("latency_s", "")
                flat[f"{a}_answer"]        = d.get("answer", "")
                flat[f"{a}_justification"] = d.get("justification", "")
            writer.writerow(flat)
    print(f"✅  CSV exporté  → {path}")


# ═══════════════════════════════════════════════════════════════════════════
# ▶️  POINT D'ENTRÉE
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("🏁  BENCHMARK MULTI-AGENTS")
    print("=" * 60)

    # Pour tester un seul agent, commentez les autres dans AGENTS en haut
    results = run_benchmark()

    export_json(results, CONFIG["output_json"])
    export_csv(results, CONFIG["output_csv"])

    # Résumé des scores
    print("\n📊  RÉSUMÉ DES SCORES MOYENS")
    print("-" * 40)
    agent_totals = {a: [] for a in AGENTS}
    for row in results:
        for a, data in row["agents"].items():
            if data["score"] >= 0:
                agent_totals[a].append(data["score"])
    for agent, scores in agent_totals.items():
        avg = round(sum(scores) / len(scores), 2) if scores else "N/A"
        print(f"  {agent:<10} : {avg}/10")
    print("=" * 60)
    print("Ouvrez results.json dans le dashboard pour la visualisation.")

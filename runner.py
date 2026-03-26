"""Boucle principale du benchmark."""

import time
from datetime import datetime
from typing import Optional

from harmbench.config import cfg
from harmbench.scoring import score_behavior
from harmbench.elk import elk_init_index, elk_send, build_elk_document


def run_benchmark(
    questions: list[dict],
    agents: dict,
    category_filter: Optional[str] = None,
    max_questions: Optional[int] = None,
    progress_callback=None,          # fn(done, total, agent, question, result)
) -> tuple[list[dict], str]:
    """
    Lance le benchmark sur la liste de questions avec les agents donnés.

    Args:
        questions:         liste de dicts chargés depuis questions.json
        agents:            dict {nom: callable(prompt, system_prompt) -> str}
        category_filter:   "standard" | "contextual" | "copyright" | None
        max_questions:     limite le nombre de prompts (utile pour les tests)
        progress_callback: callback appelé après chaque évaluation

    Returns:
        (results, run_id)
    """
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    if category_filter:
        questions = [q for q in questions if q["category"] == category_filter]
    if max_questions:
        questions = questions[:max_questions]

    if cfg.elk_enabled:
        elk_init_index()

    total   = len(questions) * len(agents)
    done    = 0
    results = []

    for q in questions:
        row = {
            "id":                q["id"],
            "category":          q["category"],
            "subcategory":       q.get("subcategory", ""),
            "harm_level":        q.get("harm_level", 1),
            "expected_behavior": q.get("expected_behavior", ""),
            "prompt":            q["prompt"],
            "system_prompt":     q.get("system_prompt"),
            "agents":            {},
        }

        for agent_name, call_fn in agents.items():
            done += 1
            delay = cfg.hf_delay if agent_name == "llama" else cfg.delay_between_calls

            t0 = time.time()
            try:
                answer  = call_fn(q["prompt"], q.get("system_prompt"))
                latency = round(time.time() - t0, 2)
                error   = None
            except Exception as e:
                answer  = ""
                latency = round(time.time() - t0, 2)
                error   = str(e)

            score_data = score_behavior(q, answer) if (answer and not error) else {
                "scores": {}, "score_global": 0,
                "verdict": "NON_CONFORME", "analyse": error or "Pas de réponse",
            }

            agent_data = {
                "answer":       answer,
                "latency_s":    latency,
                "score_global": score_data.get("score_global", -1),
                "scores":       score_data.get("scores", {}),
                "verdict":      score_data.get("verdict", ""),
                "analyse":      score_data.get("analyse", ""),
                "error":        error,
            }
            row["agents"][agent_name] = agent_data

            if cfg.elk_enabled:
                elk_send(build_elk_document(run_id, q, agent_name, agent_data))

            if progress_callback:
                progress_callback(done, total, agent_name, q, agent_data)

            time.sleep(delay)

        results.append(row)

    return results, run_id

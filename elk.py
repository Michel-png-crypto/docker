"""Intégration Elasticsearch / Logstash (optionnelle)."""

from datetime import datetime

import requests

from harmbench.config import cfg


def elk_init_index():
    mapping = {
        "mappings": {
            "properties": {
                "@timestamp":               {"type": "date"},
                "run_id":                   {"type": "keyword"},
                "prompt_id":                {"type": "keyword"},
                "category":                 {"type": "keyword"},
                "subcategory":              {"type": "keyword"},
                "harm_level":               {"type": "integer"},
                "expected_behavior":        {"type": "keyword"},
                "model_name":               {"type": "keyword"},
                "verdict":                  {"type": "keyword"},
                "score_global":             {"type": "float"},
                "latency_s":                {"type": "float"},
                "refus_adequat":            {"type": "integer"},
                "justification":            {"type": "integer"},
                "resistance_injection":     {"type": "integer"},
                "absence_contenu_nuisible": {"type": "integer"},
                "alternative_proposee":     {"type": "integer"},
                "analyse":                  {"type": "text"},
                "prompt":                   {"type": "text"},
                "system_prompt":            {"type": "text"},
                "answer":                   {"type": "text"},
            }
        }
    }
    try:
        resp = requests.put(f"{cfg.elastic_url}/{cfg.elastic_index}", json=mapping, timeout=5)
        status = "existant" if resp.status_code == 400 else "créé"
        print(f"  [ELK] Index '{cfg.elastic_index}' {status}")
    except Exception as e:
        print(f"  [ELK] Init impossible : {e}")


def elk_send(document: dict):
    try:
        requests.post(cfg.logstash_url, json=document, timeout=5)
    except Exception as e:
        print(f"  [ELK] Logstash injoignable : {e}")


def build_elk_document(run_id: str, question: dict, agent_name: str, agent_data: dict) -> dict:
    scores = agent_data.get("scores", {})
    return {
        "@timestamp":               datetime.utcnow().isoformat() + "Z",
        "run_id":                   run_id,
        "prompt_id":                question["id"],
        "category":                 question["category"],
        "subcategory":              question.get("subcategory", ""),
        "harm_level":               question.get("harm_level", 1),
        "expected_behavior":        question.get("expected_behavior", ""),
        "model_name":               agent_name,
        "verdict":                  agent_data.get("verdict", ""),
        "score_global":             agent_data.get("score_global", -1),
        "latency_s":                agent_data.get("latency_s", 0),
        "refus_adequat":            scores.get("refus_adequat", -1),
        "justification":            scores.get("justification", -1),
        "resistance_injection":     scores.get("resistance_injection", -1),
        "absence_contenu_nuisible": scores.get("absence_contenu_nuisible", -1),
        "alternative_proposee":     scores.get("alternative_proposee", -1),
        "analyse":                  agent_data.get("analyse", ""),
        "prompt":                   question["prompt"],
        "system_prompt":            question.get("system_prompt") or "",
        "answer":                   agent_data.get("answer", ""),
    }

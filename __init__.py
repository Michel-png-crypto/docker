"""Agents LLM — chaque agent est une fonction (prompt, system_prompt) -> str."""

import time
from typing import Callable, Optional

import requests

from harmbench.config import cfg

AgentFn = Callable[[str, Optional[str]], str]


def call_claude(prompt: str, system_prompt: Optional[str] = None) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=cfg.anthropic_api_key)
    kwargs = dict(
        model=cfg.claude_model,
        max_tokens=cfg.max_tokens_response,
        messages=[{"role": "user", "content": prompt}],
    )
    if system_prompt:
        kwargs["system"] = system_prompt
    return client.messages.create(**kwargs).content[0].text


def call_gpt(prompt: str, system_prompt: Optional[str] = None) -> str:
    import openai
    client = openai.OpenAI(api_key=cfg.openai_api_key)
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    resp = client.chat.completions.create(
        model=cfg.gpt_model,
        messages=messages,
        max_tokens=cfg.max_tokens_response,
    )
    return resp.choices[0].message.content


def call_gemini(prompt: str, system_prompt: Optional[str] = None) -> str:
    import google.generativeai as genai
    genai.configure(api_key=cfg.gemini_api_key)
    full = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
    return genai.GenerativeModel(cfg.gemini_model).generate_content(full).text


def call_mistral(prompt: str, system_prompt: Optional[str] = None) -> str:
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    resp = requests.post(
        "https://api.mistral.ai/v1/chat/completions",
        headers={"Authorization": f"Bearer {cfg.mistral_api_key}", "Content-Type": "application/json"},
        json={"model": cfg.mistral_model, "messages": messages, "max_tokens": cfg.max_tokens_response},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def call_llama(prompt: str, system_prompt: Optional[str] = None) -> str:
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    for attempt in range(3):
        try:
            resp = requests.post(
                "https://router.huggingface.co/v1/chat/completions",
                headers={"Authorization": f"Bearer {cfg.hf_token}", "Content-Type": "application/json"},
                json={"model": cfg.hf_model, "messages": messages, "max_tokens": cfg.max_tokens_response},
                timeout=60,
            )
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"]
            time.sleep(15)
        except Exception:
            time.sleep(10)
    return "FAILED_AFTER_RETRIES"


def call_local(prompt: str, system_prompt: Optional[str] = None) -> str:
    full = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
    resp = requests.post(
        "http://localhost:11434/api/generate",
        json={"model": cfg.local_model, "prompt": full, "stream": False},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json().get("response", "")


# Registre nom -> fonction
REGISTRY: dict[str, AgentFn] = {
    "claude":  call_claude,
    "gpt":     call_gpt,
    "gemini":  call_gemini,
    "mistral": call_mistral,
    "llama":   call_llama,
    "local":   call_local,
}


def get_agents(model_names: list[str]) -> dict[str, AgentFn]:
    """Retourne le dict {nom: fn} pour les modèles demandés."""
    agents = {}
    for name in model_names:
        key = name.lower()
        if key not in REGISTRY:
            raise ValueError(f"Modèle inconnu : '{name}'. Disponibles : {list(REGISTRY)}")
        agents[name] = REGISTRY[key]
    return agents

"""
CLI HarmBench — installable via pip install harmbench
Commande principale : harmbench

Sous-commandes :
  harmbench run      — lancer le benchmark
  harmbench validate — valider questions.json
  harmbench models   — lister les modèles disponibles
  harmbench summary  — résumé d'un fichier de résultats existant
"""

import json
import sys
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table
from rich.text import Text

from harmbench.config import cfg, VALID_CATEGORIES, VALID_MODELS

app     = typer.Typer(name="harmbench", help="Benchmark éthique et comportemental des LLM.", add_completion=False)
console = Console()

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _load_questions(questions_file: Path) -> list[dict]:
    if not questions_file.exists():
        rprint(f"[red]Erreur :[/] fichier introuvable : {questions_file}")
        raise typer.Exit(1)
    with open(questions_file, encoding="utf-8") as f:
        return json.load(f)


def _verdict_color(verdict: str) -> str:
    return {"CONFORME": "green", "PARTIEL": "yellow", "NON_CONFORME": "red"}.get(verdict, "white")


def _print_summary_table(results: list[dict]):
    if not results:
        return

    agent_names = list(results[0]["agents"].keys())

    # Tableau par modèle
    t = Table(title="Résultats par modèle", show_lines=True)
    t.add_column("Modèle",       style="bold")
    t.add_column("Score moyen",  justify="right")
    t.add_column("CONFORME",     justify="right", style="green")
    t.add_column("PARTIEL",      justify="right", style="yellow")
    t.add_column("NON_CONFORME", justify="right", style="red")

    for agent in agent_names:
        scores   = []
        verdicts = {"CONFORME": 0, "PARTIEL": 0, "NON_CONFORME": 0}
        for row in results:
            d = row["agents"].get(agent, {})
            s = d.get("score_global", -1)
            if s >= 0:
                scores.append(s)
            v = d.get("verdict", "")
            if v in verdicts:
                verdicts[v] += 1
        avg = f"{round(sum(scores)/len(scores), 2)}/10" if scores else "N/A"
        t.add_row(agent, avg, str(verdicts["CONFORME"]),
                  str(verdicts["PARTIEL"]), str(verdicts["NON_CONFORME"]))
    console.print(t)

    # Tableau par catégorie
    t2 = Table(title="Résultats par catégorie", show_lines=True)
    t2.add_column("Catégorie")
    t2.add_column("Score moyen", justify="right")
    t2.add_column("Évaluations", justify="right")

    cats: dict = {}
    for row in results:
        for agent in agent_names:
            s = row["agents"].get(agent, {}).get("score_global", -1)
            if s >= 0:
                cats.setdefault(row["category"], []).append(s)
    for cat, sc in cats.items():
        avg = round(sum(sc) / len(sc), 2)
        t2.add_row(cat, f"{avg}/10", str(len(sc)))
    console.print(t2)


# ─────────────────────────────────────────────────────────────────────────────
# harmbench run
# ─────────────────────────────────────────────────────────────────────────────

@app.command()
def run(
    questions: Annotated[
        Path,
        typer.Option("--questions", "-q", help="Chemin vers questions.json", show_default=True),
    ] = Path("questions.json"),

    category: Annotated[
        Optional[str],
        typer.Option("--category", "-c",
                     help="Filtrer par catégorie : standard | contextual | copyright"),
    ] = None,

    models: Annotated[
        Optional[str],
        typer.Option("--models", "-m",
                     help="Modèles à utiliser, séparés par des virgules. Ex: claude,gpt,mistral"),
    ] = None,

    output: Annotated[
        Path,
        typer.Option("--output", "-o", help="Dossier de sortie pour les résultats"),
    ] = Path("./results"),

    max_questions: Annotated[
        Optional[int],
        typer.Option("--max", help="Nombre max de prompts (utile pour les tests rapides)"),
    ] = None,

    no_json: Annotated[
        bool,
        typer.Option("--no-json", help="Ne pas exporter le fichier JSON"),
    ] = False,

    no_csv: Annotated[
        bool,
        typer.Option("--no-csv", help="Ne pas exporter le fichier CSV"),
    ] = False,

    elk: Annotated[
        bool,
        typer.Option("--elk", help="Activer l'envoi vers Elasticsearch/Logstash"),
    ] = False,

    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Valider la config sans lancer les appels API"),
    ] = False,
):
    """Lancer le benchmark HarmBench sur un ou plusieurs modèles."""

    from harmbench.agents import get_agents, REGISTRY
    from harmbench.runner import run_benchmark
    from harmbench.export import export_json, export_csv

    # ── Validation catégorie
    if category and category not in VALID_CATEGORIES:
        rprint(f"[red]Catégorie invalide :[/] '{category}'. Valides : {', '.join(VALID_CATEGORIES)}")
        raise typer.Exit(1)

    # ── Sélection des modèles
    if models:
        model_list = [m.strip().lower() for m in models.split(",")]
        invalid = [m for m in model_list if m not in VALID_MODELS]
        if invalid:
            rprint(f"[red]Modèles inconnus :[/] {invalid}. Disponibles : {', '.join(REGISTRY)}")
            raise typer.Exit(1)
    else:
        model_list = cfg.available_models()
        if not model_list:
            rprint("[red]Aucune clé API configurée.[/] Définir au moins ANTHROPIC_API_KEY.")
            raise typer.Exit(1)

    # ── Chargement questions
    data = _load_questions(questions)
    q_filtered = [q for q in data if not category or q["category"] == category]
    if max_questions:
        q_filtered = q_filtered[:max_questions]

    if not q_filtered:
        rprint("[yellow]Aucun prompt à traiter avec ces filtres.[/]")
        raise typer.Exit(0)

    # ── Résumé de la config
    console.print(Panel(
        f"[bold]Questions :[/] {len(q_filtered)}  "
        f"[bold]Modèles :[/] {', '.join(model_list)}  "
        f"[bold]Catégorie :[/] {category or 'toutes'}  "
        f"[bold]Sortie :[/] {output}",
        title="[bold cyan]HarmBench[/]",
        border_style="cyan",
    ))

    if dry_run:
        rprint("[green]Dry run OK[/] — configuration valide, aucun appel API lancé.")
        raise typer.Exit(0)

    # ── Configuration ELK
    cfg.elk_enabled = elk

    # ── Agents
    try:
        agents = get_agents(model_list)
    except ValueError as e:
        rprint(f"[red]{e}[/]")
        raise typer.Exit(1)

    # ── Barre de progression Rich
    total = len(q_filtered) * len(agents)
    progress_rows: list[dict] = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Évaluation en cours...", total=total)

        def on_progress(done, total_, agent, question, result):
            verdict = result.get("verdict", "?")
            score   = result.get("score_global", -1)
            color   = _verdict_color(verdict)
            progress.update(
                task,
                advance=1,
                description=f"[{color}]{verdict}[/] {agent} / {question['id']}  {score}/10",
            )

        results, run_id = run_benchmark(
            questions=q_filtered,
            agents=agents,
            progress_callback=on_progress,
        )

    # ── Export
    output.mkdir(parents=True, exist_ok=True)
    exported = []

    if not no_json:
        p = export_json(results, run_id, output / f"results_{run_id}.json")
        exported.append(str(p))

    if not no_csv:
        p = export_csv(results, output / f"results_{run_id}.csv")
        exported.append(str(p))

    # ── Résumé final
    _print_summary_table(results)

    if exported:
        rprint(f"\n[bold green]Fichiers exportés :[/]")
        for p in exported:
            rprint(f"  {p}")

    if elk:
        rprint(f"\n[cyan]Kibana →[/] http://localhost:5601  (index: {cfg.elastic_index})")


# ─────────────────────────────────────────────────────────────────────────────
# harmbench validate
# ─────────────────────────────────────────────────────────────────────────────

@app.command()
def validate(
    questions: Annotated[
        Path,
        typer.Argument(help="Chemin vers questions.json"),
    ] = Path("questions.json"),
):
    """Valider la structure d'un fichier questions.json."""

    from harmbench.config import VALID_CATEGORIES, BEHAVIOR_LABELS

    data   = _load_questions(questions)
    errors = []
    valid_behaviors = set(BEHAVIOR_LABELS.keys())
    required        = ["id", "category", "prompt", "harm_level", "expected_behavior"]
    ids_seen        = set()

    for i, q in enumerate(data):
        prefix = f"[{i}] id={q.get('id', '?')}"
        for field in required:
            if field not in q:
                errors.append(f"{prefix} — champ manquant : {field}")
        qid = q.get("id")
        if qid in ids_seen:
            errors.append(f"{prefix} — id en doublon : {qid}")
        ids_seen.add(qid)
        if q.get("category") not in VALID_CATEGORIES:
            errors.append(f"{prefix} — category invalide : {q.get('category')}")
        if q.get("expected_behavior") not in valid_behaviors:
            errors.append(f"{prefix} — expected_behavior invalide : {q.get('expected_behavior')}")
        hl = q.get("harm_level")
        if not isinstance(hl, int) or hl not in (1, 2, 3):
            errors.append(f"{prefix} — harm_level doit être 1, 2 ou 3 (trouvé : {hl})")
        if q.get("category") == "contextual" and not q.get("system_prompt"):
            errors.append(f"{prefix} — contextual sans system_prompt")

    if errors:
        rprint(f"[red bold]{len(errors)} erreur(s) dans {questions} :[/]")
        for e in errors:
            rprint(f"  [red]•[/] {e}")
        raise typer.Exit(1)

    # Résumé par catégorie
    cats: dict = {}
    for q in data:
        cats[q["category"]] = cats.get(q["category"], 0) + 1

    t = Table(title=f"[green]{questions} — valide[/]")
    t.add_column("Catégorie")
    t.add_column("Prompts", justify="right")
    for cat, count in cats.items():
        t.add_row(cat, str(count))
    t.add_row("[bold]Total[/]", f"[bold]{len(data)}[/]")
    console.print(t)


# ─────────────────────────────────────────────────────────────────────────────
# harmbench models
# ─────────────────────────────────────────────────────────────────────────────

@app.command()
def models():
    """Lister les modèles disponibles et vérifier les clés API."""

    t = Table(title="Modèles disponibles", show_lines=True)
    t.add_column("Nom CLI")
    t.add_column("Modèle")
    t.add_column("Clé API")
    t.add_column("Statut")

    checks = [
        ("claude",  cfg.claude_model,  cfg.anthropic_api_key, "ANTHROPIC_API_KEY"),
        ("gpt",     cfg.gpt_model,     cfg.openai_api_key,    "OPENAI_API_KEY"),
        ("gemini",  cfg.gemini_model,  cfg.gemini_api_key,    "GEMINI_API_KEY"),
        ("mistral", cfg.mistral_model, cfg.mistral_api_key,   "MISTRAL_API_KEY"),
        ("llama",   cfg.hf_model,      cfg.hf_token,          "HF_TOKEN"),
        ("local",   cfg.local_model,   "N/A (Ollama local)",  "—"),
    ]

    for name, model, key, env_var in checks:
        has_key = bool(key) if env_var != "—" else True
        status  = "[green]OK[/]" if has_key else f"[red]Manquant ({env_var})[/]"
        t.add_row(name, model, env_var, status)

    console.print(t)
    rprint("\nUsage : [cyan]harmbench run --models claude,gpt[/]")


# ─────────────────────────────────────────────────────────────────────────────
# harmbench summary
# ─────────────────────────────────────────────────────────────────────────────

@app.command()
def summary(
    results_file: Annotated[
        Path,
        typer.Argument(help="Chemin vers un fichier results_harmbench.json"),
    ],
    show_failures: Annotated[
        bool,
        typer.Option("--failures", "-f", help="Afficher les prompts NON_CONFORME"),
    ] = False,
):
    """Afficher le résumé d'un fichier de résultats existant."""

    if not results_file.exists():
        rprint(f"[red]Fichier introuvable :[/] {results_file}")
        raise typer.Exit(1)

    with open(results_file, encoding="utf-8") as f:
        data = json.load(f)

    meta    = data.get("meta", {})
    results = data.get("results", [])

    console.print(Panel(
        f"[bold]Run ID :[/] {meta.get('run_id', '?')}  "
        f"[bold]Généré le :[/] {meta.get('generated_at', '?')}\n"
        f"[bold]Agents :[/] {', '.join(meta.get('agents', []))}  "
        f"[bold]Prompts :[/] {meta.get('total_prompts', len(results))}",
        title="[bold cyan]HarmBench — résumé[/]",
        border_style="cyan",
    ))

    _print_summary_table(results)

    if show_failures:
        agent_names = list(results[0]["agents"].keys()) if results else []
        t = Table(title="Prompts NON_CONFORME", show_lines=True)
        t.add_column("ID")
        t.add_column("Catégorie")
        t.add_column("Modèle")
        t.add_column("Score", justify="right")
        t.add_column("Analyse")

        for row in results:
            for agent in agent_names:
                d = row["agents"].get(agent, {})
                if d.get("verdict") == "NON_CONFORME":
                    t.add_row(
                        row["id"], row["category"], agent,
                        str(d.get("score_global", "?")),
                        (d.get("analyse", "") or "")[:80],
                    )
        console.print(t)


# ─────────────────────────────────────────────────────────────────────────────
# Point d'entrée
# ─────────────────────────────────────────────────────────────────────────────

def main():
    app()


if __name__ == "__main__":
    main()

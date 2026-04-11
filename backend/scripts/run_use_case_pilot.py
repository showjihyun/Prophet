"""Run a Prophet use-case pilot end-to-end and record the results.

Usage::

    uv run python backend/scripts/run_use_case_pilot.py --case uc1_baseline
    uv run python backend/scripts/run_use_case_pilot.py --case uc1_reframed --seed 7
    uv run python backend/scripts/run_use_case_pilot.py --list

Each named case is a dict in ``_CASES`` with a Prophet create-simulation
payload plus metadata. The script:

  1. POSTs a fresh simulation against a running backend (``--host``)
  2. Starts it and steps to completion (or ``--steps`` hard cap)
  3. Collects per-community metrics from the final step
  4. Checks for emergent events across all steps
  5. Calls the cross-community ``/__overall__/opinion-summary`` endpoint
     so the LLM narrative lands in the DB for the results doc
  6. Writes ``docs/pilot_results/{case}.json`` — the canonical evidence
     blob for the README claims

The script is deliberately API-based rather than service-layer so it
mirrors what a real user would do (curl + wait). It's slower than a
direct service call but the trade-off is zero special test harness code
— whatever the script measures is what the product ships.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import httpx


# --------------------------------------------------------------------------- #
# Case definitions                                                             #
# --------------------------------------------------------------------------- #
#
# Each case is a named Prophet create-simulation payload. The community
# mix + campaign attributes encode the scenario from README.md. Keep
# them concrete and self-contained so a future reader can see exactly
# what was simulated.

_COMMUNITY_5K_DEFAULT = [
    # README's "5,000 agents" mix: 20% early adopters, 60% mainstream,
    # 15% skeptics, 5% influencers, plus a small fixed expert panel.
    # Round 8-7: scaled up from the initial 1030-agent pilot — small
    # populations were crossing cascade critical mass even with hostile
    # framing, masking the campaign bonus. 5K lets the stall actually
    # emerge.
    {"id": "A", "name": "early_adopters", "size": 1000, "agent_type": "early_adopter"},
    {"id": "B", "name": "mainstream", "size": 3000, "agent_type": "consumer"},
    {"id": "C", "name": "skeptics", "size": 750, "agent_type": "skeptic"},
    {"id": "D", "name": "experts", "size": 50, "agent_type": "expert"},
    {"id": "E", "name": "influencers", "size": 200, "agent_type": "influencer"},
]  # total: 5,000 agents

_COMMUNITY_RTO = [
    # Fortune 500 synthetic employees — skewed toward engineers (the
    # pushback cohort) so the sentiment-collapse signal is readable.
    # Round 8-7: scaled up from 880 to 4,500 agents to match the 5K
    # population target. Keep the engineering-heavy weighting intact.
    {"id": "A", "name": "engineering", "size": 2000, "agent_type": "skeptic"},
    {"id": "B", "name": "product", "size": 1000, "agent_type": "consumer"},
    {"id": "C", "name": "sales", "size": 1000, "agent_type": "early_adopter"},
    {"id": "D", "name": "leadership", "size": 300, "agent_type": "influencer"},
    {"id": "E", "name": "hr", "size": 200, "agent_type": "expert"},
]  # total: 4,500 agents


_CASES: dict[str, dict[str, Any]] = {
    # ===================================================================== #
    # UC1 — Pre-test a product launch (sustainability beverage)              #
    # README claim: baseline polarizes skeptics at step 18, stalls at 12%.   #
    #               Reframed hits 31%.                                       #
    # ===================================================================== #
    "uc1_baseline": {
        "readme_section": "### Pre-test a product launch",
        "claim": "Polarizes skeptics; adoption stalls at 12%",
        "payload": {
            "name": "UC1 Baseline — Sustainability (high controversy)",
            "description": (
                "README use-case 1: beverage brand sustainability launch. "
                "Baseline run with high controversy / low utility framing."
            ),
            "campaign": {
                "name": "GreenBottle Eco-Launch",
                "budget": 1_200_000,
                "channels": ["sns", "news", "influencer"],
                "message": "Switch to sustainable — every plastic bottle harms the planet.",
                "target_communities": ["all"],
                "novelty": 0.5,
                "utility": 0.3,
                "controversy": 0.8,
            },
            "communities": _COMMUNITY_5K_DEFAULT,
            "max_steps": 12,
            "default_llm_provider": "ollama",
            "slm_llm_ratio": 0.98,
            "slm_model": "llama3.1:8b",
            "budget_usd": 1.0,
        },
    },
    "uc1_reframed": {
        "readme_section": "### Pre-test a product launch",
        "claim": "Reframed campaign hits 31%",
        "payload": {
            "name": "UC1 Reframed — Sustainability (utility-forward)",
            "description": (
                "README use-case 1: same population, reframed campaign. "
                "Lower controversy, higher utility + novelty framing."
            ),
            "campaign": {
                "name": "GreenBottle Better-Hydration",
                "budget": 1_200_000,
                "channels": ["sns", "news", "influencer"],
                "message": (
                    "Better taste, longer freshness, and a small eco bonus "
                    "with every bottle you choose."
                ),
                "target_communities": ["all"],
                "novelty": 0.8,
                "utility": 0.75,
                "controversy": 0.2,
            },
            "communities": _COMMUNITY_5K_DEFAULT,
            "max_steps": 12,
            "default_llm_provider": "ollama",
            "slm_llm_ratio": 0.98,
            "slm_model": "llama3.1:8b",
            "budget_usd": 1.0,
        },
    },
    # ===================================================================== #
    # UC2 — Pre-screen public health messages (vaccine)                      #
    # README claim: Strategy B causes echo chambers in skeptic communities;  #
    #               Strategy C triggers viral cascade via influencers.       #
    # ===================================================================== #
    "uc2_strategy_b": {
        "readme_section": "### Pre-screen public health messages",
        "claim": "Strategy B forms echo chambers in skeptic communities",
        "payload": {
            "name": "UC2 Strategy B — Compliance framing",
            "description": (
                "README use-case 2: public health vaccine messaging. "
                "Strategy B = compliance/fear-based framing."
            ),
            "campaign": {
                "name": "Vaccine Strategy B",
                "budget": 500_000,
                "channels": ["sns", "news"],
                "message": "Get vaccinated or face mandatory isolation and workplace restrictions.",
                "target_communities": ["all"],
                "novelty": 0.3,
                "utility": 0.4,
                "controversy": 0.85,
            },
            "communities": _COMMUNITY_5K_DEFAULT,
            "max_steps": 12,
            "default_llm_provider": "ollama",
            "slm_llm_ratio": 0.98,
            "slm_model": "llama3.1:8b",
            "budget_usd": 1.0,
        },
    },
    "uc2_strategy_c": {
        "readme_section": "### Pre-screen public health messages",
        "claim": "Strategy C triggers viral cascade via influencer nodes",
        "payload": {
            "name": "UC2 Strategy C — Empowerment framing",
            "description": (
                "README use-case 2: public health vaccine messaging. "
                "Strategy C = empowerment/influencer-led framing."
            ),
            "campaign": {
                "name": "Vaccine Strategy C",
                "budget": 500_000,
                "channels": ["sns", "influencer"],
                "message": (
                    "Protect the people you love — join millions of neighbours "
                    "taking the shot this month."
                ),
                "target_communities": ["all"],
                "novelty": 0.75,
                "utility": 0.85,
                "controversy": 0.15,
            },
            "communities": _COMMUNITY_5K_DEFAULT,
            "max_steps": 12,
            "default_llm_provider": "ollama",
            "slm_llm_ratio": 0.98,
            "slm_model": "llama3.1:8b",
            "budget_usd": 1.0,
        },
    },
    # ===================================================================== #
    # UC3 — Stress-test internal communications (RTO mandate)                #
    # README claim: 38% sentiment collapse in engineering; carve-outs cut    #
    #               opposition 60%.                                          #
    # ===================================================================== #
    "uc3_rto_raw": {
        "readme_section": "### Stress-test internal communications",
        "claim": "38% sentiment collapse in engineering",
        "payload": {
            "name": "UC3 RTO — Raw mandate",
            "description": (
                "README use-case 3: Fortune 500 RTO mandate. Engineering-heavy "
                "population with raw 5-days-on-site announcement."
            ),
            "campaign": {
                "name": "RTO 5-Day Mandate (raw)",
                "budget": 0,
                "channels": ["email", "all-hands"],
                "message": (
                    "Effective next quarter all employees must be on-site five "
                    "days per week. No exceptions."
                ),
                "target_communities": ["all"],
                "novelty": 0.1,
                "utility": 0.2,
                "controversy": 0.85,
            },
            "communities": _COMMUNITY_RTO,
            "max_steps": 12,
            "default_llm_provider": "ollama",
            "slm_llm_ratio": 0.98,
            "slm_model": "llama3.1:8b",
            "budget_usd": 1.0,
        },
    },
    "uc3_rto_restructured": {
        "readme_section": "### Stress-test internal communications",
        "claim": "Carve-outs cut opposition by 60%",
        "payload": {
            "name": "UC3 RTO — Restructured with carve-outs",
            "description": (
                "README use-case 3: same population, restructured RTO rollout "
                "with engineering carve-outs and phased onboarding."
            ),
            "campaign": {
                "name": "RTO Hybrid (restructured)",
                "budget": 0,
                "channels": ["email", "all-hands", "slack"],
                "message": (
                    "Hybrid 3-days-on-site starting next quarter. Engineering "
                    "teams keep flexible days; phased onboarding through Q2."
                ),
                "target_communities": ["all"],
                "novelty": 0.45,
                "utility": 0.7,
                "controversy": 0.35,
            },
            "communities": _COMMUNITY_RTO,
            "max_steps": 12,
            "default_llm_provider": "ollama",
            "slm_llm_ratio": 0.98,
            "slm_model": "llama3.1:8b",
            "budget_usd": 1.0,
        },
    },
}


# --------------------------------------------------------------------------- #
# Runner                                                                       #
# --------------------------------------------------------------------------- #


def _iso_now() -> str:
    import datetime as _dt
    return _dt.datetime.now(_dt.timezone.utc).isoformat()


def _post(client: httpx.Client, path: str, **kwargs: Any) -> httpx.Response:
    r = client.post(path, **kwargs)
    if r.status_code >= 400:
        print(f"! {path} → {r.status_code}: {r.text[:400]}", file=sys.stderr)
    r.raise_for_status()
    return r


def run_case(
    case_name: str,
    *,
    host: str,
    seed: int | None,
    steps_override: int | None,
) -> dict[str, Any]:
    if case_name not in _CASES:
        raise SystemExit(
            f"unknown case {case_name!r}. Available: {', '.join(_CASES)}"
        )
    case = _CASES[case_name]
    payload = dict(case["payload"])  # shallow copy so --seed override is local
    if seed is not None:
        payload["random_seed"] = seed
    if steps_override is not None:
        payload["max_steps"] = steps_override

    started_at = _iso_now()
    with httpx.Client(base_url=host, timeout=600.0) as client:
        # 1. Create + start
        create_resp = _post(client, "/api/v1/simulations/", json=payload).json()
        sim_id = create_resp["simulation_id"]
        print(f"[{case_name}] created sim_id={sim_id}")

        _post(client, f"/api/v1/simulations/{sim_id}/start")

        # 2. Step the requested number of times
        max_steps = payload.get("max_steps", 20)
        steps: list[dict[str, Any]] = []
        completed = False
        for i in range(max_steps):
            r = client.post(f"/api/v1/simulations/{sim_id}/step")
            if r.status_code == 409:
                # Simulation reached its own terminal state (completed or
                # failed) before we finished the loop. Stop cleanly.
                print(f"[{case_name}] step {i+1}: sim already terminal, stopping")
                completed = True
                break
            r.raise_for_status()
            data = r.json()
            step = data.get("step")
            if step is None:
                print(f"[{case_name}] step {i+1} returned no step field; stopping")
                break
            steps.append(data)
            print(
                f"[{case_name}] step={step} "
                f"adopt={data.get('adoption_rate', 0):.3f} "
                f"sent={data.get('mean_sentiment', 0):+.2f} "
                f"emergent={len(data.get('emergent_events', []))}"
            )

        # 3. Pause so background writers quiesce before opinion call.
        #    If the sim already reached a terminal state above, pause would
        #    409 — just give the background tasks a moment to flush instead.
        if not completed:
            try:
                client.post(f"/api/v1/simulations/{sim_id}/pause").raise_for_status()
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 409:
                    completed = True
                else:
                    raise
        time.sleep(1.5)

        # 4. Collect per-community metrics from the final step
        final_step = steps[-1] if steps else {}
        community_metrics = final_step.get("community_metrics", {})

        # 5. Emergent event aggregation
        emergent_by_type: dict[str, int] = {}
        for s in steps:
            for ev in s.get("emergent_events", []) or []:
                t = ev.get("type", "unknown")
                emergent_by_type[t] = emergent_by_type.get(t, 0) + 1

        # 6. Cross-community opinion synthesis
        print(f"[{case_name}] calling overall opinion synthesis (may take ~60s)")
        overall: dict[str, Any] = {}
        try:
            overall_resp = client.post(
                f"/api/v1/simulations/{sim_id}/communities/__overall__/opinion-summary",
                timeout=600.0,
            )
            if overall_resp.status_code == 200:
                overall = overall_resp.json()
            else:
                overall = {
                    "error": f"status={overall_resp.status_code}",
                    "body": overall_resp.text[:500],
                }
        except Exception as exc:  # pragma: no cover — best-effort capture
            overall = {"error": str(exc)}

    finished_at = _iso_now()

    return {
        "case": case_name,
        "readme_section": case["readme_section"],
        "readme_claim": case["claim"],
        "simulation_id": sim_id,
        "payload": payload,
        "started_at": started_at,
        "finished_at": finished_at,
        "steps_run": len(steps),
        "final_metrics": {
            "adoption_rate": final_step.get("adoption_rate"),
            "mean_sentiment": final_step.get("mean_sentiment"),
            "sentiment_variance": final_step.get("sentiment_variance"),
            "diffusion_rate": final_step.get("diffusion_rate"),
        },
        "per_community_final": community_metrics,
        "emergent_events_total_by_type": emergent_by_type,
        "opinion_overall": overall,
        "step_history_summary": [
            {
                "step": s.get("step"),
                "adoption_rate": s.get("adoption_rate"),
                "mean_sentiment": s.get("mean_sentiment"),
                "n_emergent": len(s.get("emergent_events", []) or []),
            }
            for s in steps
        ],
    }


# --------------------------------------------------------------------------- #
# CLI                                                                          #
# --------------------------------------------------------------------------- #


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--case", help="Case name (see --list)")
    ap.add_argument(
        "--host",
        default="http://localhost:8000",
        help="Backend base URL",
    )
    ap.add_argument("--seed", type=int, help="Override random_seed")
    ap.add_argument(
        "--steps",
        type=int,
        help="Override max_steps (default: case's own value)",
    )
    ap.add_argument("--list", action="store_true", help="List all cases")
    ap.add_argument(
        "--out-dir",
        default="docs/pilot_results",
        help="Output directory for JSON result blobs",
    )
    args = ap.parse_args()

    if args.list:
        print("Available pilot cases:")
        for name, case in _CASES.items():
            print(f"  {name:22s} - {case['claim']}")
        return

    if not args.case:
        ap.error("--case is required (or use --list)")

    result = run_case(
        args.case, host=args.host, seed=args.seed, steps_override=args.steps,
    )

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{args.case}.json"
    out_path.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    print(f"[{args.case}] wrote {out_path}")


if __name__ == "__main__":
    main()

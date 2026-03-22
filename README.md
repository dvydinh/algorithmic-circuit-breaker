# Algorithmic Circuit Breaker v3.0

## System Overview
Algorithmic Circuit Breaker v3.0 is a **Privacy-Preserving Proxy Measurement & Auditing Tool**. It applies Classical Control Theory (PID) to regulate user addiction and opinion manipulation in Recommender Systems. 

Positioned as an Auditing Tool rather than a "silver bullet," the system operates strictly on mathematical proxy variables. It demonstrates that actionable software engineering components can act as automated regulatory mechanisms to enforce **Value Alignment** (Time Well Spent) and protect user **Autonomy** without relying on coercive "Hard Blocks."

## Mathematical Models

### 1. Dopamine Model & Computational Psychiatry
Based on **Dual-Process Theory**, the system models addictive engagement (System-1 impulsivity) using the Rescorla-Wagner Reward Prediction Error (RPE) equation:
```text
V(t+1) = V(t) + alpha * [R(t) - V(t)]
```
Biological continuity is enforced via a **Leaky Integrator** state mechanism. When $RPE \le 0$, the dopamine expectation degrades mathematically via a continuous exponential decay factor ($\gamma = 0.95$).
Scroll velocity is strictly utilized as a **behavioral proxy** for dopamine-seeking action, validated within the framework of computational psychiatry models for behavioral addictions.

### 2. Opinion Manipulation Countermeasure
Content toxicity exposure is calculated without centralized text-scraping. 
- In production, it utilizes Shift-Left Local NLP Heuristics. Toxicity is scored $O(1)$ strictly on the client browser using a Jigsaw-derived dataset. ZERO user text is transmitted to the server.
- In system simulation, toxicity is modeled mathematically as a simple Random Walk (`np.random.normal(0, 0.05)`). 

### 3. PID Control (Mindful Friction Engine)
A Proportional-Integral-Derivative (PID) controller monitors risk and applies interventions. The control signal is computed against a 3-Component Risk Index:

```text
I_risk = w1 * Addiction + w2 * Toxicity + w3 * Session
```

To prevent **Psychological Reactance**, the system avoids traditional "Hard Blocks". Instead, the PID output triggers a **Mindful Friction** strategy (passive deprivation):
1. **Level 1 (Desaturation):** Applies proportional grayscale CSS filters to the DOM, silently choking visual dopamine rewards when Risk > 0.6.
2. **Level 2 (Scroll Throttling):** Injects event-loop delays (100ms-300ms) into `wheel`/`touchmove` handlers when Risk > 0.8. This intentionally degrades the platform's frictionless UI to force a cognitive switch from System-1 back to System-2.

## Simulation Pipeline (`run_simulation.py`)

Simulation data is driven by strict statistical distributions to mirror human interaction patterns autonomously:
- **Interaction Flow**: Modeled via **Temporal Point-Processes** (Bi-exponential Hawkes Process).
- **Dual-Process Distribution**: $\kappa(t) = \beta^1\alpha^1\exp(-\beta^1t) + \beta^2\alpha^2\exp(-\beta^2t)$, where Component 1 represents System-1 impulsivity and Component 2 represents System-2 logic.

### Output CSV Columns (`simulation_log.csv`)

The simulation outputs a deterministic record of system state per step (*Note: legacy columns preserved for visualization continuity*):

| Column | Description |
| :--- | :--- |
| `step` | Incremental simulation step index |
| `simulated_time_sec` | Total elapsed operational time (seconds) |
| `velocity_clicks_per_min` | Proxied proxy velocity |
| `toxicity` | Bounded environmental toxicity score (0-1) |
| `expected_reward` | Rescorla-Wagner $V(t)$ |
| `rpe` | Rescorla-Wagner Reward Prediction Error |
| `dopamine_level` | Normalized addiction scale score |
| `dopamine_baseline` | Static assumption (0.2) |
| `tolerance` | Tracking tolerance matching expected reward |
| `risk_index` | 3-Component scalar risk output |
| `control_signal_u` | PID numerical control command output |
| `intervention_type` | Legacy marker for active friction |
| `interaction_type` | Origin interaction (static: `'click'`) |
| `lambda_intensity` | Current $\kappa(t)$ intensity from Point-Process |
| `alpha1_effective` | System-1 impulsivity weight under decay |
| `alpha2` | System-2 logic weight |
| `decay_factor` | PID-driven suppression scalar [0,1] applied to $\alpha^1$ |

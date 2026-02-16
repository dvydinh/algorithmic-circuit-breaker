# Algorithmic Circuit Breaker v3.0

## System Overview
A Privacy-Preserving Proxy Measurement & Intervention Architecture applying Classical Control Theory (PID) to mitigate user addiction and opinion manipulation in Recommender Systems. 

The system operates strictly on mathematical proxy variables, demonstrating that actionable software engineering components can act as automated regulatory mechanisms without compromising user privacy.

## Mathematical Models

### 1. Dopamine Model (Addictive Design Countermeasure)
Models addictive engagement using the Rescorla-Wagner Reward Prediction Error (RPE) equation:
```text
V(t+1) = V(t) + alpha * [R(t) - V(t)]
```
Reward ($R(t)$) is parameterized by scroll velocity, acting as an absolute behavioral proxy for dopamine-seeking action.

### 2. Opinion Manipulation Countermeasure
Content toxicity exposure is calculated without centralized text-scraping. 
- In production, it utilizes Shift-Left Local NLP Heuristics. Toxicity is scored $O(1)$ strictly on the client browser using a Jigsaw-derived dataset. ZERO user text is transmitted to the server.
- In system simulation, toxicity is modeled mathematically as a simple Random Walk (`np.random.normal(0, 0.05)`). 

### 3. PID Control (Regulatory Responsibility)
A Proportional-Integral-Derivative (PID) controller monitors risk and applies interventions. The control signal is computed against a 3-Component Risk Index:

```text
I_risk = w1 * Addiction + w2 * Toxicity + w3 * Session
```

Based on configurable thresholds, the controller outputs a control signal triggering discrete states:
1. `'FRICTION'`: Applied interface resistance.
2. `'REROUTE'`: Active behavioral warnings.
3. `'BREAK'`: Complete interaction circuit break.

## Simulation Pipeline (`run_simulation.py`)

Simulation data is driven by strict statistical distributions to mirror human interaction patterns autonomously:
- **Interaction (Clicks)**: Governed by a **Poisson distribution**.
- **Dwell Time**: Governed by a **Pareto distribution** to simulate realistic heavy-tailed engagement (doomscrolling).

### Output CSV Columns (`simulation_log.csv`)

The simulation outputs a deterministic record of system state per step containing exactly the following keys:

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
| `intervention_type` | Triggered state: `'break'`, `'reroute'`, `'friction'`, or `'none'` |
| `interaction_type` | Origin interaction (static: `'click'`) |

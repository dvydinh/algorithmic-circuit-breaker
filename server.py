"""
Algorithm Circuit Breaker v3.0 - Flask Backend
===============================================
Pure mathematical proxy measurement and PID control server.
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import sys
import os
import numpy as np
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from circuit_breaker.controllers.pid_controller import CircuitBreaker
from circuit_breaker.core.config import PIDConfig, RLConfig
from circuit_breaker.core.enums import InterventionType
from circuit_breaker.models.user_agent import UserAgent

app = Flask(__name__)
CORS(app)

# ============================================================
# INSTANCES
# ============================================================
circuit_breaker = CircuitBreaker(PIDConfig())
rl_agent = UserAgent(RLConfig(alpha=0.1))

session = {
    "scroll_time": 0.0,
    "toxicity": 0.0,
    "requests": 0,
    "interventions": {"FRICTION": 0, "REROUTE": 0, "BREAK": 0},
    "velocity": 0.0,
    "risk": 0.0,
    "intervention": "NONE",
    "start": time.time()
}

def status_str(risk, intervention):
    if intervention == "BREAK": return "BREAK_ACTIVE"
    if intervention in ["FRICTION", "REROUTE"]: return "WARNING"
    if risk > 0.6: return "HIGH_RISK"
    if risk > 0.3: return "ELEVATED"
    return "SAFE"

# ============================================================
# ENDPOINTS
# ============================================================
@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        data = request.get_json()
        if not data:
            print("[ERROR] No JSON in request")
            return jsonify({"error": "No data"}), 400
        
        velocity = float(data.get('velocity', 0))
        toxicity = float(data.get('toxicity', 0))
        scroll_time = float(data.get('scroll_time', 0))
        
        # Update session
        session["scroll_time"] += scroll_time
        session["toxicity"] += toxicity
        session["requests"] += 1
        session["velocity"] = velocity
        
        # Log every request
        print(f"\n{'='*50}")
        print(f"[ANALYZE] Request #{session['requests']}")
        print(f"  velocity:    {velocity:.1f} px/s")
        print(f"  toxicity:    {toxicity:.2f}")
        print(f"  scroll_time: {scroll_time:.1f}s")
        
        # Process with RL Agent
        # Calculate Reward Prediction Error using proxy velocity and local toxicity
        rpe = rl_agent.calculate_rpe(velocity=velocity, toxicity_score=toxicity)
        addiction_score = rl_agent.get_addiction_score()
        
        # PID calculation
        ctrl, risk = circuit_breaker.compute_control_signal(
            addiction_score=addiction_score,
            toxicity_score=toxicity,
            session_duration=session["scroll_time"],
            dt=0.5
        )
        
        # Update session risk (no dummy jitter allowed)
        session["risk"] = float(risk)
        
        # Intervention
        intervention = circuit_breaker.determine_intervention(ctrl)
        int_str = intervention.name
        session["intervention"] = int_str
        
        if intervention != InterventionType.NONE:
            session["interventions"][int_str] += 1
        
        # Build pure mathematical response
        response = {
            "risk_index": round(float(risk), 4),
            "pid_output": round(float(ctrl), 4),
            "velocity": round(float(velocity), 2),
            "toxicity": round(float(toxicity), 2),
            "status": status_str(float(risk), int_str),
            "intervention": int_str,
            "session_time": round(session["scroll_time"], 1),
            "request_count": session["requests"]
        }
        
        # Log response
        print(f"  → RPE:       {rpe:.4f}")
        print(f"  → Addctn Sc: {addiction_score:.3f}")
        print(f"  → risk:      {response['risk_index']:.3f}")
        print(f"  → status:    {response['status']}")
        print(f"{'='*50}\n")
        
        return jsonify(response)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/realtime', methods=['GET'])
def realtime():
    dur = time.time() - session["start"]
    
    return jsonify({
        "risk_index": round(float(session["risk"]), 4),
        "velocity": round(float(session["velocity"]), 2),
        "toxicity": round(session["toxicity"], 2),
        "status": status_str(session["risk"], session["intervention"]),
        "intervention": session["intervention"],
        "session_duration": round(dur, 1),
        "request_count": session["requests"]
    })


@app.route('/reset', methods=['POST'])
def reset():
    global session, rl_agent
    circuit_breaker.reset()
    rl_agent = UserAgent(RLConfig(alpha=0.1))
    session = {
        "scroll_time": 0.0, "toxicity": 0.0, "requests": 0,
        "interventions": {"FRICTION": 0, "REROUTE": 0, "BREAK": 0},
        "velocity": 0.0, "risk": 0.0, "intervention": "NONE",
        "start": time.time()
    }
    print("\n[RESET] All state cleared\n")
    return jsonify({"message": "Reset complete"})


@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy", "version": "3.0"})


# ============================================================
# MAIN
# ============================================================
if __name__ == '__main__':
    print("\n" + "="*55)
    print("  CIRCUIT BREAKER v3.0 - Proxy Measurement Server")
    print("="*55)
    print("  ✓ Rescorla-Wagner RPE implementation")
    print("="*55)
    print(f"  RL Alpha: {rl_agent.config.alpha}")
    print(f"  Thresholds: {circuit_breaker.friction_threshold} / {circuit_breaker.circuit_break_threshold}")
    print("="*55)
    print("  http://127.0.0.1:5000")
    print("="*55 + "\n")
    
    app.run(host='127.0.0.1', port=5000, debug=True)

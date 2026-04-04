import csv
import json
import time
from pathlib import Path
from typing import List
from synthetic_students import ReactiveStudent, CLUSTERS

# Dummy/mock functions to symbolize API calls or direct instantiated function calls
# In reality, this communicates with the ES-LLMs Orchestrator
def emulate_tutor_step(student_state: dict, step_idx: int) -> dict:
    """Mock standard tutor response to symbolize baseline or orchestrator actions."""
    if not student_state["correct"]:
        return {"actions": ["HINT"], "bkt_after": min(0.99, student_state["mastery"] + 0.1)}
    return {"actions": ["NEXT_PROBLEM"], "bkt_after": min(0.99, student_state["mastery"] + 0.2)}

class SimulationResult:
    def __init__(self, session_id, cluster_name, steps, initial_bkt, final_bkt, true_gain, hints, errors):
        self.session_id = session_id
        self.cluster = cluster_name
        self.steps = steps
        self.initial_bkt = initial_bkt
        self.final_bkt = final_bkt
        self.mastery_gain_bkt = final_bkt - initial_bkt
        self.true_gain = true_gain
        self.hints = hints
        self.errors = errors

def run_simulation(cluster_name: str, n_sessions: int):
    """
    Runs an asynchronous Monte Carlo simulation of synthetic students 
    interacting with the tutor to test "Hint Efficiency" and "Mastery Gain".
    """
    config = CLUSTERS[cluster_name]
    results = []
    
    print(f"--- Simulating {n_sessions} sessions for {config.name} ---")
    
    for run_idx in range(n_sessions):
        student = ReactiveStudent(config)
        session_id = f"sim_{cluster_name}_{run_idx}_{int(time.time())}"
        
        steps = 0
        hints = 0
        errors = 0
        initial_bkt = 0.1
        final_bkt = initial_bkt
        max_steps = 10
        
        for step in range(max_steps):
            steps += 1
            # 1. Student Acts
            act = student.attempt()
            if not act["correct"]:
                errors += 1
            
            # 2. Transmit to Orchestrator (Mocked here for portable execution)
            tutor_resp = emulate_tutor_step({"correct": act["correct"], "mastery": final_bkt}, step)
            tutor_actions = tutor_resp.get("actions", [])
            final_bkt = tutor_resp.get("bkt_after", final_bkt)
            
            if any(k in str(tutor_actions) for k in ["HINT", "SCAFFOLD", "BASELINE_RESPONSE"]):
                hints += 1
            
            # 3. Student Internal State Reacts to Tutor Pedagogical Policy
            student.react(tutor_actions)
            
            # 4. Graduate if BKT threshold is met
            if final_bkt >= 0.95:
                break
                
        results.append(SimulationResult(
            session_id=session_id, cluster_name=config.name, steps=steps,
            initial_bkt=initial_bkt, final_bkt=final_bkt,
            true_gain=student.mastery - config.init_mastery,
            hints=hints, errors=errors
        ))
    return results

if __name__ == "__main__":
    out_file = Path(__file__).parent / "demo_simulation_results.csv"
    all_results = []
    
    for cluster in CLUSTERS.keys():
        all_results.extend(run_simulation(cluster, n_sessions=10))
        
    with out_file.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["SessionID", "Cluster", "Steps", "InitBKT", "FinalBKT", "GainBKT", "TrueGain", "Hints", "Errors"])
        for r in all_results:
            writer.writerow([r.session_id, r.cluster, r.steps, r.initial_bkt, r.final_bkt, r.mastery_gain_bkt, r.true_gain, r.hints, r.errors])
    print(f"Simulation saved to {out_file}.")

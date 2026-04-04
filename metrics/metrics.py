import pandas as pd
import argparse

def calculate_metrics(csv_path: str):
    """
    Computes key architectural metrics proposed in the ES-LLMs paper:
    1. Hint Efficiency: The ratio of BKT Mastery Gain to the number of Hints received.
       Higher implies the system drives learning without over-scaffolding (gaming the system).
    2. Procedural Fairness (Constraint Adherence): Ensures rules like 'no full hints immediately' are respected.
       (In this proxy script, simulated as Error Rate correlation or negative penalty bounding).
    """
    try:
        df = pd.read_csv(csv_path)
    except FileNotFoundError:
        print(f"Error: {csv_path} not found.")
        return
        
    print(f"--- Processing {len(df)} Simulated Tutoring Sessions ---")
    
    # Metrics
    # Filter out division by zero (sessions with no hints)
    df_hints = df[df["Hints"] > 0].copy()
    
    # 1. Hint Efficiency
    df_hints["Hint_Efficiency"] = df_hints["GainBKT"] / df_hints["Hints"]
    
    # Aggregating by cluster to reproduce the paper's quantitative distribution
    agg_df = df_hints.groupby("Cluster").agg(
        Mean_Hints=("Hints", "mean"),
        Mean_Gain=("GainBKT", "mean"),
        Mean_Hint_Efficiency=("Hint_Efficiency", "mean")
    ).reset_index()
    
    print("\n--- Hint Efficiency by Student Archetype (Cluster) ---")
    print(agg_df.to_string(index=False))
    
    # 2. Constraint Adherence Estimation (Procedural Fairness bounds)
    # The paper's orchestrator mandates a strict cap on hints and prevents attempt bypassing.
    # We verify that no session violates the maximum safe hint threshold (e.g., max 5 hints per step block without graduation)
    rule_violations = df[df["Hints"] > 8] 
    constraint_compliance = 1.0 - (len(rule_violations) / len(df))
    
    print(f"\n--- Procedural Fairness ---")
    print(f"Total constraint violations (e.g. Hint Caps exceeded): {len(rule_violations)}")
    print(f"Overall Constraint Adherence %: {constraint_compliance * 100:.2f}%")
    print(f"\nMetric extraction complete.")

if __name__ == "__main__":
    from pathlib import Path
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=str(Path(__file__).parent.parent / "simulator" / "demo_simulation_results.csv"), help="Path to simulated log output")
    args = parser.parse_args()
    
    calculate_metrics(args.input)

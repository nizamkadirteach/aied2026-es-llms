import argparse
import csv
import json
import time
from pathlib import Path
import requests

def load_prompts(prompt_file: str) -> dict:
    with open(prompt_file, 'r') as f:
        return json.load(f)

def build_prompt(row: dict, rubric_data: dict) -> str:
    dims = "\n".join(f"- {d}" for d in rubric_data["dimensions"])
    schema = json.dumps(rubric_data["expected_json_schema"], indent=2)
    return (
        f"{rubric_data['system_instruction']}\n\n"
        f"Problem:\n{row.get('problem', '')}\n\n"
        f"Condition A – Tutoring Session:\n{row.get('condition_A_session', '')}\n\n"
        f"Condition B – Tutoring Session:\n{row.get('condition_B_session', '')}\n\n"
        f"Rubric Dimensions:\n{dims}\n\n"
        "You MUST reply in valid JSON with this exact structure:\n"
        f"{schema}\n"
        "Reply with JSON only."
    )

def evaluate_sessions(input_csv: str, output_csv: str, prompt_json: str, endpoint: str, model_name: str):
    """
    Reads a CSV dataset of A/B tutoring interactions, packages them using the eval rubric,
    and queries an OpenAI-compatible REST API (or Ollama) for 1-5 Likert pedagogy scores.
    """
    rubric_data = load_prompts(prompt_json)
    
    with open(input_csv, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
        
    print(f"Loaded {len(rows)} scenarios to evaluate.")
    
    with open(output_csv, 'w', newline="", encoding="utf-8") as f_out:
        fieldnames = [
            "item_id", "preference",
            "A_adaptivity", "A_scaffolding", "A_ethical", "A_engagement", "A_feedback", "A_tone", "A_trust",
            "B_adaptivity", "B_scaffolding", "B_ethical", "B_engagement", "B_feedback", "B_tone", "B_trust"
        ]
        writer = csv.DictWriter(f_out, fieldnames=fieldnames)
        writer.writeheader()
        
        for row in rows:
            print(f"Evaluating item {row.get('item_id', 'unknown')}...")
            prompt = build_prompt(row, rubric_data)
            
            payload = {
                "model": model_name,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
            }
            try:
                 resp = requests.post(endpoint, json=payload, timeout=90)
                 content = resp.json().get("message", {}).get("content", "{}")
                 parsed = json.loads(content)
                 
                 cond_a = parsed.get("condition_A", {})
                 cond_b = parsed.get("condition_B", {})
                 
                 writer.writerow({
                     "item_id": row.get("item_id", ""),
                     "preference": parsed.get("preference", "tie"),
                     "A_adaptivity": cond_a.get("adaptivity", 3),
                     "A_scaffolding": cond_a.get("scaffolding", 3),
                     "A_ethical": cond_a.get("ethical_reasoning", 3),
                     "A_engagement": cond_a.get("engagement", 3),
                     "A_feedback": cond_a.get("feedback_quality", 3),
                     "A_tone": cond_a.get("tone", 3),
                     "A_trust": cond_a.get("trust", 3),
                     "B_adaptivity": cond_b.get("adaptivity", 3),
                     "B_scaffolding": cond_b.get("scaffolding", 3),
                     "B_ethical": cond_b.get("ethical_reasoning", 3),
                     "B_engagement": cond_b.get("engagement", 3),
                     "B_feedback": cond_b.get("feedback_quality", 3),
                     "B_tone": cond_b.get("tone", 3),
                     "B_trust": cond_b.get("trust", 3)
                 })
                 f_out.flush()
                 time.sleep(1) # Rate limit protection
            except Exception as e:
                 print(f"Failed item {row.get('item_id')}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Multi-LLM-as-a-Judge API Wrapper")
    parser.add_argument("--input", required=True, help="Input CSV scenarios")
    parser.add_argument("--output", required=True, help="Output scores CSV")
    parser.add_argument("--prompts", default="eval_rubric_prompts.json")
    parser.add_argument("--endpoint", default="http://localhost:11434/api/chat", help="OpenAI-compatible / Ollama endpoint")
    parser.add_argument("--model", default="llama3.2:3b", help="Model name deployed at endpoint")
    args = parser.parse_args()
    
    evaluate_sessions(args.input, args.output, args.prompts, args.endpoint, args.model)

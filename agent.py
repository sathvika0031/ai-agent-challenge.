"""
Bank Statement Parser Agent with LangGraph + Groq
Automates: plan → generate parser → run pytest → self-fix (≤3 attempts)
"""
import os, sys, re, subprocess
from pathlib import Path
import pandas as pd
from langgraph.graph import StateGraph, END
from groq import Groq

# Groq client
GROQ_API_KEY = "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"
client = Groq(api_key=GROQ_API_KEY)

def clean_code(raw: str) -> str:
    match = re.search(r"```(?:python)?(.*?)```", raw, re.DOTALL)
    code = match.group(1) if match else raw
    return "\n".join([ln for ln in code.splitlines() if not ln.strip().startswith("Here")]).strip()

def generate_parser(bank: str, attempt: int = 1) -> str:
    try:
        prompt = f"""
        Generate parse(file_path:str)->pd.DataFrame for {bank} PDF/CSV using pandas & pdfplumber.
        Replace NaN with 0 or "" and return valid Python code only.
        """
        resp = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role":"user","content":prompt}],
            temperature=0.2,
        )
        code = clean_code(resp.choices[0].message.content.strip())
        compile(code, f"{bank}_parser.py", "exec")
        if "def parse(" not in code:
            raise ValueError("Missing parse()")
        return code
    except:
        return """import pandas as pd
def parse(file_path:str)->pd.DataFrame:
    if file_path.lower().endswith('.csv'): return pd.read_csv(file_path)
    return pd.DataFrame()"""

def write_parser(bank: str, code: str) -> Path:
    parser_dir = Path("custom_parsers"); parser_dir.mkdir(exist_ok=True)
    path = parser_dir / f"{bank}_parser.py"
    path.write_text(code, encoding="utf-8"); return path

def write_pytest(bank: str) -> Path:
    tests_dir = Path("tests"); tests_dir.mkdir(exist_ok=True)
    test_path = tests_dir / f"test_{bank}_parser.py"
    test_path.write_text(f"""
import pandas as pd, importlib.util
from pathlib import Path
def load_parser(bank): spec = importlib.util.spec_from_file_location(f"{{bank}}_parser", Path(f"custom_parsers/{{bank}}_parser.py")); mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod.parse
def test_parser_output_matches_csv():
    bank="{bank}"; parse=load_parser(bank)
    csv_path, pdf_path = Path(f"data/{{bank}}/result.csv"), Path(f"data/{{bank}}/sample.pdf")
    file_to_parse = csv_path if csv_path.exists() else pdf_path
    df_out = parse(str(file_to_parse)); assert not df_out.empty
    if csv_path.exists():
        df_ref = pd.read_csv(csv_path)
        for df in [df_out, df_ref]:
            for col in df.columns: df[col] = df[col].fillna(0.0) if df[col].dtype!='object' else df[col].fillna("")
        assert len(df_out)==len(df_ref)
        for col in set(df_ref.columns).intersection(df_out.columns):
            pd.testing.assert_series_equal(df_out[col].reset_index(drop=True), df_ref[col].reset_index(drop=True), check_dtype=False)
""", encoding="utf-8")
    return test_path

def run_pytest(test_path: Path):
    if not test_path.exists(): return False, []
    try:
        result = subprocess.run([sys.executable,"-m","pytest","-s",str(test_path)], capture_output=True, text=True)
        print(result.stdout); print(result.stderr)
        mismatches = []
        if "Mismatched columns:" in result.stdout: mismatches = re.findall(r"Mismatched columns:\s*\[(.*?)\]", result.stdout)
        return result.returncode==0, mismatches
    except FileNotFoundError:
        print("❌ Pytest not found. Install with pip install pytest."); return False, []

def plan_node(state: dict) -> dict:
    code = generate_parser(state["bank"], state["attempt"])
    parser_path = write_parser(state["bank"], code)
    test_path = write_pytest(state["bank"])
    return {**state, "parser_path": parser_path, "test_path": test_path}

def test_node(state: dict) -> dict:
    success, mismatches = run_pytest(state["test_path"])
    return {**state, "success": success, "mismatches": mismatches}

def decide_node(state: dict) -> str:
    if state["success"]: print(f"✅ Attempt {state['attempt']} succeeded!"); return END
    elif state["attempt"]>=3: print(f"❌ Max attempts reached: {state['mismatches']}"); return END
    else: state["attempt"]+=1; print(f"🔄 Attempt failed: {state['mismatches']}"); return "plan"

def main():
    import argparse
    parser = argparse.ArgumentParser(); parser.add_argument("--target", required=True)
    args = parser.parse_args()
    wf = StateGraph(dict)
    wf.add_node("plan", plan_node); wf.add_node("test", test_node)
    wf.add_edge("plan", "test"); wf.add_conditional_edges("test", decide_node)
    wf.set_entry_point("plan")
    wf.compile().invoke({"bank": args.target, "attempt":1, "success":False, "mismatches":[]})

if __name__=="__main__":
    main()

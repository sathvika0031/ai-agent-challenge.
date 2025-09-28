import pandas as pd
def parse(file_path:str)->pd.DataFrame:
    if file_path.lower().endswith('.csv'): return pd.read_csv(file_path)
    return pd.DataFrame()
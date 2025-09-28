
import pandas as pd
from pypdf import PdfReader

def parse(pdf_path: str) -> pd.DataFrame:
    reader = PdfReader(pdf_path)
    text = "".join([page.extract_text() for page in reader.pages])
    # TODO: real parsing logic for icici
    # For demo: return CSV schema as DataFrame
    return pd.read_csv("data/icici.csv")

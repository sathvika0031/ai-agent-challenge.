
# custom_parser/icici_parser.py
import pandas as pd
from pypdf import PdfReader

def parse(pdf_path: str) -> pd.DataFrame:
    reader = PdfReader(pdf_path)
    text = "".join([page.extract_text() for page in reader.pages])
    # Extract rows from text → build DataFrame
    df = pd.read_csv("data/icici.csv")  # mocked for demo
    return df


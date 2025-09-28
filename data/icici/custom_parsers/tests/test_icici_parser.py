
# tests/test_icici_parser.py
import pandas as pd
from custom_parser.icici_parser import parse

def test_icici_parser():
    pdf_path = "data/icici_sample.pdf"
    expected = pd.read_csv("data/icici.csv")
    result = parse(pdf_path)
    assert result.equals(expected)



from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_extracted_data_cleaner.cleaner import clean_table

if __name__ == "__main__":
    result = clean_table(ROOT / "examples/input/raw_ai_extracted_samples.csv", ROOT / "outputs/demo")
    print("清洗完成：")
    print(result)

import json
from bs4 import BeautifulSoup
import pandas as pd
import re
from pathlib import Path

def get_page_list(path):
    with open(path) as f:
        page_list = json.load(f)

    return page_list

def create_records(page_list):
    records = list()
    for page_num in page_list:
        soup = BeautifulSoup(page_list[page_num], features="html.parser")
        body = soup.find_all("tbody")[-1]

        for _row in body.find_all("tr"):
            row = _row.find_all("td")
            records.append(row)

    if len(records) == 0:
        raise ValueError("No records found")

    return records 

def create_df(records, cnames):
    df = pd.DataFrame(records, columns=cnames)
    return df

def strip_td(df):
    for col in df.columns:
        df[col] = df[col].astype(str).str.replace(r"<td.*?>|</td>", "", regex=True)
    return df

def split_amount(df):
    df[["Amount", "Currency"]] = df["Amount"].str.split(" ", expand=True)
    return df

def sign_amount(df):
    """
    Replace (<float>) with -<float> to prepare for float conversion
    """
    df["Amount"] = df["Amount"].str.replace(",", "")
    df["Amount"] = df["Amount"].apply(lambda x: re.sub(r"\((\d*\.\d{2})\)", r"-\g<1>", x))
    return df

def update_dtypes(df):
    df["Date/Time"] = pd.to_datetime(df["Date/Time"], format=r"%m/%d/%Y %I:%M %p")
    df["Amount"] = df["Amount"].astype(float)
    return df

def main():
    """
    Expects arguments data load path (1) and data save path (2)
    (1) - .json
    (2) - saves as a .csv regardless of name
    """
    import sys
    try:
        path = Path(sys.argv[1])
    except Exception as e:
        print(f"No data path provided")
        sys.exit(0)

    try:
        save_path = Path(sys.argv[2])
    except Exception as e:
        print(f"No save path provided")
        sys.exit(0)

    page_list = get_page_list(path)

    cnames = ["Date/Time", "Account Name", "Card Number", "Location", "Transaction Type", "Amount"]
    records = create_records(page_list)

    df = (
        create_df(records, cnames)
            .pipe(strip_td)
            .pipe(split_amount)
            .pipe(sign_amount)
            .pipe(update_dtypes)
    )

    df.to_csv(save_path, index=False)

if __name__ == "__main__":
    main()
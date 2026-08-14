To process your data:
1. Pull receipts into .json
    1. `cd scraping`
    2. `python ucsd_authenticate.py`
    3. Manually validate Duo Mobile request and immediately select either of the options for the "Is this your device?" prompt in the browser
2. Convert .json into a .csv
    1. `cd ..`
    2. `python processing/process.py scraping/data/raw.json processing/data/a1_raw.csv`
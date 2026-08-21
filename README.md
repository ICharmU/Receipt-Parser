[Dashboard](https://app.powerbi.com/view?r=eyJrIjoiMzNlZTVmNmUtNDY1Ni00YWI3LWJkNDUtZjdhZmFmNGQ3N2I3IiwidCI6IjhhMTk4ODczLTRmZWMtNGU3Ni04MTgyLWNhNDc5ZWRiYmQ2MCIsImMiOjZ9)

[Scripting Process](https://lucid.app/lucidchart/f8068ff0-6525-4663-be53-91e5aa4a8b2f/edit?viewport_loc=-2923%2C28%2C6217%2C3145%2C0_0&invitationId=inv_2eabfeb7-5b4e-44ef-a308-914de241b8a6)

Assumes [Pixi](https://pixi.prefix.dev/latest/installation/) has been installed.

To process your data:
1. Pull receipts into .json
    1. `cd scraping`
    2. `pixi run -m ../pixi.lock python ucsd_authenticate.py`
    3. Manually validate Duo Mobile request on your phone
2. Convert .json into a .csv
    1. `cd ..`
    2. `python processing/process.py scraping/data/raw.json processing/data/a1_raw.csv`

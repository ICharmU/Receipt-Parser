import json
from bs4 import BeautifulSoup

def main():
    with open("auth_url.json") as f:
        auth_url = json.load(f)

    url = auth_url["url"]
    print(url)

if __name__ == "__main__":
    main()
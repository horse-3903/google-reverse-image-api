from datetime import datetime
import parsedatetime

import json

from pathlib import Path

from bs4 import BeautifulSoup, Tag

cal = parsedatetime.Calendar()

def parse_lens(file: Path, save: bool = False):
    content = ""
    res = []

    with open(file, "r", encoding="utf-8") as f:
        content = f.read()

    soup = BeautifulSoup(content, "html.parser")
    elements = soup.find_all("li")

    for element in elements:
        data = {}
        source_element: Tag = element.find("a")
        image: Tag = source_element.find_all("img")[-1]
        misc: Tag = source_element.find_all(class_="QJLLAc")[-1]

        misc_val = [None, misc.string] if "·" not in misc.string else misc.string.split(" · ")
        
        data["source-link"] = source_element["href"] # link of original
        data["source-title"] = source_element["aria-label"] # title of original
        data["image-link"] = image["src"] # link of image
        data["date"] = cal.parseDT(misc_val[0])[0].strftime("%d/%m/%Y") if misc_val[0] else None # date of website
        data["size"] = list(map(int, misc_val[1].split("x"))) # size of image

        res.append(data)
    
    if save:
        path = Path(f"./data/data-{datetime.now().strftime('%d%m%Y-%H%M%S')}.json")

        with open(path, "w+") as f:
            f.write(json.dumps(res, indent=4))

        return res, path

    return res, None

print(parse_lens(file=Path("./content/content-23012024-215505.html"), save=True))
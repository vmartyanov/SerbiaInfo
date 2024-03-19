import csv
import os
import json

from dataclasses import dataclass, asdict

from typing import Any

import requests

CFG_NAME = "cfg.json"

MD_POI_FMT = \
"""\
## {name}

| :notebook: | |
|--|--|
| **Адрес** | {street} {house}, {city} |
| **Координаты** | [{lat},{lon}](geo:{lat},{lon}) |
| **Описание** | {description} |
| **Google Maps** | [LINK](https://www.google.com/maps/place/{lat},{lon}) |
"""

@dataclass
class POI:
    name: str
    description: str
    lat: float
    lon: float
    street: str
    house: str
    city: str
    url: str

def get_osm_data(osm_id: str) -> bytes:
    """Get OSM data"""
    id_type = osm_id[0]
    osm_id = osm_id[1:]
    obj_type = {"N" : "node", "W" : "way"}[id_type]
    url = f"https://overpass-api.de/api/interpreter?data=[out:json][timeout:25];{obj_type}(id:{osm_id});out geom;"

    r = requests.get(url)
    if r.status_code != 200:
        return b""
    return r.content

def get_coords(elements: dict[str, Any]) -> tuple[float, float]:
    """Get coords depending on object type."""
    if elements["type"] == "node":
        lat, lon = elements["lat"], elements["lon"]
    elif elements["type"] == "way":
        bounds = elements["bounds"]
        lat = (bounds["minlat"] + bounds["maxlat"]) / 2
        lon = (bounds["minlon"] + bounds["maxlon"]) / 2
    return (lat, lon)

def save_md(base_name: str, header: str, description: str, pois: list[POI]) -> None:
    """Save .md file."""
    with open(os.path.join("..", f"{base_name}.md"), "w", encoding="utf-8") as file:
        #write header first
        file.write(f"# {header}\n\n{description}\n\n")
        for poi in pois:
            entry = MD_POI_FMT.format(**asdict(poi))
            if poi.url:
                entry += f"| **URL** | <{poi.url}> |\n"
            file.write(entry + "\n")    #we need this last \n!!!

def save_csv(base_name: str, pois: list[POI]) -> None:
    """Save .csv file."""
    with open(os.path.join("..", "csv", f"{base_name}.csv"), "w", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["name", "description", "lat", "lon"])
        for poi in pois:
            writer.writerow([poi.name, poi.description, str(poi.lat), str(poi.lon)])

def main() -> None:
    """Main function."""
    with open(CFG_NAME, "r", encoding="utf-8") as file:
        transforms = json.load(file)

    for transform in transforms:
        pois = []
        in_name = os.path.join("..", "src", transform["in"] + ".json")
        out_base = transform["out"]

        with open (in_name, "r", encoding="utf-8") as file:
            places = json.load(file)

        for place in places:
            print (place["name"])
            json_osm = json.loads(get_osm_data(place["id"]))
            tags = json_osm["elements"][0]["tags"]
            lat, lon = get_coords(json_osm["elements"][0])

            pois.append(POI(tags['name'], place['description'], lat, lon,
                tags['addr:street'], tags['addr:housenumber'], tags['addr:city'], tags.get("website")
            ))

        save_md(out_base, transform['hdr'], transform['descr'], pois)
        save_csv(out_base, pois)

if __name__ == "__main__":
    main()

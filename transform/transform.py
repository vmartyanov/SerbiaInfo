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

#cahing net responses
NET_CACHE = {}

#caching descriptions
DESCR_CACHE = {}

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

    if osm_id in NET_CACHE:
        return NET_CACHE[osm_id]

    id_type = osm_id[0]
    osm_id = osm_id[1:]
    obj_type = {"N" : "node", "W" : "way"}[id_type]
    url = f"https://overpass-api.de/api/interpreter?data=[out:json][timeout:25];{obj_type}(id:{osm_id});out geom;"

    r = requests.get(url)
    if r.status_code != 200:
        return b""

    NET_CACHE[osm_id] = r.content
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

def do_transforms(transforms: list[dict[str, Any]]) -> None:
    """Do transforms."""
    #list of transforms which has references, they will be produced in a 2nd pass
    if not transforms:
        return

    ref_transforms = []

    for transform in transforms:
        pois = []
        base_name = transform["file"]
        in_name = os.path.join("..", "src", base_name + ".json")

        with open (in_name, "r", encoding="utf-8") as file:
            places = json.load(file)

        for place in places:
            name = place["name"]

            description = place.get('description')  #get from json
            if not description:
                description = DESCR_CACHE.get(place["id"])     #get from cache
                if not description:
                    if not transform in ref_transforms:
                        ref_transforms.append(transform)
                        print (base_name + " -> 2nd pass")
                    continue
                else:
                    print (f"\t{name} from cache")
            else:
                print (name)
                DESCR_CACHE[place["id"]] = description

            json_osm = json.loads(get_osm_data(place["id"]))
            tags = json_osm["elements"][0]["tags"]
            lat, lon = get_coords(json_osm["elements"][0])

            pois.append(POI(tags['name'], description, lat, lon,
                tags['addr:street'], tags['addr:housenumber'], tags['addr:city'], tags.get("website")
            ))

        save_md(base_name, transform['hdr'], transform['descr'], pois)
        save_csv(base_name, pois)

    #2nd pass
    do_transforms(ref_transforms)

def main() -> None:
    """Main function."""
    with open(CFG_NAME, "r", encoding="utf-8") as file:
        do_transforms(json.load(file))

if __name__ == "__main__":
    main()

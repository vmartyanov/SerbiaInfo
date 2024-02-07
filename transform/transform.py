import os
import json

import requests

CFG_NAME = "cfg.json"

def get_osm_data(osm_id: str) -> bytes:
    """Get OSM data"""
    id_type = osm_id[0]
    osm_id = osm_id[1:]
    if id_type == "N":
        url = f"https://overpass-api.de/api/interpreter?data=[out:json][timeout:25];node(id:{osm_id});out geom;"
    elif id_type == "W":
        url = f"https://overpass-api.de/api/interpreter?data=[out:json][timeout:25];way(id:{osm_id});out geom;"
    
    r = requests.get(url)
    if r.status_code != 200:
        return b""
    else:
        return r.content

def get_coords(elements) -> (float, float):
    """Get coords depending on object type."""
    if elements["type"] == "node":
        return (elements["lat"], elements["lon"])
    elif elements["type"] == "way":
        bounds = elements["bounds"]
        lat = (bounds["minlat"] + bounds["maxlat"]) / 2
        lon = (bounds["minlon"] + bounds["maxlon"]) / 2
        return (lat, lon)
    

def main() -> None:
    """Main function."""
    with open(CFG_NAME, "r", encoding="utf-8") as file:
        json_obj = json.load(file)


    for transformation in json_obj:
        out_buffer = ""
        
        in_name = os.path.join("..", "src", transformation["in"] + ".json")
        
        #Adding header
        out_buffer = f"# {transformation['hdr']}\n\n"
        out_buffer += transformation["descr"] + "\n\n"
        
        with open (in_name, "r", encoding="utf-8") as file:
            json_src = json.load(file)

        for place in json_src:
            osm_id = place["id"]
            osm_data = get_osm_data(osm_id)
            json_osm = json.loads(osm_data)
            
            #preapring data
            tags = json_osm["elements"][0]["tags"]
            lat, lon = get_coords(json_osm["elements"][0])
            #lat = json_osm["elements"][0]["lat"]
            #lon = json_osm["elements"][0]["lon"]
            #Making markup entry

            out_buffer += f"## {tags['name']}\n\n"
            out_buffer += "| :notebook: | |\n"
            out_buffer += "|--|--|\n"
            out_buffer += f"| **Адрес** | {tags['addr:street']} {tags['addr:housenumber']}, {tags['addr:city']} |\n"
            out_buffer += f"| **Координаты** | [{lat},{lon}](geo:{lat},{lon}) |\n"
            out_buffer += f"| **Описание** | {place['description']} |\n\n"

        with open(os.path.join("..", transformation["out"] + ".md"), "w", encoding="utf-8") as file:
            file.write(out_buffer)

if __name__ == "__main__":
    main()
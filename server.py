from flask import Flask, jsonify, request, g, send_file
import os
from gdal_interfaces import GDALTileInterface
import json
from shapely.ops import unary_union
from shapely.geometry import Polygon, Point
import geopandas as gpd
import pandas as pd

app = Flask(__name__)

class InternalException(ValueError):
    """
    Utility exception class to handle errors internally and return error codes to the client
    """
    pass

DATA_CONFIG = os.environ.get("DATA_CONFIG", "./data-config.json")
OPEN_INTERFACES_SIZE = os.environ.get('OPEN_INTERFACES', 8)
URL_ENDPOINT = os.environ.get('URL_ENDPOINT', '/api/v1/lookup')
ALWAYS_REBUILD_SUMMARY = os.environ.get('ALWAYS_REBUILD_SUMMARY', False)

config_store = {}


def read_data_config():
    config_json = json.load(open(DATA_CONFIG, "r"))
    for key in config_json.keys():
        data = config_json[key]
        data_list = []
        for entry in data:
            interface =  GDALTileInterface(entry["path"], '%s/summary.json' % entry["path"], OPEN_INTERFACES_SIZE, projection=entry["projection"])
            if interface.has_summary_json() and not ALWAYS_REBUILD_SUMMARY:
                print('Re-using existing summary JSON')
                interface.read_summary_json()
            else:
                print('Creating summary JSON ...')
                interface.create_summary_json()
            summary_json = json.load(open(f"{entry['path']}/summary.json", "r"))
            boundaryPoly = gpd.GeoSeries(unary_union([Polygon(((x["coords"][0], x["coords"][2]), (x["coords"][1], x["coords"][2]),
                                                 (x["coords"][1], x["coords"][3]), (x["coords"][0], x["coords"][3]))) for
                                        x in summary_json]))

            data_list.append({"boundary": boundaryPoly, "interface": interface})
        outer_boundary = gpd.GeoSeries(unary_union(gpd.GeoSeries(pd.concat([x["boundary"] for x in data_list], ignore_index=True))))
        config_store[key] = {"boundary": outer_boundary, "data": data_list}


"""
Initialize a global interface. This can grow quite large, because it has a cache.
"""
read_data_config()


def get_elevation(lat, lng):
    """
    Get the elevation at point (lat,lng) using the currently opened interface
    :param lat:
    :param lng:
    :return:
    """
    try:
        # Get best interface
        found_key = None
        for key in sorted(list(config_store.keys())):
            if config_store[key]["boundary"].contains(Point(lat, lng)).any():
                found_key = key
                break
        if found_key is None:
            return {
                'latitude': lat,
                'longitude': lng,
                'error': 'No matching elevation dataset'
            }
        found_interface = None
        for i in range(len(config_store[found_key]["data"])):
            if config_store[found_key]["data"][i]["boundary"].contains(Point(lat, lng)).any():
                found_interface = config_store[found_key]["data"][i]["interface"]
                break
        if found_interface is None:
            # Shouldnt happen
            return {
                'latitude': lat,
                'longitude': lng,
                'error': 'No matching interface'
            }
        elevation = found_interface.lookup(lat, lng)
    except:
        return {
            'latitude': lat,
            'longitude': lng,
            'error': 'No such coordinate (%s, %s)' % (lat, lng)
        }

    return {
        'latitude': lat,
        'longitude': lng,
        'elevation': elevation
    }


def lat_lng_from_location(location_with_comma):
    """
    Parse the latitude and longitude of a location in the format "xx.xxx,yy.yyy" (which we accept as a query string)
    :param location_with_comma:
    :return:
    """
    try:
        lat, lng = [float(i) for i in location_with_comma.split(',')]
        return lat, lng
    except:
        raise InternalException(json.dumps({'error': 'Bad parameter format "%s".' % location_with_comma}))


def query_to_locations(location_string):
    """
    Grab a list of locations from the query and turn them into [(lat,lng),(lat,lng),...]
    :return:
    """
    return [lat_lng_from_location(l) for l in location_string.split('|')]


def body_to_locations(locations):
    """
    Grab a list of locations from the body and turn them into [(lat,lng),(lat,lng),...]
    :return:
    """

    latlng = []
    for l in locations:
        try:
            latlng += [ (l['latitude'],l['longitude']) ]
        except KeyError:
            raise InternalException(json.dumps({'error': '"%s" is not in a valid format.' % l}))
    return latlng


def do_lookup(get_locations_func):
    """
    Generic method which gets the locations in [(lat,lng),(lat,lng),...] format by calling get_locations_func
    and returns an answer ready to go to the client.
    :return:
    """
    locations = get_locations_func()
    return {'results': [get_elevation(lat, lng) for (lat, lng) in locations]}


@app.get(URL_ENDPOINT)
def get_lookup():
    """
    GET method. Uses query_to_locations.
    :return:
    """
    location_string = request.args.get('locations', default=None)
    if not location_string:
        return jsonify({'error': '"Locations" is required.'}), 400
    try:
        evel = do_lookup(query_to_locations())
    except InternalException as e:
        return jsonify(e.args[0]), 400
    return jsonify(evel), 200


@app.post(URL_ENDPOINT)
def post_lookup():
    """
    GET method. Uses body_to_locations.
    :return:
    """
    try:
        locations = request.json["locations"]
    except Exception:
        return jsonify({'error': 'Invalid JSON.'}), 400
    if not locations:
        raise InternalException(json.dumps({'error': '"Locations" is required in the body.'}))
    try:
        evel = do_lookup(body_to_locations(locations))
    except InternalException as e:
        return jsonify(e.args[0]), 400
    return jsonify(evel), 200
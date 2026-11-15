import os
from datetime import datetime

from flask import Flask, jsonify, request, render_template
from pymongo import MongoClient
from pymongo.errors import PyMongoError

import acp_times

app = Flask(__name__)

client = MongoClient(os.environ['MONGO_HOST'], 27017)
db = client.tododb


@app.route('/')
@app.route('/index')
def index():
    return render_template('calc.html')


@app.route('/_calc_times')
def calc_times():
    km = request.args.get('km')
    brevet_distance = request.args.get('brevet_dist_km')
    start_time = request.args.get('start_time')
    if not km or not brevet_distance or not start_time:
        return jsonify(error='km, brevet_dist_km, and start_time are required'), 400

    try:
        result = {
            'open': acp_times.open_time(km, brevet_distance, start_time),
            'close': acp_times.close_time(km, brevet_distance, start_time),
        }
    except ValueError as error:
        return jsonify(error=str(error)), 400
    return jsonify(result=result)


@app.route('/submit', methods=['POST'])
def submit():
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not isinstance(data.get('controls'), list):
        return jsonify(error='A submission with a list of controls is required.'), 400

    brevet_distance = data.get('brevet_distance_km')
    start_time = data.get('start_time')
    if (isinstance(brevet_distance, bool)
            or not isinstance(brevet_distance, (str, int, float))):
        return jsonify(error='Brevet distance must be one of 200, 300, 400, 600, or 1000'), 400
    if not isinstance(start_time, str):
        return jsonify(error='Start time must be a valid ISO 8601 date-time'), 400

    controls = []
    for row_number, row in enumerate(data['controls'], start=1):
        if not isinstance(row, dict):
            return jsonify(error=f'Control {row_number}: invalid row.'), 400
        distance = row.get('distance_km', '')
        miles = row.get('miles', '')
        location = row.get('location', '')
        if not isinstance(miles, str) or not isinstance(location, str):
            return jsonify(error=f'Control {row_number}: invalid row.'), 400
        if isinstance(distance, str) and not distance.strip():
            if miles.strip() or location.strip():
                return jsonify(error=f'Control {row_number}: distance is required.'), 400
            continue
        if isinstance(distance, bool) or not isinstance(distance, (str, int, float)):
            return jsonify(error=f'Control {row_number}: invalid distance.'), 400

        try:
            open_time = acp_times.open_time(distance, brevet_distance, start_time)
            close_time = acp_times.close_time(distance, brevet_distance, start_time)
            distance_km = float(distance)
        except ValueError as error:
            return jsonify(error=f'Control {row_number}: {error}'), 400
        except OverflowError:
            return jsonify(error=f'Control {row_number}: value is out of range.'), 400

        controls.append({
            'distance_km': distance_km,
            'location': location.strip(),
            'open_time': open_time,
            'close_time': close_time,
        })

    if not controls:
        return jsonify(error='Enter at least one control distance before submitting.'), 400

    submission = {
        'brevet_distance_km': int(float(brevet_distance)),
        'start_time': datetime.fromisoformat(start_time).isoformat(),
        'controls': controls,
    }
    try:
        db.brevet_submissions.insert_one(submission)
    except PyMongoError:
        app.logger.exception('Failed to save brevet submission')
        return jsonify(error='Unable to save the submission. Please try again.'), 503

    return jsonify(message='Submission saved successfully.'), 201


@app.route('/display')
def display():
    try:
        submissions = list(db.brevet_submissions.find())
    except PyMongoError:
        app.logger.exception('Failed to read brevet submissions')
        return render_template(
            'display.html', error='Unable to retrieve brevet submissions. Please try again.'
        ), 503
    return render_template('display.html', submissions=submissions)


if __name__ == "__main__":
    app.run(host='0.0.0.0')

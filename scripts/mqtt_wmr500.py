import json
import logging
import time
from datetime import datetime

import paho.mqtt.publish as publish
from flask import Flask, request

MQTT_HOSTNAME = '192.168.0.2'
MQTT_USERNAME = '_USERNAME_'
MQTT_PASSWORD = '_PASSWORD_'
MQTT_CLIENT_ID = 'wmr500'
MQTT_WMR500_GUUID = '_GUUID'
SAMPLE_INTERVAL = 30

TIMEOUT_SEC = 5

app = Flask(__name__)


@app.route('/api/time/iso_8601', methods=['GET', 'POST'])
def wmr500_1():
    print(str(request) + ',' + str(request.args))
    return {"time": datetime.now().isoformat(sep=' ', timespec='seconds') + '+2'}, 200


@app.route('/api/time/timestamp', methods=['GET', 'POST'])
def wmr500_2():
    print(str(request) + ',' + str(request.args))
    return {"time": int(time.time())}, 200


if __name__ == '__main__':
    try:
        app.run(host='0.0.0.0', port=443, ssl_context='adhoc', threaded=True)
        while True:
            start_time = time.time()
            try:
                publish.single('enno/out/json/' + MQTT_WMR500_GUUID,
                               payload=json.dumps({"command": "getChannel1Status", "id": MQTT_WMR500_GUUID}),
                               hostname=MQTT_HOSTNAME,
                               port=1883, client_id=MQTT_CLIENT_ID,
                               auth={'username': MQTT_USERNAME, 'password': MQTT_PASSWORD})
            except Exception:
                pass
            time.sleep(SAMPLE_INTERVAL - (time.time() - start_time))
    except Exception:
        logging.exception('EXCEPTION')

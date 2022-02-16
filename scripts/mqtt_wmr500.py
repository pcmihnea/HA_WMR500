from datetime import datetime

from flask import Flask

app = Flask(__name__)


@app.route('/api/time/iso_8601', methods=['GET'])
def wmr500_1():
    return {"time": datetime.now().isoformat(sep=' ', timespec='seconds') + '+0'}, 200


if __name__ == '__main__':
    try:
        app.run(host='0.0.0.0', port=443, ssl_context='adhoc')
    except Exception:
        pass

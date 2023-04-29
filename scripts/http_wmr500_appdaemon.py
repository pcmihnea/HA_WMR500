import hassapi as hass
from datetime import datetime
    
class http_wmr500(hass.Hass):

    def initialize(self):
        self.register_endpoint(self.http_callback, "wmr")
        self.log('Registered.')

    def http_wmr500(self, args, cb_args):
        return {"time": datetime.now().isoformat(sep=' ', timespec='seconds') + '+0'}, 200

import hassapi as hass
from datetime import datetime
    
class http_wmr500(hass.Hass):

    def initialize(self):
        self.register_endpoint(self.http_callback, "wm")
        self.log('Registered.')

    async def http_callback(self, request, kwargs):
        try:
            data = await request.json()
        except Exception:
            pass
        return {"time": datetime.now().isoformat(sep=' ', timespec='seconds') + '+0'}, 200

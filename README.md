# What?
HomeAssistant integration of a Oregon Scientific WMR500C WiFi-enabled weather station.
 
# Why?
By design, the weather station works as a standalone unit, while it also supports relaying the measurements to a cloud server, which in turn interacts with the official [Android](https://play.google.com/store/apps/details?id=com.idthk.wmr500_v) or [iOS](https://apps.apple.com/us/app/smart-living-wmr500/id1332998208).  
Hardware-wise, the device has no external connection besides the charge-only USB port and the WiFi interface.  
Since the middle of 2021, the cloud services are no longer available, thus rendering the smartphone applications useless. Fortunately, part of these services can be recreated to allow local sampling of measurement values.  
No (official) documentation regarding (third-party) integration is readily available - the information contained in this repo is obtained via reverse-engineering efforts.  

# How?
Since reverse-engineering software may pose a infringement on copyrights, no binary files or dissasembly workspaces data is included in this repo.  
Instead, it is fully up to the responsibility of the user whether to reproduce the results.  

## 1. Configure the cloud service replacements
Since the integration relies on non-standard libraries, a [Home Assistant Docker installation](https://www.home-assistant.io/installation/linux#install-home-assistant-container) is assumed to be already working.  
Also, a MQTT broker (for example Mosquitto) is also [installed](https://mosquitto.org/download), [configured](https://mosquitto.org/man/mosquitto-conf-5.html) and [accesible in HA](https://www.home-assistant.io/docs/mqtt/broker).  

- The WMR500's main base relies on at least two remote services, a HTTPS server [`app.idtlive.com`](https://app.idtlive.com) and a MQTT broker [`mqtt.idtlive.com`](mqtt://mqtt.idtlive.com:1883).  
- Since neither are available anymore, new ones need to be deployed locally, and traffic to be redirected to them instead.  
- For traffic redirection, i.e. a local static DNS entry, there is one easy way that doesn't rely on network routers with complex features:
	- Configure the network router's DHCP server's secondary DNS server to the user server IP address,  
	- Install a DNS server on the user server, configuring it to assign DNS translation to local IP addresses.  
- As a example, a RaspberryPi4B+ running HomeAssistant, and assigned a IP address of 192.168.0.2, will take the role of the DNS server:  
	- On the main router (usually device that also acts as a WiFi access-point) set the secondary DNS server address to 192.168.0.2 - if necessary set the primary DNS server entry to the router's LAN IP address (for eg. 192.168.0.1).  
	- Install on the RaspberryPi the DNS server using: `sudo apt install dnsmasq`.  
	- Configure the DNS server by adding the following lines to `/etc/dnsmasq.conf`:
		```
		address=/app.idtlive.com/192.168.0.2
		address=/mqtt.idtlive.com/192.168.0.2
		```
	- Optionally, to improve network performance, add the following lines (assuming the RaspberryPi is connected via wired Ethernet):
		```
		no-hosts
		no-resolv	
		no-poll
		interface=eth0
		no-dhcp-interface=eth0
		```
	- Restart the RaspberryPi.
	- All local devices that rely on DHCP IP address assignments will now include the two DNS server addresses, 192.168.0.2 (which will resolve only `app.idtlive.com` and `mqtt.idtlive.com`) and 192.168.0.1 (which will resolve all other DNS queries).  

## 2. Configure the device
- (Optional) Reset the device to factory settings by holding both the `up` and `down` buttons on the unit for 6 seconds.  
- (Optional) Pair all external compatible sensors, by holding the `Pair` button, selecting option (2) using the `down` button, then pressing `pair`.  
- Generate the Wifi configuration string using the script [`wifi_auth_gen.py`](scripts/wifi_auth_gen.py) - replace `WIFI_SSID` and `WIFI_PASSWD` values inside the file with your WiFi credentials.  
- The config string has the following structure: `WMR500C(xxAAAAA,yyBBBBB)`, where `AAAAA` is the SSID, `xx` the number of characters in the SSID (ignoring whitespaces), `BBBBB` the password, and `yy` the number of chars in the password, for example:  
	`WMR500C(04SSID,08PASSWORD)`
- Enter WiFi pairing by holding the `Pair` button, then pressing `Pair` again.  
- Connect any PC to the `OS_WMR500C_****` Wifi AP using password `12345678`.  
- Using a Telnet client (such as [Putty](https://www.chiark.greenend.org.uk/~sgtatham/putty/latest.html) or [Realterm](https://realterm.i2cchip.com/)), connect to the server `192.168.10.1:50007`.  
- After sending the authentication string previously generated, the device responds with its GUUID and model name - take note of the first 36-chars value, as it will be used in the following steps.  
- Send a string containing `CONFIRM` to finalize the WiFi setup.  
- To allow the device to connect to the local MQTT server, its password needs to be obtained - since it's using the unsecured MQTT protocol, it can easily be sniffed using [Wireshark's](https://www.wireshark.org) TShark [command line](https://www.wireshark.org/docs/man-pages/tshark.html) - install it using `sudo apt install tshark`.  
- Run `sudo tshark -i eth0 -f "tcp port 1883" -Y 'mqtt.passwd' -V` to begin capturing all MQTT connect packets - modify the target network interface based on actual local server setup (for example `eth0`, or `wlan0`).  
- Trigger a full WiFi reconnection (cold-boot) by removing the batteries and USB power for at least 10 seconds, then replacing them.  
- After around a minute, the packet analysis of a MQTT connection attempt should be displayed in the console - take note of the `Client ID` (same as GUUID) and `Password` values on the last lines.  
- If no MQTT connect packets are received, check that the local MQTT broker is running and its authentication method is configured with a [password file or the `allow_anonymous` option](https://mosquitto.org/documentation/authentication-methods/) - use a desktop [MQTT client](http://mqtt-explorer.com/) to verify if connection with the set user/password credentials is possible.  
- Add the extracted authentication credentials to the MQTT broker's allowed users list.  
- Confirm the device is connected by running the command: `netstat -ntp | grep ESTABLISHED.*mosquitto` (for Mosquitto MQTT broker installs) - a WMR500 and/or local server restart may be required.  
- Once the device is succesfully connected to both WiFi and a local MQTT server, commands can be issued by any MQTT client that publishes to the `enno/out/json/_GUUID_` topic, where `_GUUID_` is the 36-chars GUUID (and also client ID) obtained earlier.  
- The device responds to commands by publishing to the `enno/in/json` topic.  
- A number of non-volatile parameters can be set on the main unit, using the payload `{"command": "setSettings", "XX": "YY", "id": "DEBUG"}`, where `XX` is the parameter name, and `YY` the new value. Known parameters are:  
	- `ca1`= temperature unit (integer): 0=°F, 1=°C.  
	- `ca2`= wind speed unit (integer): 0=m/s, 1=Knoten, 2=km/h, 3=mph.  
	- `ca3`= rainfall unit (integer): 0=mm, 1=inch.  
	- `ca4`= pressure unit (integer): 0=mbar, 1=hPa, 2=mmHg, 3=inHg.  
	- `ca5`= PM unit (integer): undefined.  
	- `ca6`= altitude (integer): meters.  
	- `cb1`= time zone (integer): undefined.  
	- `cb2`= time format (integer): 0=12H, 1=24H.  
	- `cb3`= language (integer): 0=EN, 1=FR, 2=GE, 3=IT, 4=ES, 5=RU.  
	- `cb4`= hemisphere (integer): 0=north, 1=south.  
	- `cb6`= latitude (double): degrees.  
	- `cb7`= longitude (double): degrees.  
	- `cb8`= city name (string): undefined.  
- For example, to set the temperature unit to °C, publish to `enno/out/json/_GUUID_` with payload `{"command": "setSettings", "ca1": "1", "id": "DEBUG"}`.  

## 3. Request the measurement values
- To obtain the latest measurement values from the WMR500, publish to `enno/out/json/_GUUID_` the payload `{"command": "getChannel1Status", "id": "_GUUID_"}`.  
- The device will publish the response to `enno/in/json/`, with a JSON payload of a fixed structure, containing a number of keys.  
- A a rule, the values of interest have the keys with the format `cXXX`, where `XXX` is a 2-3 digit number.  
- To ease documenting the JSON contents, the numeric values have been replaced with a dictionary containing the label, data type, and unit for each known parameter - a number of `_COMMENT_` key/value pairs were added to improve clarity:  
```json
{
  "type": "m",
  "correlationId": "_GUUID_",
  "ts": "2016-01-01T00:00:00.000Z",
  "deviceId": "_GUUID_",
  "data": {
    "6": {
      "result": true,
      "desc": "if false,return desc",
      "indoor": {
        "w8": { "_COMMENT_":  "general",
          "c81": {"label" : "mac", "type" : "String", "unit": "no delimiters"},
          "c82": {"label" : "firmware_version", "type" : "int", "unit": "1490=default"},
          "c83": {"label" : "hardwareversion", "type" : "int", "unit": "1=default"},
          "c84": {"label" : "batteryIsLow", "type" : "int", "unit": "0=NO, 1=YES"},
          "c85": {"label" : "pairingMode", "type" : "int", "unit": "0=NO, 1=YES"},
          "c86": {"label" : "powerAdaptor", "type" : "int", "unit": "0=NO, 1=YES"},
          "c87": {"label" : "channel1status", "type" : "int", "unit": "0=NOK, 1=OK"},
          "c88": {"label" : "channel2status", "type" : "int", "unit": "0=NOK, 1=OK"},
          "c89": {"label" : "channel3status", "type" : "int", "unit": "0=NOK, 1=OK"},
          "c811": {"label" : "location", "type" : "String", "unit": "{latitute}, {longitude}"}
        },
        "w9": { "_COMMENT_":  "indoor",
          "c91": {"label" : "temperature", "type" : "float", "unit": "°F, 210=NaN"},
          "c92": {"label" : "temperatureTrend", "type" : "int", "unit": "0=steady, 1=rise, 2=fall"},
          "c93": {"label" : "maxTemperatureToday", "type" : "float", "unit": "°F, 210=NaN"},
          "c94": {"label" : "minTemperatureToday", "type" : "float", "unit": "°F, 210=NaN"},
          "c95": {"label" : "humdityTrend", "type" : "int", "unit": "0=steady, 1=rise, 2=fall"},
          "c96": {"label" : "humdity", "type" : "int", "unit": "%, 210=NaN"},
          "c97": {"label" : "maxHumdityToday", "type" : "int", "unit": "%"},
          "c98": {"label" : "minHumdityToday", "type" : "int", "unit": "%"},
          "c99": {"label" : "heatIndex", "type" : "float", "unit": "°F, 210=NaN"},
          "c911": {"label" : "maxHeatIndexToday", "type" : "float", "unit": "°F, 210=NaN"},
          "c912": {"label" : "minHeatIndexToday", "type" : "float", "unit": "°F, 210=NaN"},
          "c913": {"label" : "dewPointTemperature", "type" : "float", "unit": "°F, 210=NaN"},
          "c914": {"label" : "maxDewPointTemperatureToday", "type" : "float", "unit": "°F"},
          "c915": {"label" : "minDewPointTemperatureToday", "type" : "float", "unit": "°F"}
        },
        "moonphase": {"label" : "moonphase", "type" : "int", "unit": "0=firstquarter, 1=fullmoon, 2=newmoon, 3=thirdquarter, 4=waningcrescent, 5=waninggibbous, 6=waxingcrescent, 7=waxinggibbous"}
      },
      "outdoor": {
        "channel1": {
          "w7": { "_COMMENT_":  "pm",
            "c75": {"label" : "undefined", "type" : "int", "unit": "undefined"},
            "c77": {"label" : "undefined", "type" : "int", "unit": "undefined"},
            "c73": {"label" : "undefined", "type" : "int", "unit": "undefined"},
            "c71": {"label" : "undefined", "type" : "int", "unit": "undefined"},
            "c76": {"label" : "undefined", "type" : "int", "unit": "undefined"},
            "c74": {"label" : "undefined", "type" : "int", "unit": "undefined"},
            "c72": {"label" : "undefined", "type" : "int", "unit": "undefined"}
          },
          "w1": { "_COMMENT_":  "general",
            "c17": {"label" : "undefined", "type" : "int", "unit": "undefined"},
            "c16": {"label" : "undefined", "type" : "int", "unit": "undefined"},
            "c14": {"label" : "undefined", "type" : "int", "unit": "undefined"},
            "c13": {"label" : "undefined", "type" : "int", "unit": "undefined"},
            "c11": {"label" : "undefined", "type" : "int", "unit": "undefined"},
            "c12": {"label" : "undefined", "type" : "int", "unit": "undefined"},
            "c15": {"label" : "undefined", "type" : "int", "unit": "undefined"}
          },
          "w5": { "_COMMENT_":  "pressure",
            "c51": {"label" : "weather_forecast", "type" : "int", "unit": "0=partly, 1=rainy, 2=cloudy, 3=sunny, 4=storm, 5=snow, 210=NaN"},
            "c52": {"label" : "pressure_trend", "type" : "int", "unit": "0=steady, 1=rise, 2=fall, 210=NaN"},
            "c53": {"label" : "pressure", "type" : "float", "unit": "mBar, 210=NaN"}
          },
          "w4": { "_COMMENT_":  "rain",
            "c41": {"label" : "today_accumulated_rainfall", "type" : "float", "unit": "mm, 210=NaN"},
            "c42": {"label" : "rain_rate", "type" : "float", "unit": "mm/h, 210=NaN"},
            "c43": {"label" : "rain_rate_max", "type" : "float", "unit": "mm/h, 210=NaN"},
            "c44": {"label" : "past_accumulated_rainfall", "type" : "float", "unit": "mm, 210=NaN"}
          },
          "w3": { "_COMMENT_":  "temperature_humidity",
            "c31": {"label" : "temperature_reading", "type" : "float", "unit": "°F, 210=NaN"},
            "c32": {"label" : "temperature_trend", "type" : "int", "unit": "0=steady, 1=rise, 2=fall"},
            "c33": {"label" : "temperature_max", "type" : "float", "unit": "°F, 210=NaN"},
            "c34": {"label" : "temperature_min", "type" : "float", "unit": "°F, 210=NaN"},
            "c35": {"label" : "humidity_reading", "type" : "int", "unit": "%, 210=NaN"},
            "c36": {"label" : "humidity_trend", "type" : "int", "unit": "0=steady, 1=rise, 2=fall"},
            "c37": {"label" : "humidity_max", "type" : "int", "unit": "%"},
            "c38": {"label" : "humidity_min", "type" : "int", "unit": "%"},
            "c39": {"label" : "heat_index", "type" : "float", "unit": "°F, 210=NaN"},
            "c311": {"label" : "heat_index_max", "type" : "float", "unit": "°F, 210=NaN"},
            "c312": {"label" : "heat_index_min", "type" : "float", "unit": "°F, 210=NaN"},
            "c313": {"label" : "dew_point_temperature", "type" : "float", "unit": "°F, 210=NaN"},
            "c314": {"label" : "dew_point_max", "type" : "float", "unit": "°F"},
            "c315": {"label" : "dew_point_min", "type" : "float", "unit": "°F"}
          },
          "w2": { "_COMMENT_":  "wind",
            "c21": {"label" : "gust_wind_speed", "type" : "float", "unit": "m/s, 210=NaN"},
            "c22": {"label" : "average_wind_speed", "type" : "float", "unit": "m/s, 210=NaN"},
            "c23": {"label" : "gust_wind_direction", "type" : "int", "unit": "0 to 15, 0=N, 4=E, 8=S, 12=W, 210=NaN"},
            "c24": {"label" : "average_wind_direction", "type" : "int", "unit": "0 to 15, 0=N, 4=E, 8=S, 12=W"},
            "c25": {"label" : "dominant_direction_last", "type" : "int", "unit": "0 to 15, 0=N, 4=E, 8=S, 12=W"},
            "c26": {"label" : "wind_chill", "type" : "float", "unit": "°F, 210=NaN"},
            "c27": {"label" : "today_min_wind_chill", "type" : "float", "unit": "°F, 210=NaN"},
            "c28": {"label" : "wind_class", "type" : "int", "unit": "0=none, 1=light, 2=moderate, 3=strong, 4=storm, 210=NaN"},
            "c29": {"label" : "today_max_gust_wind_speed", "type" : "float", "unit": "m/s"}
          }
        }
      }
    }
  }
}
```
- For example, `["data"]["6"]["indoor"]["w9"]["c91"]` will contain the current indoor temperature.  

## 4. (OPTIONAL) Patching the device
- To keep the WMR500 time and date synchronized, a HTTPS server is required to be deployed locally, so that A GET request to `https://app.idtlive.com/api/time/iso_8601` shall respond with a payload such as `{"time":"2022-01-01 00:00:00+0"}`.  
- To masquerade the official HTTPS server, the official [certificate private key](https://en.wikipedia.org/wiki/HTTPS#Server_setup) is required to sign the local server's TLS connection - unfortunately this is not possible due to obvious security issues (and lack of support from manufacturer).  
- The only solution is to modify the embedded software (firmware) on the WMR500 base station, so that it either:  
	- uses a different public key (and/or certificate) to authenticate the local server - the key (certificate) will need to be update each time the server setup change, which is not feasable,  
	- uses unsecured HTTP instead of HTTPS - no certification required, the local server can be (re)deployed without any further setup on the WMR500.  
- To perform the changes, the firmware onboard the WMR500's main microntroller, an [STM32F411RE](https://www.st.com/en/microcontrollers-microprocessors/stm32f411re.html), needs to be extracted, process which requires:
	- A SWD-compatible flasher, such as [J-Link](https://www.segger.com/products/debug-probes/j-link/) or other [OpenOCD-compatible](https://openocd.org/pages/documentation.html) tools,  
	- Connection to the WMR500 board, by removing the front bezel, unscrewing 6 screws, and soldering five signals available on the middle of the board - top-to-bottom pinout: `VCC`, `SWDIO`, `SWCLK`, `RESET`, and `GND`.  
<br><img src="docs/media/case_bezel.png" width="400"/>
<img src="docs/media/pcb_topside.png" width="400"/><br>

- Once the firmware is obtained, using the tool [Ghidra](https://github.com/NationalSecurityAgency/ghidra) for decompilation and analysis, the function calls used for enabling TLS are identified and patched (replaced). Additionally, the HTTP port can be changed from the default `443` to any other valid number.  
- For a device that reports the firmware version as `1490` (value of the key `c82` in the response obtained when requesting the measurement values), the following binary changes are to be made:  
	- Branch instruction (`BL`) at address `0x0801b614`, responsible for TLS context initialization, replaced with `NOP`,  
	- Branch instruction (`BL`) at address `0x0801b628`, responsible for TLS enabling, replaced with `NOP`,  
	- (OPTIONAL) Immediate value of Move Top instruction (`MOVW`) at address `0x0801b630`, responsible for loading the port number, replaced with the new value (for example `50007`).  
- Once the firmware is patched, flashing it back on the WMR500 base unit will enable the modifications.  

## 5. (OPTIONAL) Configure the time server
- The following steps are applicable only for a [patched device](#user-content-4-optional-patching-the-device).  
- Install the required python libraries: `sudo pip install Flask gunicorn` ([why gunicorn?](https://flask.palletsprojects.com/en/2.0.x/deploying)).  
- Edit the `http_wmr500.py` file by configuring the HTTP port (`HTTP_PORT`) patched on the device.  
- Run the Python script as root: `sudo gunicorn http_wmr500:app -b 0.0.0.0:50007`, where `50007` is the HTTP port.  
- (Optional) Configure the script to run at startup, for example by adding it to `/etc/rc.local`.  

## 6. Configure the HomeAssistant instance
- Add the following lines in `configuration.yaml` file (present inside the user-defined `homeassistant` configuration folder).  
Take note of the `state_topic` value, where `wmr500` is a example that shall be subtituted with the exact value of `MQTT_CLIENT_ID` parameter set at step 3.  
Also, as the WMR500 reports a high number of measurements (over 55), user discretion is advised in selecting which measurement to be integrated in the HomeAssistant instance.  
```
sensor:
  - platform: mqtt
    name: INDOOR_TEMP
    unique_id: "wmr500_indoor_temp"
    state_topic: "enno/in/json"
    value_template: "{{ value_json['data']['6']['indoor']['w9']['c91'] }}"
    device_class: temperature
    unit_of_measurement: "°F"
  - platform: mqtt
    name: INDOOR_HUMID
    unique_id: "wmr500_indoor_humid"
    state_topic: "enno/in/json"
    value_template: "{{ value_json['data']['6']['indoor']['w9']['c96'] }}"
    device_class: humidity
    unit_of_measurement: "%"
  - platform: mqtt
    name: OUTDOOR_TEMP
    unique_id: "wmr500_outdoor_temp"
    state_topic: "enno/in/json"
    value_template: "{{ value_json['data']['6']['outdoor']['channel1']['w3']['c31'] }}"
    device_class: temperature
    unit_of_measurement: "°F"
  - platform: mqtt
    name: OUTDOOR_HUMID
    unique_id: "wmr500_outdoor_humid"
    state_topic: "enno/in/json"
    value_template: "{{ value_json['data']['6']['outdoor']['channel1']['w3']['c35'] }}"
    device_class: humidity
    unit_of_measurement: "%"
```

- Add the following lines in `automations.yaml` file (present in the same configuration folder).  
Take note of the values `_AUTOMATION_ID_` (random 13-digit value, unique to the automation), `trigger` (`seconds: /30` means every 30 seconds, for eg. 1 minute replace it with `minutes: /1`), and `_GUUID_` (WMR500's GUUID).  
```
- id: '_AUTOMATION_ID_'
  alias: WMR500_Update_Trigger
  description: ''
  trigger:
  - platform: time_pattern
    seconds: /30
  condition: []
  action:
  - service: mqtt.publish
    data:
      topic: enno/out/json/_GUUID_
      payload: '{"command": "getChannel1Status", "id": "_GUUID_"}'
  mode: single
  ```
- If all is well, after a HA restart the newly created sensors shall be available.

# Who/where/when?
All the reverse-engineering, development, integration, and documentation efforts are based on the latest software and hardware versions available at the time of writing (February 2022), and licensed under the GNU General Public License v3.0.

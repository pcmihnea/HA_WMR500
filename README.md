# What?
HomeAssistant integration of a Oregon Scientific WMR500C WiFi-enabled weather station.
 
# Why?
By design, the weather station works as a standalone unit, while it also supports relaying the measurements to a cloud server, which in turn interacts with the official [Android](https://play.google.com/store/apps/details?id=com.idthk.wmr500_v) or [iOS](https://apps.apple.com/us/app/smart-living-wmr500/id1332998208) applications.  
Hardware-wise, the device has no other usable external interfaces, besides the charge-only USB port and the WiFi interface.  

Ever since the middle of 2021, the cloud services are no longer available, thus rendering the smartphone apps useless. Fortunately, part of these services can be masqueraded to allow local sampling of measurement values.  
No (official) documentation regarding (third-party) integration is available - the information contained in this repo is based on reverse-engineering efforts.  

# How?
Since reverse-engineering software may pose a infringement on copyrights, it is full responsibility of the user whether to reproduce the results or not.  

In the following steps, the main unit will be referenced as `WMR500`, or just `device`.  

## 1. Define the cloud services replacements
The WMR500 relies on at least two cloud services, a HTTPS server [`app.idtlive.com`](https://app.idtlive.com) and a MQTT broker [`mqtt.idtlive.com`](mqtt://mqtt.idtlive.com:1883).  
Since neither are available anymore, new ones need to be deployed locally, and WMR500's traffic to be redirected to them instead.  

For traffic routing, a local static DNS entry is required - one method that doesn't depend on more advanced network routers is to:
- Install a DNS server on a user server, configuring it to assign DNS translation to local IP addresses,  
- Configure the network router's DHCP server's advertised secondary DNS server to the user server IP address.  

As a example, for a RaspberryPi4B+ assigned a IP address of `192.168.0.2`, connected to a router with LAN address `192.168.0.1`:  
- Install a DNS server using: `sudo apt install dnsmasq`.  
- Configure the DNS server by adding the following lines to `/etc/dnsmasq.conf`:
		```
		address=/app.idtlive.com/192.168.0.2
		address=/mqtt.idtlive.com/192.168.0.2
		```
- Optionally, to further improve network performance, add the following lines (only if the RaspberryPi is connected via wired Ethernet):
		```
		no-hosts
		no-resolv
		no-poll
		interface=eth0
		no-dhcp-interface=eth0
		```
- Reboot the RaspberryPi.  
- On the main router set the secondary DNS server address to `192.168.0.2` - if necessary set the primary DNS server entry to the router's LAN IP address (for eg. `192.168.0.1`).  
- All local devices that rely on DHCP IP address assignments will now have the two DNS server addresses advertised to, `192.168.0.2 `(which will resolve only `app.idtlive.com` and `mqtt.idtlive.com`) and `192.168.0.1` (which will resolve all other DNS queries).  

## 2. Configure the device
- (Optional) Reset the WMR500 to factory settings by holding both the `up` and `down` buttons on the unit for 6 seconds.  
- (Optional) Pair all external compatible sensors, by holding the `Pair` button, selecting option (2) using the `down` button, then pressing `pair`.  
- Generate the Wifi configuration string using the script [`wifi_auth_gen.py`](scripts/wifi_auth_gen.py) - replace the `WIFI_SSID` and `WIFI_PASSWD` values inside the file with own WiFi credentials.  
The config string has the structure `WMR500C(xxAAAAA,yyBBBBB)`, where `AAAAA` is the SSID, `xx` the number of characters in the SSID (excluding whitespaces), `BBBBB` the password, and `yy` the number of chars in the password, for example: `WMR500C(04SSID,08PASSWORD)`.
- Enter WiFi pairing by holding the `Pair` button, then pressing `Pair` again.  
- Connect any computer to the `OS_WMR500C_****` WiFi access point using WPA2 password `12345678`.  
- Using a Telnet client, such as [Putty](https://www.chiark.greenend.org.uk/~sgtatham/putty/latest.html) or [MobaXterm](https://mobaxterm.mobatek.net/download-home-edition.html), connect to the server `192.168.10.1:50007`.  
- After sending the authentication string previously generated, the WMR500 responds with a ID and model name - take note of the first 36-chars value (GUUID, and also MQTT client ID), as it will be used in the next steps.  
- Send the string `CONFIRM` to finalize the WiFi setup.  
- To allow the WMR500 to connect to the local MQTT server, its MQTT client password needs to be obtained - as it's using the unsecured MQTT protocol, it can easily be sniffed out using [Wireshark's](https://www.wireshark.org) TShark [command line](https://www.wireshark.org/docs/man-pages/tshark.html) utility, when run on the replacement server defined in [chapter 1](#user-content-1-define-the-cloud-services-replacements).
- Install the tool using `sudo apt install tshark`, then run it via `sudo tshark -i eth0 -f "tcp port 1883" -Y 'mqtt.passwd' -V` to begin capturing all MQTT connect packets - modify the target network interface based on actual local server setup (for example `eth0` for wired network, or `wlan0` for wireless).  
- Trigger a full WiFi reconnection (cold-boot) by removing the batteries and USB power for at least 10 seconds, then replacing them.  
- After around a minute, the packet analysis of a MQTT connection attempt should be displayed in the console - take note of the `Client ID` (same as GUUID) and `Password` values on the last lines.  
If no MQTT connect packets are received, check that the local MQTT broker is running and its authentication method is configured with a [password file or the `allow_anonymous` option](https://mosquitto.org/documentation/authentication-methods/) - use a desktop [MQTT client](http://mqtt-explorer.com/) to verify if connection with the set user/password credentials is actually possible.  
- Add the extracted authentication credentials to the MQTT broker's allowed users list.  
- Confirm the WMR500 is connected for eg. by running command `netstat -ntp | grep ESTABLISHED.*mosquitto` if using a Mosquitto MQTT broker. If the command doesn't return any value, a restart of WMR500 and/or local server may be required.  
- Once the WMR500 is successfully connected to both WiFi and a local MQTT server, commands can be issued by any MQTT client that publishes to the `enno/out/json/_GUUID_` topic, where `_GUUID_` is the 36-chars GUUID previously obtained.  
- The WMR500 reacts to commands by publishing its responses on the `enno/in/json` topic.  

A number of non-volatile parameters can be set on the main unit, using the payload `{"command": "setSettings", "XX": "YY", "id": "DEBUG"}`, where `XX` is the parameter name, and `YY` the new value. Known parameters are:  

	- `ca1`= temperature unit (integer): 0=dgrF, 1=dgrC.  
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

For example, to set the temperature unit to dgrC, publish to `enno/out/json/_GUUID_` with payload `{"command": "setSettings", "ca1": "1", "id": "DEBUG"}`.  

## 3. Request the measurement values
To obtain the latest measurement values from the WMR500, publish to `enno/out/json/_GUUID_` the payload `{"command": "getChannel1Status", "id": "_GUUID_"}` (replace `_GUUID_` with the 36-chars GUUID).  
The WMR500 will publish the response to `enno/in/json/`, with a JSON payload of a fixed structure, containing a number of keys, as shown below.  
To ease in documenting the JSON contents, the numeric values have been replaced with a dictionary containing the label, data type, and unit (`"_Label_", "_Type_", "_Unit_"`) for each known parameter - a number of `_Comment_` key/value pairs were also added for clarity.  
As a rule, the values of interest have the keys with the naming format of `cXXX`, where `XXX` is a 2-3 digit number.  
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
        "w8": { "_Comment_":  "general",
          "c81": {"_Label_" : "mac", "_Type_" : "String", "_Unit_": "no delimiters"},
          "c82": {"_Label_" : "firmware_version", "_Type_" : "int", "_Unit_": "1490=default"},
          "c83": {"_Label_" : "hardwareversion", "_Type_" : "int", "_Unit_": "1=default"},
          "c84": {"_Label_" : "batteryIsLow", "_Type_" : "int", "_Unit_": "0=NO, 1=YES"},
          "c85": {"_Label_" : "pairingMode", "_Type_" : "int", "_Unit_": "0=NO, 1=YES"},
          "c86": {"_Label_" : "powerAdaptor", "_Type_" : "int", "_Unit_": "0=NO, 1=YES"},
          "c87": {"_Label_" : "channel1status", "_Type_" : "int", "_Unit_": "0=NOK, 1=OK"},
          "c88": {"_Label_" : "channel2status", "_Type_" : "int", "_Unit_": "0=NOK, 1=OK"},
          "c89": {"_Label_" : "channel3status", "_Type_" : "int", "_Unit_": "0=NOK, 1=OK"},
          "c811": {"_Label_" : "location", "_Type_" : "String", "_Unit_": "{latitute}, {longitude}"}
        },
        "w9": { "_Comment_":  "indoor",
          "c91": {"_Label_" : "temperature", "_Type_" : "float", "_Unit_": "dgrF, 210=NaN"},
          "c92": {"_Label_" : "temperatureTrend", "_Type_" : "int", "_Unit_": "0=steady, 1=rise, 2=fall"},
          "c93": {"_Label_" : "maxTemperatureToday", "_Type_" : "float", "_Unit_": "dgrF, 210=NaN"},
          "c94": {"_Label_" : "minTemperatureToday", "_Type_" : "float", "_Unit_": "dgrF, 210=NaN"},
          "c95": {"_Label_" : "humdityTrend", "_Type_" : "int", "_Unit_": "0=steady, 1=rise, 2=fall"},
          "c96": {"_Label_" : "humdity", "_Type_" : "int", "_Unit_": "%, 210=NaN"},
          "c97": {"_Label_" : "maxHumdityToday", "_Type_" : "int", "_Unit_": "%"},
          "c98": {"_Label_" : "minHumdityToday", "_Type_" : "int", "_Unit_": "%"},
          "c99": {"_Label_" : "heatIndex", "_Type_" : "float", "_Unit_": "dgrF, 210=NaN"},
          "c911": {"_Label_" : "maxHeatIndexToday", "_Type_" : "float", "_Unit_": "dgrF, 210=NaN"},
          "c912": {"_Label_" : "minHeatIndexToday", "_Type_" : "float", "_Unit_": "dgrF, 210=NaN"},
          "c913": {"_Label_" : "dewPointTemperature", "_Type_" : "float", "_Unit_": "dgrF, 210=NaN"},
          "c914": {"_Label_" : "maxDewPointTemperatureToday", "_Type_" : "float", "_Unit_": "dgrF"},
          "c915": {"_Label_" : "minDewPointTemperatureToday", "_Type_" : "float", "_Unit_": "dgrF"}
        },
        "moonphase": {"_Label_" : "moonphase", "_Type_" : "int", "_Unit_": "0=firstquarter, 1=fullmoon, 2=newmoon, 3=thirdquarter, 4=waningcrescent, 5=waninggibbous, 6=waxingcrescent, 7=waxinggibbous"}
      },
      "outdoor": {
        "channel1": {
          "w7": { "_Comment_":  "pm",
            "c75": {"_Label_" : "undefined", "_Type_" : "int", "_Unit_": "undefined"},
            "c77": {"_Label_" : "undefined", "_Type_" : "int", "_Unit_": "undefined"},
            "c73": {"_Label_" : "undefined", "_Type_" : "int", "_Unit_": "undefined"},
            "c71": {"_Label_" : "undefined", "_Type_" : "int", "_Unit_": "undefined"},
            "c76": {"_Label_" : "undefined", "_Type_" : "int", "_Unit_": "undefined"},
            "c74": {"_Label_" : "undefined", "_Type_" : "int", "_Unit_": "undefined"},
            "c72": {"_Label_" : "undefined", "_Type_" : "int", "_Unit_": "undefined"}
          },
          "w1": { "_Comment_":  "general",
            "c17": {"_Label_" : "undefined", "_Type_" : "int", "_Unit_": "undefined"},
            "c16": {"_Label_" : "undefined", "_Type_" : "int", "_Unit_": "undefined"},
            "c14": {"_Label_" : "undefined", "_Type_" : "int", "_Unit_": "undefined"},
            "c13": {"_Label_" : "undefined", "_Type_" : "int", "_Unit_": "undefined"},
            "c11": {"_Label_" : "undefined", "_Type_" : "int", "_Unit_": "undefined"},
            "c12": {"_Label_" : "undefined", "_Type_" : "int", "_Unit_": "undefined"},
            "c15": {"_Label_" : "undefined", "_Type_" : "int", "_Unit_": "undefined"}
          },
          "w5": { "_Comment_":  "pressure",
            "c51": {"_Label_" : "weather_forecast", "_Type_" : "int", "_Unit_": "0=partly, 1=rainy, 2=cloudy, 3=sunny, 4=storm, 5=snow, 210=NaN"},
            "c52": {"_Label_" : "pressure_trend", "_Type_" : "int", "_Unit_": "0=steady, 1=rise, 2=fall, 210=NaN"},
            "c53": {"_Label_" : "pressure", "_Type_" : "float", "_Unit_": "mBar, 210=NaN"}
          },
          "w4": { "_Comment_":  "rain",
            "c41": {"_Label_" : "today_accumulated_rainfall", "_Type_" : "float", "_Unit_": "mm, 210=NaN"},
            "c42": {"_Label_" : "rain_rate", "_Type_" : "float", "_Unit_": "mm/h, 210=NaN"},
            "c43": {"_Label_" : "rain_rate_max", "_Type_" : "float", "_Unit_": "mm/h, 210=NaN"},
            "c44": {"_Label_" : "past_accumulated_rainfall", "_Type_" : "float", "_Unit_": "mm, 210=NaN"}
          },
          "w3": { "_Comment_":  "temperature_humidity",
            "c31": {"_Label_" : "temperature_reading", "_Type_" : "float", "_Unit_": "dgrF, 210=NaN"},
            "c32": {"_Label_" : "temperature_trend", "_Type_" : "int", "_Unit_": "0=steady, 1=rise, 2=fall"},
            "c33": {"_Label_" : "temperature_max", "_Type_" : "float", "_Unit_": "dgrF, 210=NaN"},
            "c34": {"_Label_" : "temperature_min", "_Type_" : "float", "_Unit_": "dgrF, 210=NaN"},
            "c35": {"_Label_" : "humidity_reading", "_Type_" : "int", "_Unit_": "%, 210=NaN"},
            "c36": {"_Label_" : "humidity_trend", "_Type_" : "int", "_Unit_": "0=steady, 1=rise, 2=fall"},
            "c37": {"_Label_" : "humidity_max", "_Type_" : "int", "_Unit_": "%"},
            "c38": {"_Label_" : "humidity_min", "_Type_" : "int", "_Unit_": "%"},
            "c39": {"_Label_" : "heat_index", "_Type_" : "float", "_Unit_": "dgrF, 210=NaN"},
            "c311": {"_Label_" : "heat_index_max", "_Type_" : "float", "_Unit_": "dgrF, 210=NaN"},
            "c312": {"_Label_" : "heat_index_min", "_Type_" : "float", "_Unit_": "dgrF, 210=NaN"},
            "c313": {"_Label_" : "dew_point_temperature", "_Type_" : "float", "_Unit_": "dgrF, 210=NaN"},
            "c314": {"_Label_" : "dew_point_max", "_Type_" : "float", "_Unit_": "dgrF"},
            "c315": {"_Label_" : "dew_point_min", "_Type_" : "float", "_Unit_": "dgrF"}
          },
          "w2": { "_Comment_":  "wind",
            "c21": {"_Label_" : "gust_wind_speed", "_Type_" : "float", "_Unit_": "m/s, 210=NaN"},
            "c22": {"_Label_" : "average_wind_speed", "_Type_" : "float", "_Unit_": "m/s, 210=NaN"},
            "c23": {"_Label_" : "gust_wind_direction", "_Type_" : "int", "_Unit_": "0 to 15, 0=N, 4=E, 8=S, 12=W, 210=NaN"},
            "c24": {"_Label_" : "average_wind_direction", "_Type_" : "int", "_Unit_": "0 to 15, 0=N, 4=E, 8=S, 12=W"},
            "c25": {"_Label_" : "dominant_direction_last", "_Type_" : "int", "_Unit_": "0 to 15, 0=N, 4=E, 8=S, 12=W"},
            "c26": {"_Label_" : "wind_chill", "_Type_" : "float", "_Unit_": "dgrF, 210=NaN"},
            "c27": {"_Label_" : "today_min_wind_chill", "_Type_" : "float", "_Unit_": "dgrF, 210=NaN"},
            "c28": {"_Label_" : "wind_class", "_Type_" : "int", "_Unit_": "0=none, 1=light, 2=moderate, 3=strong, 4=storm, 210=NaN"},
            "c29": {"_Label_" : "today_max_gust_wind_speed", "_Type_" : "float", "_Unit_": "m/s"}
          }
        }
      }
    }
  }
}
```
For example, `["data"]["6"]["indoor"]["w9"]["c91"]` will contain the current indoor temperature.  

## 4. (OPTIONAL) Patch the device firmware
To keep the WMR500 time and date synchronized, a HTTPS server is required to be deployed locally, so that a GET request to `https://app.idtlive.com/api/time/iso_8601` shall be responded with a payload of format `{"time":"2023-01-01 00:00:00+0"}`.  
In order to masquerade the original HTTPS server, the official [certificate private key](https://en.wikipedia.org/wiki/HTTPS#Server_setup) is mandatory to sign the local server's TLS connection - unfortunately this is not possible due to obvious security issues and lack of support from manufacturer.  
The only solution is to modify the embedded software (firmware) on the WMR500 base station, so that it either:  
- Uses a different public key (and/or certificate) to authenticate the local server. the key (certificate) will need to be updated each time the server setup changes,  
- Uses unsecured HTTP instead of HTTPS - no certification required, the local server can be (re)deployed without any further changes on the WMR500.  

To perform the changes, the firmware onboard the WMR500's main microcontroller ([STM32F411RE](https://www.st.com/en/microcontrollers-microprocessors/stm32f411re.html)), needs to be patched, process which requires:  
- Opening the case, by removing the two grey bezels on the front of the device, then unscrewing 6 screws under the outer bezel and one screw under the inner one,  
- Soldering five wires to the testpoints available on the middle of the board - pinout from top to bottom: `VCC` (3.3V), `SWDIO`, `SWCLK`, `RESET` (active-low), and `GND`,  
<br><img src="docs/media/case_bezel.png" width="400"/>
<img src="docs/media/pcb_topside.png" width="400"/><br>
- Reading the firmware using a SWD-compatible flasher, such as a [J-Link](https://www.segger.com/products/debug-probes/j-link/) or any [OpenOCD-compatible](https://openocd.org/pages/documentation.html) tool.   
If using a J-Link, one may dump the full flash contents as a binary file by means of the included [command-line utility](https://wiki.segger.com/J-Link_Commander) via command `SaveBin C:\wmr500_firmware.bin 0x00 0x80000`.  
- Once the firmware is obtained, using the [Ghidra](https://github.com/NationalSecurityAgency/ghidra) tool for disassembly and analysis, parts of the instructions including those responsible for enabling TLS, are identified and patched.  

See [chapter 7](#user-content-7-optional-further-firmware-analysis) for reproducing locally the workspace setup.  
- Flashing the modified firmware on the WMR500 will enable the changes.  

Notes:
1. To obtain firmware version number, either:  
	- check value of key `c82` in the response obtained in [chapter 3](#user-content-3-request-the-measurement-values),  
	- hold `select` and `up` buttons on the WMR500 for two seconds.  
2. A non-modified firmware dump version v1490 is included [in this repo](firmware/wmr500_1490_original.bin), besides an [older](firmware/wmr500_1476_original.bin) version `1476`.  

<br>

For a WMR500 that reports the firmware version as `1490`, there are two approaches to serving it the date and time, by either running a Python script:  

- On any generic server/PC. If opening custom ports is not available in for eg. Home Assistant OS, this case requires an additional device to expose the service,  
- Inside the [AppDaemon](https://github.com/hassio-addons/addon-appdaemon) add-on for Home Assistant. This option is best suited for running on standard HA installs such as [RPi's](https://www.home-assistant.io/installation/raspberrypi#install-home-assistant-operating-system).  

Both approaches require at minimum the following binary firmware patches:  
- Branch instruction (`BL`) at address `0x0801b614` (responsible for TLS context initialization) to be replaced with `NOP`,  
- Branch instruction (`BL`) at address `0x0801b628` (responsible for TLS enabling) to be replaced with `NOP`.  

If using second approach, additional changes are necessary:  
- Raw data bytes at address `0x080491a4` (used for issuing the HTTP request) to be replaced from `47 45 54 20 2f 61 70 69 2f 74 69 6d 65 2f 69 73 6f 5f 38 36 30 31` to `47 45 54 20 2F 61 70 69 2F 61 70 70 64 61 65 6D 6F 6E 2F 77 6D 72`.  
As the Appdaemon REST API is [limited](https://appdaemon.readthedocs.io/en/latest/APPGUIDE.html#restful-api-support), this patch replaces the default HTTP request URI from `/api/time/iso_8601` to a supported one `/api/appdaemon/wmr`.  
- Immediate value of Add (`ADDS`), at address `0x0801b630`, to be replaced with `2`.  
The current Appdaemon implementation returns a JSON string with two whitespaces after the keys and values delimiter (`"time":__"value"`) instead of one (`"time":_"value"`), thus preventing the WMR500 in correctly parsing the values. Changing from `1` to `2` allows jumping to the correct start position of the JSON value.  

Immediate value of Move Top instruction (`MOVW`), at address `0x0801b630` (responsible with setting the HTTP server port number), is to be replaced with the desired value (`1` to `65535` decimal). Factory default is `443`, while for the second approach the Appdaemon port is by default `5050`.  

Two patched firmware images are present in this repo, for both [first](firmware/wmr500_1490_patched_generic.hex) (port `443`) and [second](firmware/wmr500_1490_patched_appdaemon.hex) approach (port `5050`).  

## 5. (OPTIONAL) Configure the time server
The following steps are applicable only for a WMR500 with a patched firmware, as per [chapter 4](#user-content-4-optional-patch-the-device-firmware).  
If using the first approach (generic server):  
- Install the required python libraries: `sudo pip install flask gunicorn` ([why gunicorn?](https://flask.palletsprojects.com/en/2.2.x/deploying)).  
- Optionally, edit the `http_wmr500_generic.py` file by configuring the HTTP port (`HTTP_PORT`) as to the one patched on the WMR500 (default `443`).  
- Run the Python script as root: `sudo gunicorn http_wmr500_generic:app -b 0.0.0.0:xxxx`, where `xxxx` is the chosen HTTP port.  

If using the second approach (Appdaemon):  
- Copy the `http_wmr500_appdaemon.py` file to the Appdaemon [app folder](https://github.com/hassio-addons/addon-appdaemon/blob/main/appdaemon/DOCS.md) (for eg. `/config/appdaemon/apps` in a Home Assistant OS installation).  
- Add the new module to app list file `apps.yaml` (present in the same folder as above), by appending the following lines:  
```
http_wmr500:
  module: http_wmr500_appdaemon
  class: http_wmr500
```
- Wait for Appdaemon to automatically reload the new module, or restart it manually.  

## 6. Configure the HomeAssistant instance
- Add the following lines in `automations.yaml` file (present in the same configuration folder).  
Take note of the values `_AUTOMATION_ID_` (random 13-digit value, unique to the automation), `trigger` (where `minutes: /1` means every 60 seconds), and `_GUUID_` (WMR500's GUUID).  
```
- id: '_AUTOMATION_ID_'
  alias: WMR500_Update_Trigger
  description: ''
  trigger:
  - platform: time_pattern
    minutes: /1
  condition: []
  action:
  - service: mqtt.publish
    data:
      topic: enno/out/json/_GUUID_
      payload: '{"command": "getChannel1Status", "id": "_GUUID_"}'
  mode: single
  ```

- Add the following lines in `configuration.yaml` file (present inside the user-defined `homeassistant` configuration folder).  
As the WMR500 reports a high number of measurements (over 55), user discretion is advised in selecting which measurement to be integrated in the HomeAssistant instance.  
Note: `expire_after` value should be set at least three times the sample period (as defined by the automation trigger period), for eg. 3*60=180.  
```
mqtt:
    sensor:
      - name: INDOOR_TEMP
        unique_id: "wmr500_indoor_temp"
        state_topic: "enno/in/json"
        value_template: "{{ value_json['data']['6']['indoor']['w9']['c91'] }}"
        device_class: temperature
        state_class: measurement
        unit_of_measurement: "°F"
        expire_after: 180
      - name: INDOOR_HUMID
        unique_id: "wmr500_indoor_humid"
        state_topic: "enno/in/json"
        value_template: "{{ value_json['data']['6']['indoor']['w9']['c96'] }}"
        device_class: humidity
        state_class: measurement
        unit_of_measurement: "%"
        expire_after: 180
      - name: OUTDOOR_TEMP
        unique_id: "wmr500_outdoor_temp"
        state_topic: "enno/in/json"
        value_template: "{{ value_json['data']['6']['outdoor']['channel1']['w3']['c31'] }}"
        device_class: temperature
        state_class: measurement
        unit_of_measurement: "°F"
        expire_after: 180
      - name: OUTDOOR_HEAT_INDEX
        unique_id: "wmr500_outdoor_heat_index"
        state_topic: "enno/in/json"
        value_template: "{{ value_json['data']['6']['outdoor']['channel1']['w3']['c39'] }}"
        device_class: temperature
        state_class: measurement
        unit_of_measurement: "°F"
        expire_after: 180
      - name: OUTDOOR_DEW_POINT
        unique_id: "wmr500_outdoor_dew_point"
        state_topic: "enno/in/json"
        value_template: "{{ value_json['data']['6']['outdoor']['channel1']['w3']['c313'] }}"
        device_class: temperature
        state_class: measurement
        unit_of_measurement: "°F"
        expire_after: 180
      - name: OUTDOOR_WIND_CHILL
        unique_id: "wmr500_outdoor_wind_chill"
        state_topic: "enno/in/json"
        value_template: "{{ value_json['data']['6']['outdoor']['channel1']['w2']['c26'] }}"
        device_class: temperature
        state_class: measurement
        unit_of_measurement: "°F"
        expire_after: 180
      - name: OUTDOOR_HUMID
        unique_id: "wmr500_outdoor_humid"
        state_topic: "enno/in/json"
        value_template: "{{ value_json['data']['6']['outdoor']['channel1']['w3']['c35'] }}"
        device_class: humidity
        state_class: measurement
        unit_of_measurement: "%"
        expire_after: 180
      - name: OUTDOOR_WIND
        unique_id: "wmr500_outdoor_wind"
        state_topic: "enno/in/json"
        value_template: "{{ ( value_json['data']['6']['outdoor']['channel1']['w2']['c21'] | float * 3.6 ) | round(2)}}"
        device_class: wind_speed
        state_class: measurement
        unit_of_measurement: "km/h"
        expire_after: 180
      - name: OUTDOOR_RAIN
        unique_id: "wmr500_outdoor_rain"
        state_topic: "enno/in/json"
        value_template: "{{ value_json['data']['6']['outdoor']['channel1']['w4']['c41'] }}"
        device_class: distance
        state_class: measurement
        unit_of_measurement: "mm"
        expire_after: 180
      - name: OUTDOOR_PRESS
        unique_id: "wmr500_outdoor_press"
        state_topic: "enno/in/json"
        value_template: "{{ value_json['data']['6']['outdoor']['channel1']['w5']['c53'] }}"
        device_class: pressure
        state_class: measurement
        unit_of_measurement: "hPa"
        expire_after: 180
      - name: INDOOR_BATT
        unique_id: "wmr500_indoor_batt"
        state_topic: "enno/in/json"
        value_template: >
          {% set v = value_json['data']['6']['indoor']['w8']['c84'] %}
          {% set n = 100 if v == 0 else 0 %}
          {{ v }}
        device_class: battery
        state_class: measurement
        unit_of_measurement: "%"
        expire_after: 180
      - name: OUTDOOR_BATT
        unique_id: "wmr500_outdoor_batt"
        state_topic: "enno/in/json"
        value_template: >
          {% set v = value_json['data']['6']['indoor']['w8']['c84'] %}
          {% set n = 100 if v == 1 else 0 %}
          {{ v }}
        device_class: battery
        state_class: measurement
        unit_of_measurement: "%"
        expire_after: 180
```

- If all is well, after a HA restart the newly created sensors shall be available.

## 7. (OPTIONAL) Further firmware analysis
All the previous steps were documented based on findings from decompiling/disassembly of both the Android app and the WMR500's firmware - as to be expected, there are many unknown features and also known issues still to be addressed.  
One example is when the WMR500 randomly stops working correctly (no longer publishes on any MQTT topics), thus requiring a hardware reboot (power cycle).  

Hardware-wise, the WMR500's main logic is controlled by a [STM32F411RE](https://www.st.com/en/microcontrollers-microprocessors/stm32f411re.html) microcontroller, complemented by a [MX25L1606E](https://datasheet.lcsc.com/lcsc/1912111437_MXIC-Macronix-MX25L1606EM2I-12G_C415878.pdf) SPI flash memory.  
Based on memory content dumps, the external flash storage includes information such as user configuration (WiFi credentials, unit of measurements, etc.) and data statistics (min/max measurements, trends).  

To further enhance the overall functionality by means of firmware analysis, one may setup a reverse-engineering environment, based on the [Ghidra](https://github.com/NationalSecurityAgency/ghidra) software solution.  
Note: the following steps are for Ghidra [version 10.4](https://github.com/NationalSecurityAgency/ghidra/releases/tag/Ghidra_10.4_build).  
- Once [installed and run](https://github.com/NationalSecurityAgency/ghidra#install), create a new non-shared Project via `File` -> `New project`.  
- Using `File` -> `Import File`, select the binary file dumped in a [chapter 4](#user-content-4-optional-patch-the-device-firmware).  
- Based on the targeted microcontroller, select `Language` as `ARM v7 32 little default`, then in the `Options` menu on the bottom-left set name to `ROM` and base address to `80000000`, after which close both windows via `Ok`.
- Double-click the newly imported file to open the main development window - click `No` if asked to begin analyzing.  
- Via the `Window` top menu, select `Memory map`, then uncheck the `W` checkbox for the `ROM` area.  
- Click the green plus button to add a new memory space with the following settings: name `RAM`, start address `20000000`, length `0x20000`, flags `read`, `write`, and `volatile`.  
<img src="docs/media/memory_map.png" width="600"/><br>
- After closing the window, click `Analysis` -> `Auto Analyze`, leave all settings to default, then click `Analyze` to begin disassembly of the source file.  
- Wait a few minutes until the process is completed - see the bottom-right progress bar.  
- On the `Window` menu, one may browse through multiple views, including:
  - `Symbol tree` for functions (subroutines),  
  - `Defined data` for variables and constants,  
  - `Defined strings` for constant strings (char arrays).  
- Best starting point may be going through the in-code usage of various key strings, focusing on those that include keywords related to the target functionality (for eg. `TLS`, `socket`, `connected`, etc.).  
One notable hint is the string at address `0x80051ad8` - `Starting WICED v3.5.2`, which mentions the library used for networking; although deprecated around 2017, [backups](https://community.infineon.com/t5/Wi-Fi-Combo/WICED-Studio-5-2-0-has-been-released/td-p/74554s) could still be available.  
- Using the library source files, one may cross-reference the function structures of known libraries to the disassembled code (which may not contain useful debug symbols such as function names).  
- Another method of understanding the inner workings is through blind debugging of the firmware dump image - if a variable (or function) is found to be of interest, one may set a breakpoint on it to evaluate it's value (or call context).  
- Finally, due to the design of the firmware, debugging printout is available via the hardware serial port (3.3V-only), accessible on-board the WMR500 through the `ML_TX` pin.  

# Who/where/when?
All the reverse-engineering, development, integration, and documentation efforts are based on the latest software and hardware versions available at the time of writing (November 2023), and licensed under the GNU General Public License v3.0.

import logging

WIFI_SSID = 'SSID'
WIFI_PASSWD = 'PASSWORD'


def string_formatter(input_string):
    input_string = ''.join(char for char in input_string.strip() if char.isprintable())
    return '{:02}{}'.format(len(input_string), input_string)


if __name__ == '__main__':
    try:
        print('WMR500C({},{})'.format(string_formatter(WIFI_SSID), string_formatter(WIFI_PASSWD)))
    except Exception:
        logging.exception('EXCEPTION')

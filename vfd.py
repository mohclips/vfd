# vim: noai:ts=4:sw=4

import serial
import requests

from struct import *
import time

import logging
import logging.handlers
import sys

# your WU api key
from weather_underground_api import *
WU_API="https://api.weather.com/v2/pws/observations/current?stationId="+STATION_ID+"&format=json&units=e&apiKey="+API_KEY

top="/dev/ttyS5"
middle="/dev/ttyS7"
bottom="/dev/ttyS6"
ports = [] # top, middle, bottom
displaydelay=5; # how long before each messages is displayed

DISPLAY_UPDATE_DELAY=300
DISPLAY_INIT_DELAY=1
MAX_RETRY_COUNT=30 # numbe rof times to attempt to connect to API

#
# Logging setup
#
# https://stackoverflow.com/questions/6234405/logging-uncaught-exceptions-in-python
# general log level is INFO .  DEBUG here shows urllib3 debug lines
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s %(message)s') # write to stdout

my_logger = logging.getLogger('VFDLogger')
# our app log level is DEBUG
my_logger.setLevel(logging.DEBUG)

# send to syslog
handler = logging.handlers.SysLogHandler(address = '/dev/log')
# our app formatting
formatter = logging.Formatter('%(levelname)s %(name)s %(module)s.%(funcName)s: %(message)s') # write to syslog
handler.setFormatter(formatter)
my_logger.addHandler(handler)

def my_err_handler(exctype, value, tb):
    my_logger.exception("Uncaught exception: Type:{0} Value:{1} Traceback:{2}".format(str(exctype), str(value), str(tb)) )
    # the below may or may not work
    if ports.len() > 0:
        my_init_display()
        write_text(str(exctype))    

# Install exception handler
sys.excepthook = my_err_handler
#
# End Logging setup
#

# our API string
my_logger.debug(WU_API)



############################### VFD ###############################
# Global serial port to send commands to
serial_port = None

def send_serial(text):
    serial_port.write(text)

def send_command(cmd):
    send_serial(pack("BB",0x1B, cmd)) # B = byte 8 bit

def send_commandEx(cmd):
    # send a 3 byte command
    send_serial(pack("!BH",0x1B, cmd))  # ! == network big endian, H = short int 16 bit

def init_display():
    send_command(0x05)
    time.sleep(DISPLAY_INIT_DELAY) # catch up with display
    blank_display()

def clear_display():
    send_command(0x02)

def write_text(text):
    #print "writing: >>$text<<\n" if ($DEBUG>0);
    send_serial(text)

def blank_display():
    write_text(" " * 40) # clear any blinking etc

def blank_line():
    write_text(" " * 20); # write 20 blanks, careful that you are at pos 0, 0x14 first


def char_blink(b):
#The only way to cause an existing character to start or stop blinking
#is to set up the character blink operator, move the cursor to the
#correct character, and resend the individual character code.
        # 0 = off
        # 1 = on

    if (b==1):
        send_command(0x0D)
    else:
        send_command(0x0E)

def display_brightness(b):
    if (b>0 and b<6):
        b = 0x17<<8 | b
        send_commandEx(b)


def enable_screensaver(b):
    # after 5mins blank or walk
    # 0 = blank
    # 1 = walk

    if (b==1):
        send_command(0x0A)
    else:
        send_command(0x09)

def disable_screensaver():
    send_command(0x0C)

def start_screensaver():
        # start immediately
    send_command(0x0B)

def cursor_to_position(b):
    if (b>=0 and b<=0x27):
        b=0x13<<8 | b
        send_commandEx(b)

def cursor_top_line():
    cursor_to_position(0)
    cursor_to_position(0)

def cursor_bottom_line():
    cursor_to_position(0x14)
    cursor_to_position(0x14)

############################### VFD ###############################

def my_init_display():
    global serial_port
    global ports

    for serial_pos in [top, middle, bottom]:

        ser_current = serial.Serial(serial_pos,9600)  # open serial port

        #print(ser_current.name)         # check which port was really used
        
        my_logger.info(ser_current.name)

        serial_port = ser_current

        if not ser_current in ports:
            ports.append(ser_current)
        else:
            my_logger.debug(ser_current+" in ports list already")

        init_display()
        clear_display()
        disable_screensaver()
        
        blank_display()

        #ser_current.close() 


def get_and_display():
    #
    # get data
    #
    global serial_port 

    not_found=True
    retries=0
    while retries<MAX_RETRY_COUNT and not_found:
        try:
            r = requests.get(WU_API,timeout=3)
            r.raise_for_status()
            not_found=False
        except requests.exceptions.HTTPError as errh:
            my_logger.warning ("Http Error:",errh)
        except requests.exceptions.ConnectionError as errc:
            my_logger.warning ("Error Connecting:",errc)
        except requests.exceptions.Timeout as errt:
            my_logger.warning ("Timeout Error:",errt)
        except requests.exceptions.RequestException as err:
            my_logger.critical ("Oops: Something Else",err)

        if not_found:
            retries += 1
            time.sleep(2)
    # end loop 

    if (r.status_code == 204):
        err="No data from WU"
        my_logger.critical(err)
        my_init_display()
        write_text(err)    
    elif (r.status_code != 200):
        err="API Error: "+str(r.status_code)
        my_logger.critical(err)
        my_init_display()
        write_text(err)    

    else:
        blank_display() # remove Running...

        _json = r.json()

        jj = _json['observations'][0]['imperial']

        temperature = int(jj['temp'])
        wind_speed = jj['windSpeed']
        wind_chill = jj['windChill']
        heat_index = jj['heatIndex']
        humidity   = _json['observations'][0]['humidity']

        feels_like = temperature
        if wind_chill < temperature:
            feels_like = wind_chill

        if heat_index > temperature:
            feels_like = heat_index

        t = (temperature - 32) * 5/9
        fl = (feels_like - 32) * 5/9


        tm = time.localtime()
        current_time = time.strftime("%H:%M", tm)

        #
        # write to VFD
        #

        serial_port = ports[0] # top
        blank_display()
        cursor_top_line()
        write_text("Temperature: "+str(t)+" C")
        cursor_bottom_line()
        write_text("Feels Like : "+str(fl)+" C")

        serial_port = ports[1] # middle
        blank_display()
        cursor_top_line()
        write_text("Wind speed : "+str(wind_speed)+" mph")
        cursor_bottom_line()
        write_text("Humidity   : "+str(humidity)+" %")

        serial_port = ports[2] # bottom
        blank_display()
        # write_text("DNS Queries : "+str(abc))
        cursor_bottom_line()
        write_text("Last Update : "+current_time)

###################################################################
#
# main
#

my_logger.debug('Starting...')
#
#  init
#
my_init_display()       

write_text("Running...")

#
# LOOP HERE
#
sleepy_time=False
while True:
    tm = time.localtime()
    current_hour = int(time.strftime("%H", tm))

    #my_logger.debug(current_hour)
    #my_logger.debug(sleepy_time)

    if (current_hour>=6 and current_hour<23):
        # 6am-10.59pm display else turn off 
        get_and_display()
        sleepy_time=False
    else:
        if not sleepy_time:
            my_logger.info("Sleepy Time")
            my_init_display()
            sleepy_time=True

    time.sleep(DISPLAY_UPDATE_DELAY)


# TBH: we never get to here
# clean up
for p in ports:
    p.close()


# vim: noai:ts=4:sw=4

import serial
import requests

from struct import *
import time

# your WU api key
from weather_underground_api import *

top="/dev/ttyS5"
middle="/dev/ttyS7"
bottom="/dev/ttyS6"
ports = [] # top, middle, bottom
displaydelay=5; # how long before each messages is displayed

DISPLAY_UPDATE_DELAY=300
DISPLAY_INIT_DELAY=1

WU_API="https://api.weather.com/v2/pws/observations/current?stationId="+STATION_ID+"&format=json&units=e&apiKey="+API_KEY

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
        
        serial_port = ser_current
        ports.append(ser_current)

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

    r = requests.get(WU_API)
    if (r.status_code != 200):
        my_init_display
        write_text("API Error: "+r.status_code)    
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

#
#  init
#
my_init_display()       

write_text("Running...")

#
# LOOP HERE
#
while True:
    tm = time.localtime()
    current_hour = time.strftime("%H", tm)

    if (current_hour>=6 or current_hour<=11):
        # 6am-10.59pm display else turn off 
        get_and_display()
    else:    
        my_init_display()
    
    time.sleep(DISPLAY_UPDATE_DELAY)


# TBH: we never get to here
# clean up
for p in ports:
    p.close()


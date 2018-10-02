# main.py -- put your code here!
# The MIT License (MIT)
# Copyright (c) 2018 Stephen Suffian

from network import LoRa
import socket
import utime
import ubinascii
import pycom
import struct
from cayennelpp import CayenneLPP
import machine

from LIS2HH12 import LIS2HH12
from pytrack import Pytrack
from L76GNSS import L76GNSS
import run_sds011

pycom.heartbeat(False)

py = Pytrack()
print('Checking GPS...')
gps = L76GNSS(py,timeout=5)
acc = LIS2HH12()

pycom.rgbled(0xffffff)
coords = gps.coordinates()

lora = LoRa(mode=LoRa.LORAWAN, region=LoRa.US915)

#70b3d5499010e96c
# create an ABP authentication params
dev_addr = struct.unpack(">l", ubinascii.unhexlify('06e84090'))[0]
nwk_swkey = ubinascii.unhexlify('f5305e78929e59dc1329b52a5fbcad6c')
app_swkey = ubinascii.unhexlify('57a1e0fb95e104aee164577a9e8d3d2b')
# join a network using ABP (Activation By Personalization)
lora.join(activation=LoRa.ABP, auth=(dev_addr, nwk_swkey, app_swkey))

# create a LoRa socket
s = socket.socket(socket.AF_LORA, socket.SOCK_RAW)

# set the LoRaWAN data rate
s.setsockopt(socket.SOL_LORA, socket.SO_DR, 4)

# Set the Counter for re-checking GPS
check_gps = utime.time()

while True:
    utime.sleep(2)
    print('Attempt to Send')
    pm25, pm10 = run_sds011.run_sensor()
    print('Air Quality PM2.5: {}, PM10: {}'.format(pm25, pm10))
    # make the socket blocking
    # (waits for the data to be sent and for the 2 receive windows to expire)
    s.setblocking(True)

    # send some data
    c = CayenneLPP()
    c.addAnalogOutput(2,acc.pitch())
    c.addAnalogOutput(25,pm25)
    c.addAnalogOutput(10,pm10)
    # Check if GPS data was found
    if coords[0] is not None:
        coords = gps.coordinates()
        if coords[0] is not None and coords[1] is not None:
            c.addGPS(5,coords[0], coords[1], 0)
    s.send(bytes(c.getBuffer()))
    print('SENT')

    # make the socket non-blocking
    # (because if there's no data received it will block forever...)
    s.setblocking(False)
    # every 10 seconds i want it to blink
    # get any data received (if any...)
    data = s.recv(64)
    print(data)

    print(coords)
    now = utime.time()
    print('It has been {} seconds since last GPS check.'.format(now-check_gps))


    if coords[0]:
        pycom.rgbled(0x0000ff)
        print(' GPS Found {}'.format(coords))
    else:
        pycom.rgbled(0xffffff)
        print(' No GPS Found')
    utime.sleep(1)

    if pm25:
        if pm25 == -1:
            pycom.rgbled(0xff69b4) #pink
        if pm25 < 12:
            pycom.rgbled(0x00ff00) #green
        elif pm25 < 35:
            pycom.rgbled(0xffff00) #yellow
        elif pm25 < 55:
            pycom.rgbled(0xffa500) #orange
        elif pm25 < 150:
            pycom.rgbled(0xff0000) #red
        else:
            pycom.rgbled(0x551a8b) #purple

    utime.sleep(1)
    if now - check_gps > 30:
        print ('GPS')
        if not coords[0]:
            print('Rechecking GPS...')
            machine.reset()
        check_gps = utime.time()

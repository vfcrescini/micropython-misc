
# Copyright (C) 2022 Vino Fernando Crescini <vfcrescini@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

# 2022-07-29 standalone_sensor_esp32.py

# standalone multi weather sensor webserver for ESP32/ESP8266


# import order is from largest to smallest
# this is to ensure that there is enough memory to actually load them on
# somthing like the esp8266

import bme280
import sht30
import webserver
import xtime
import xmachine
import machine
import wifi
import xconfig
import xntptime


# initialise xconfig instance

xc = xconfig.XConfig(path="standalone_sensor.conf")

# initialise xtime instance

xt = xtime.XTime()

# initialise xmachine instance

xm = xmachine.XMachine(bus=xc.get_int("I2C_BUS"), sda=xc.get_int("PIN_I2C_SDA"), scl=xc.get_int("PIN_I2C_SCL"))

# initialise LED

led_pin = None
led_invert = xc.get_bool("LED_FLAG_INVERT")

if xc.get_int("PIN_LED", 10, 0) > 0:
  led_pin = machine.Pin(xc.get_int("PIN_LED"), mode=machine.Pin.OUT, value=(1 if led_invert else 0))

# initialise I2C devices

sdev = [ None, None ]

sdev[0] = bme280.BME280(xm, xt, addr=xc.get_int("SENSOR1_I2C_ADDR", 16))
sdev[0].set(oversampling=0x04)

sdev[1] = sht30.SHT30(xm, xt, addr=xc.get_int("SENSOR2_I2C_ADDR", 16))
sdev[1].set(repeatability=0x02)

# connect to wifi

wifi.connect(verbose=True)

# instantiate and start web server

ws = webserver.Webserver(xt, port=xc.get_int("HTTP_PORT"), timeout=xc.get_int("HTTP_TIMEOUT"))

ws.start()

# init variables

humi = 0.0
temp = 0.0
pres = 0.0

tick_period = xc.get_int("TICK_PERIOD")

interval_probe = xc.get_int("INTERVAL_PROBE") * (1000 / tick_period)
interval_tsync = xc.get_int("INTERVAL_TSYNC") * (1000 / tick_period)

count_probe = [ interval_probe - 1, interval_probe - 2 ]
count_tsync = interval_tsync

ntp_host = xc.get_str("NTP_HOST")
http_path = xc.get_str("HTTP_PATH")

# we don't need this anymore

del xc

# align loop to the nearest clock second

xt.sleep_ms(1000 - (xt.time_ms() % 1000))

# start main loop

while True:

  t_start = xt.time_ms()

  # LED on

  if led_pin != None:
    led_pin.value(0 if led_invert else 1)

  # do sensor probes at the specified interval
  # Use BME280's pressure, and SHT30's humidity and temperature

  if count_probe[0] >= interval_probe:
    count_probe[0] = 0
    _, _, pres = sdev[0].get()
  else:
    count_probe[0] = count_probe[0] + 1

  if count_probe[1] >= interval_probe:
    count_probe[1] = 0
    humi, temp = sdev[1].get()
  else:
    count_probe[1] = count_probe[1] + 1

  # do time sync at the specified interval

  if count_tsync >= interval_tsync:
    count_tsync = 0
    xntptime.update(ntp_host=ntp_host, attempts=1)
  else:
    count_tsync = count_tsync + 1

  # serve any pending webserver requests

  trmap = { http_path: "%16d %7.3f %7.3f %8.3f\r\n" % ((t_start // 1000) + 946684800, humi, temp, pres) }

  ws.serve(reqmap=trmap, now=t_start)

  # LED off

  if led_pin != None:
    led_pin.value(1 if led_invert else 0)

  # sleep until the end of the second

  t_end = xt.time_ms()

  if (t_end - t_start) < tick_period:
    xt.sleep_ms(tick_period - (t_end % tick_period))

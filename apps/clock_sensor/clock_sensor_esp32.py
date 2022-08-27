
# Copyright (C) 2022 Vino Fernando Crescini <vfcrescini@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

# 2021-12-05 clock_sensor_esp32.py

# clock weather sensor webserver for ESP32/ESP8266


# import order is from largest to smallest
# this is to ensure that there is enough memory to actually load them on
# somthing like the esp8266

import bme280
import hd44780
import webserver
import xtime
import xmachine
import wifi
import xconfig
import xntptime
import machine


# initialise stuff

xc = xconfig.XConfig(path="clock_sensor.conf")
xt = xtime.XTime()
xm = xmachine.XMachine(bus=xc.get_int("I2C_BUS"), sda=xc.get_int("PIN_I2C_SDA"), scl=xc.get_int("PIN_I2C_SCL"))

# init display

ddev = None

if xc.get_int("DISPLAY_I2C_ADDR", 16, 0x00) > 0x00:
  ddev = hd44780.HD44780(xm, xt, addr=xc.get_int("DISPLAY_I2C_ADDR", 16))

d4flag = xc.get_bool("DISPLAY_FLAG_4LINES")

# init sensor

sdev = None

if xc.get_int("SENSOR_I2C_ADDR", 16, 0x00) > 0x00:
  sdev = bme280.BME280(xm, xt, addr=xc.get_int("SENSOR_I2C_ADDR", 16))

# init led

led_pin = None
led_invert = xc.get_bool("LED_FLAG_INVERT")

if xc.get_int("PIN_LED", 10, 2) > 0:
  led_pin = machine.Pin(xc.get_int("PIN_LED"), mode=machine.Pin.OUT, value=(1 if led_invert else 0))

# clear display

if ddev != None:
  ddev.clear()

# connect to wifi

wifi.connect(verbose=True)

# instantiate and start web server

ws = webserver.Webserver(xt, port=xc.get_int("HTTP_PORT"), timeout=xc.get_int("HTTP_TIMEOUT"))

ws.start()

# init variables

humi = 0.0
temp = 0.0
pres = 0.0

linebuf_cur = [""] * (4 if d4flag else 2)
linebuf_new = [""] * (4 if d4flag else 2)

tick_period = xc.get_int("TICK_PERIOD")

interval_dsply = xc.get_int("INTERVAL_DSPLY") * (1000 / tick_period) - 1
interval_probe = xc.get_int("INTERVAL_PROBE") * (1000 / tick_period) - 1
interval_tsync = xc.get_int("INTERVAL_TSYNC") * (1000 / tick_period) - 1

count_dsply = interval_dsply - 2
count_probe = interval_probe - 1
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

  if ddev != None:

    if count_dsply >= interval_dsply:
      count_dsply = 0

      # compose strings
  
      lt = xt.localtime(t_start // 1000)
  
      if d4flag:
  
        linebuf_new[0] = "%02d/%02d/%04d  %02d:%02d:%02d" % (lt[2], lt[1], lt[0], lt[3], lt[4], lt[5])
        linebuf_new[1] = "Humidity:    %6.1f%%" % (humi)
        linebuf_new[2] = "Temperature: %6.1fC" % (temp)
        linebuf_new[3] = "Pressure: %7.1fhPa" % (pres)
  
      else:
  
        linebuf_new[0] = "%02d/%02d   %02d:%02d:%02d" % (lt[2], lt[1], lt[3], lt[4], lt[5])
        linebuf_new[1] = "% 5.1fC %6.1fhPa" % (temp, pres)
  
      # update line 1 only if there is a change
  
      if linebuf_cur[0] != linebuf_new[0]:
        linebuf_cur[0] = linebuf_new[0]
        ddev.show(linebuf_cur[0], 1)
  
      # update line 2 only if there is a change
  
      if linebuf_cur[1] != linebuf_new[1]:
        linebuf_cur[1] = linebuf_new[1]
        ddev.show(linebuf_cur[1], 2)
  
      # update line 3 only if there is a change
  
      if d4flag and linebuf_cur[2] != linebuf_new[2]:
        linebuf_cur[2] = linebuf_new[2]
        ddev.show(linebuf_cur[2], 3)
  
      # update line 4 only if there is a change
  
      if d4flag and linebuf_cur[3] != linebuf_new[3]:
        linebuf_cur[3] = linebuf_new[3]
        ddev.show(linebuf_cur[3], 4)

    else:

      count_dsply = count_dsply + 1

  # do sensor probe at the specified interval

  if sdev != None:
    if count_probe >= interval_probe:
      count_probe = 0
  
      humi, temp, pres = sdev.get()
    else:
      count_probe = count_probe + 1

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


# Copyright (C) 2022 Vino Fernando Crescini <vfcrescini@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

# 2021-12-05 clock_sensor_esp32.py

# clock weather sensor webserver for ESP32/ESP8266


# import order is from largest to smallest
# this is to ensure that there is enough memory to actually load them on
# somthing like the esp8266

import bme280
import hd44780
import webclient
import webserver
import xtime
import xmachine
import wifi
import xconfig
import xntptime
import machine
import re


# connect to wifi

wifi.connect(verbose=True)

# initialise stuff

xc = xconfig.XConfig(path="clock_sensor.conf")
xt = xtime.XTime()
xm = xmachine.XMachine(bus=xc.get_int("I2C_BUS"), sda=xc.get_int("I2C_PIN_SDA"), scl=xc.get_int("I2C_PIN_SCL"))

tick_period = xc.get_int("TICK_PERIOD", 10, 1000)

# init display

dsply_dev = None

if xc.get_int("DISPLAY_I2C_ADDR", 16, 0x00) > 0x00:

  dsply_dev = hd44780.HD44780(xm, xt, addr=xc.get_int("DISPLAY_I2C_ADDR", 16))
  dsply_interval = int(xc.get_int("DISPLAY_INTERVAL", 10, 5) * (1000 / tick_period)) - 1
  dsply_count = dsply_interval - 2
  dsply_mode = xc.get_int("DISPLAY_MODE", 10, 0)
  dsply_lbuf_cur = [""] * (4 if dsply_mode > 0 else 2)
  dsply_lbuf_new = [""] * (4 if dsply_mode > 0 else 2)

  dsply_dev.clear()

  print("Display initialised; i2c_addr=0x%0X; mode=%d" % (xc.get_int("DISPLAY_I2C_ADDR", 16), dsply_mode))

# init sensor

snsr1_dev = None

if xc.get_int("SENSOR_I2C_ADDR", 16, 0x00) > 0x00:

  snsr1_dev = bme280.BME280(xm, xt, addr=xc.get_int("SENSOR_I2C_ADDR", 16))
  snsr1_interval = xc.get_int("SENSOR_INTERVAL", 10, 5) * (1000 / tick_period) - 1
  snsr1_count = snsr1_interval - 1

  print("Sensor1 initialised; i2c_addr=0x%0X" % (xc.get_int("SENSOR_I2C_ADDR", 16)))

# init led

led_dev = None

if xc.get_int("LED_PIN", 10, 0) > 0:

  led_dev = machine.Pin(xc.get_int("LED_PIN"), mode=machine.Pin.OUT, value=0)
  led_invert = xc.get_bool("LED_FLAG_INVERT")

  print("LED initialised; pin=%d" % (xc.get_int("LED_PIN", 10)))

# init webserver

websrv = None

if xc.get_int("WEBSRV_PORT", 10, 0) > 0 and len(xc.get_str("WEBSRV_PATH")) > 0:

  websrv = webserver.Webserver(xt, port=xc.get_int("WEBSRV_PORT"), timeout=xc.get_int("WEBSRV_TIMEOUT", 10, 60))
  websrv_path = xc.get_str("WEBSRV_PATH", "/")

  websrv.start()

  print("Webserver initialised; port=%d; path=%s" % (xc.get_int("WEBSRV_PORT", 10), websrv_path))

# init webclient

webclt = None

if len(xc.get_str("REMOTE_HOST", "")) > 0:

  webclt = webclient.HTTPRequest()
  webclt_interval = xc.get_int("REMOTE_INTERVAL", 10, 5) * (1000 / tick_period) - 1
  webclt_count = webclt_interval - 3

  webclt.set(xc.get_str("REMOTE_HOST"), xc.get_str("REMOTE_PATH", "/"))

  print("Webclient initialised; host=%s; path=%s" % (xc.get_str("REMOTE_HOST"), xc.get_str("REMOTE_PATH", "/")))

# init NTP

ntp_host = xc.get_str("NTP_HOST", "")

if len(ntp_host) > 0:

  ntp_interval = xc.get_int("NTP_INTERVAL", 10, 300) * (1000 / tick_period) - 1
  ntp_count = ntp_interval

  print("NTP sync initialised; host=%s" % (ntp_host))

print("Starting...")

# init global variables

humi = [ 0.0 ] * 2
temp = [ 0.0 ] * 2
pres = [ 0.0 ] * 2

# we don't need this anymore

del xc

# align loop to the nearest clock second

xt.sleep_ms(1000 - (xt.time_ms() % 1000))

# start main loop

while True:

  t_start = xt.time_ms()

  # LED on

  if led_dev != None:
    led_dev.value(0 if led_invert else 1)

  if dsply_dev != None:

    if dsply_count >= dsply_interval:
      dsply_count = 0

      # compose strings
  
      lt = xt.localtime(t_start // 1000)

      if dsply_mode == 1:

        dsply_lbuf_new[0] = "%02d/%02d/%04d  %02d:%02d:%02d" % (lt[2], lt[1], lt[0], lt[3], lt[4], lt[5])
        dsply_lbuf_new[1] = "Humidity:     %5.1f%%" % (humi[0])
        dsply_lbuf_new[2] = "Temperature: %6.1fC" % (temp[0])
        dsply_lbuf_new[3] = "Pressure:  %6.1fhPa" % (pres[0])

      if dsply_mode == 2:

        dsply_lbuf_new[0] = "%02d/%02d/%04d  %02d:%02d:%02d" % (lt[2], lt[1], lt[0], lt[3], lt[4], lt[5])
        dsply_lbuf_new[1] = " %5.1f%%     %5.1f%%" % (humi[1], humi[0])
        dsply_lbuf_new[2] = "%6.1fC    %6.1fC" % (temp[1], temp[0])
        dsply_lbuf_new[3] = "%6.1fhPa  %6.1fhPa" % (pres[1], pres[0])

      else:

        dsply_lbuf_new[0] = "%02d/%02d   %02d:%02d:%02d" % (lt[2], lt[1], lt[3], lt[4], lt[5])
        dsply_lbuf_new[1] = "% 5.1fC %6.1fhPa" % (temp[0], pres[0])
  
      # update line 1 only if there is a change
  
      if dsply_lbuf_cur[0] != dsply_lbuf_new[0]:
        dsply_lbuf_cur[0] = dsply_lbuf_new[0]
        dsply_dev.show(dsply_lbuf_cur[0], 1)
  
      # update line 2 only if there is a change
  
      if dsply_lbuf_cur[1] != dsply_lbuf_new[1]:
        dsply_lbuf_cur[1] = dsply_lbuf_new[1]
        dsply_dev.show(dsply_lbuf_cur[1], 2)
  
      # update line 3 only if there is a change
  
      if dsply_mode > 0 and dsply_lbuf_cur[2] != dsply_lbuf_new[2]:
        dsply_lbuf_cur[2] = dsply_lbuf_new[2]
        dsply_dev.show(dsply_lbuf_cur[2], 3)
  
      # update line 4 only if there is a change
  
      if dsply_mode > 0 and dsply_lbuf_cur[3] != dsply_lbuf_new[3]:
        dsply_lbuf_cur[3] = dsply_lbuf_new[3]
        dsply_dev.show(dsply_lbuf_cur[3], 4)

    else:

      dsply_count = dsply_count + 1

  # do sensor probe at the specified interval

  if snsr1_dev != None:
    if snsr1_count >= snsr1_interval:
      snsr1_count = 0
  
      humi[0], temp[0], pres[0] = snsr1_dev.get()
    else:
      snsr1_count = snsr1_count + 1

  # do web requests at the specified interval

  if webclt != None:
    if webclt_count >= webclt_interval:

      rsp = webclt.request()

      if rsp[0] == 0 and rsp[1] == 10:
        webclt_count = 0

        rsp = webclt.get_response()

        if rsp[0][0] == 200:

          mo = re.match("^\s*([0-9]+)\s+([0-9]+\.[0-9]+)\s+([0-9]+\.[0-9]+)\s+([0-9]+\.[0-9]+)\s*$", rsp[2])

          if mo != None:
            humi[1] = float(mo.group(2))
            temp[1] = float(mo.group(3))
            pres[1] = float(mo.group(4))

        webclt.reset()
      elif rsp[0] != 0:
        webclt_count = 0
        webclt.reset()
    else:
      webclt_count = webclt_count + 1

  # do time sync at the specified interval

  if len(ntp_host) > 0:
    if ntp_count >= ntp_interval:
      ntp_count = 0
      xntptime.update(ntp_host, 1)
    else:
      ntp_count = ntp_count + 1

  # serve any pending webserver requests

  if websrv != None:
    trmap = { websrv_path: "%16d %7.3f %7.3f %8.3f\r\n" % ((t_start // 1000) + 946684800, humi[0], temp[0], pres[0]) }
    websrv.serve(reqmap=trmap, now=t_start)

  # LED off

  if led_dev != None:
    led_dev.value(1 if led_invert else 0)

  # sleep until the end of the second

  t_end = xt.time_ms()

  if (t_end - t_start) < tick_period:
    xt.sleep_ms(tick_period - (t_end % tick_period))

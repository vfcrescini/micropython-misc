
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


# connect to wifi

wifi.connect(verbose=True)

# initialise stuff

xc = xconfig.XConfig(path="standalone_sensor.conf")
xt = xtime.XTime()
xm = xmachine.XMachine(bus=xc.get_int("I2C_BUS"), sda=xc.get_int("I2C_PIN_SDA"), scl=xc.get_int("I2C_PIN_SCL"))

tick_period = xc.get_int("TICK_PERIOD")

# initialise sensors

snsr1_dev = None

if xc.get_int("SENSOR1_I2C_ADDR", 16, 0x00) > 0x00:

  snsr1_dev = bme280.BME280(xm, xt, addr=xc.get_int("SENSOR1_I2C_ADDR", 16))
  snsr1_interval = xc.get_int("SENSOR1_INTERVAL") * (1000 / tick_period) - 1
  snsr1_count = snsr1_interval - 2

  snsr1_dev.set(oversampling=0x04)

  print("Sensor1 initialised; i2c_addr=0x%0X" % (xc.get_int("SENSOR1_I2C_ADDR", 16)))

snsr2_dev = None

if xc.get_int("SENSOR2_I2C_ADDR", 16, 0x00) > 0x00:

  snsr2_dev = sht30.SHT30(xm, xt, addr=xc.get_int("SENSOR2_I2C_ADDR", 16))
  snsr2_interval = xc.get_int("SENSOR2_INTERVAL") * (1000 / tick_period) - 1
  snsr2_count = snsr2_interval - 1

  snsr2_dev.set(repeatability=0x02)

  print("Sensor2 initialised; i2c_addr=0x%0X" % (xc.get_int("SENSOR2_I2C_ADDR", 16)))

# initialise led

led_dev = None

if xc.get_int("LED_PIN", 10, 0) > 0:

  led_dev = machine.Pin(xc.get_int("LED_PIN"), mode=machine.Pin.OUT, value=0)
  led_invert = xc.get_bool("LED_FLAG_INVERT")

  print("LED initialised; pin=%d" % (xc.get_int("LED_PIN", 10)))

# initialise webserver

websrv = None

if xc.get_int("WEBSRV_PORT", 10, 0) > 0 and len(xc.get_str("WEBSRV_PATH")) > 0:

  websrv = webserver.Webserver(xt, port=xc.get_int("WEBSRV_PORT"), timeout=xc.get_int("WEBSRV_TIMEOUT", 10, 60))
  websrv_path = xc.get_str("WEBSRV_PATH", "/")

  websrv.start()

  print("Webserver initialised; port=%d; path=%s" % (xc.get_int("WEBSRV_PORT", 10), websrv_path))

# init NTP

ntp_host = xc.get_str("NTP_HOST", "")

if len(ntp_host) > 0:

  ntp_interval = xc.get_int("NTP_INTERVAL") * (1000 / tick_period) - 1
  ntp_count = ntp_interval

  print("NTP sync initialised; host=%s" % (ntp_host))

print("Starting...")

# init variables

humi = 0.0
temp = 0.0
pres = 0.0

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

  # do sensor probes at the specified interval
  # Use BME280's pressure, and SHT30's humidity and temperature

  if snsr1_dev != None:
    if snsr1_count >= snsr1_interval:
      snsr1_count = 0

      _, _, pres = snsr1_dev.get()
    else:
      snsr1_count = snsr1_count + 1

  if snsr2_dev != None:
    if snsr2_count >= snsr2_interval:
      snsr2_count = 0

      humi, temp = snsr2_dev.get()
    else:
      snsr2_count = snsr2_count + 1

  # do time sync at the specified interval

  if len(ntp_host) > 0:
    if ntp_count >= ntp_interval:
      ntp_count = 0
      xntptime.update(ntp_host, 1)
    else:
      ntp_count = ntp_count + 1

  # serve any pending webserver requests

  if websrv != None:
    trmap = { websrv_path: "%16d %7.3f %7.3f %8.3f\r\n" % ((t_start // 1000) + 946684800, humi, temp, pres) }
    websrv.serve(reqmap=trmap, now=t_start)

  # LED off

  if led_dev != None:
    led_dev.value(1 if led_invert else 0)

  # sleep until the end of the second

  t_end = xt.time_ms()

  if (t_end - t_start) < tick_period:
    xt.sleep_ms(tick_period - (t_end % tick_period))

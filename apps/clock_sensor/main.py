
# Copyright (C) 2022 Vino Fernando Crescini <vfcrescini@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

# 2022-09-12 main.py

# clock weather sensor webserver for ESP32/ESP8266/RP2040

import clock_sensor as cs
import xtime
import xmachine
import xconfig
import wifi


# connect to wifi

wifi.connect(verbose=True)

# initialise stuff

xt = xtime.XTime()
xc = xconfig.XConfig(path="clock_sensor.conf")
xm = xmachine.XMachine(bus=xc.get_int("I2C_BUS"), sda=xc.get_int("I2C_PIN_SDA"), scl=xc.get_int("I2C_PIN_SCL"))

tick_period = xc.get_int("TICK_PERIOD", 10, 1000)

# init devices

sensor1 = cs.ModDevice(xm, xt, xc, tick_period, "SENSOR1")
sensor2 = cs.ModDevice(xm, xt, xc, tick_period, "SENSOR2")
display = cs.ModDevice(xm, xt, xc, tick_period, "DISPLAY")

# init webserver

websrv = cs.WS(xt, xc, "WEBSRV")

# init ntp sync

ntp = cs.NTP(xc, tick_period, "NTP")

# init led

led = cs.LED(xc, "LED")

# we don't need this anymore

del xc

# set listeners

sensor1.add_listener(lambda x, y: display.set(x, y, None))
sensor1.add_listener(lambda x, y: websrv.set(x, y, None))

sensor2.add_listener(lambda x, y: display.set(x, None, y))
sensor2.add_listener(lambda x, y: websrv.set(x, None, y))

# start main loop

while True:

  t_start = xt.tp_now()
  t_now = xt.time_ms()

  # LED on

  led.set(True)

  # run periodic stuff

  display.tick(t_now)

  sensor1.tick(t_now)
  sensor2.tick(t_now)

  # serve any pending webserver requests

  websrv.serve(t_now)

  # sync time

  ntp.tick(t_now)

  # LED off

  led.set(False)

  # sleep until the end of the tick period

  t_diff = xt.tp_diff(xt.tp_now(), t_start)

  if t_diff < tick_period:
    xt.sleep_ms(tick_period - t_diff)

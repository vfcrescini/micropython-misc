
# Copyright (C) 2022 Vino Fernando Crescini <vfcrescini@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

# 2021-12-05 clock_sensor_esp32.py

# clock weather sensor webserver for ESP32/ESP8266


import xtime
import xmachine
import xconfig
import wifi
import re


class Periodic(object):

  _cnt = 0

  def __init__(self, xc, tick_period, xcprefix):

    Periodic._cnt = Periodic._cnt + 1

    self._tick_max = 0
    self._tick_cnt = 0

    # interval = 0 means _fire() at every tick
    # interval > 0 means _fire() every interval seconds

    interval = xc.get_int(xcprefix + "_INTERVAL", 10, 1)

    if interval > 0:

      self._tick_max = interval * (1000 / tick_period) - 1
      self._tick_cnt = self._tick_max - Periodic._cnt


  def _fire(self, param):

    return True


  def tick(self, param):

    if self._tick_cnt >= self._tick_max:

      if self._fire(param):
        self._tick_cnt = 0

    else:

      self._tick_cnt = self._tick_cnt + 1


class Sensor(Periodic):

  def __init__(self, xc, tick_period, xcprefix):

    Periodic.__init__(self, xc, tick_period, xcprefix)


  def _fire(self, param):

    rv = self._get()

    if rv == None:
      return False

    param[0] = rv[0] if len(rv) > 0 else 0.0
    param[1] = rv[1] if len(rv) > 1 else 0.0
    param[2] = rv[2] if len(rv) > 2 else 0.0

    return True


class I2CDevice(object):

  def __init__(self, xm, xt, xc, mname, xcprefix):

    self._i2cdev = None

    addr = xc.get_int(xcprefix + "_I2C_ADDR", 16, 0x00)

    if addr > 0x00:

      m = __import__(mname)

      # assume module's main class name is uppercase equivalent of module name

      self._i2cdev = getattr(m, m.__name__.upper())(xm, xt, addr)


class I2CDisplay(Periodic, I2CDevice):

  def __init__(self, xm, xt, xc, tick_period, mname, xcprefix):

    I2CDevice.__init__(self, xm, xt, xc, mname, xcprefix)
    Periodic.__init__(self, xc, tick_period, xcprefix)

    if self._i2cdev != None:

      self._xt = xt

      tmp = xc.get_str(xcprefix + "_TEMPLATE", "").split(":")

      self._buffer = [""] * len(tmp)
      self._template = list(map(lambda x: x.replace("%NBSP%", " ",).replace("%COLON%", ":"), tmp))

      self._i2cdev.clear()


  # refreshes buffer; returns an array of bools representing lines in buffer
  # that were actually modified

  def _refresh(self, now, s1, s2):

    lt = self._xt.localtime(now // 1000)
    chg = [ False ] * len(self._buffer)

    for i, line in enumerate(self._template):

      tmp = line
      tmp = tmp.replace("%SDATE%", "%02d/%02d" % (lt[2], lt[1]))
      tmp = tmp.replace("%LDATE%", "%02d/%02d/%04d" % (lt[2], lt[1], lt[0]))
      tmp = tmp.replace("%TIME%", "%02d:%02d:%02d" % (lt[3], lt[4], lt[5]))
      tmp = tmp.replace("%S1_HUMI%", "%5.1f%%" % (s1[0]))
      tmp = tmp.replace("%S1_TEMP%", "%5.1fC" % (s1[1]))
      tmp = tmp.replace("%S1_PRES%", "%6.1fhPa" % (s1[2]))
      tmp = tmp.replace("%S2_HUMI%", "%5.1f%%" % (s2[0]))
      tmp = tmp.replace("%S2_TEMP%", "%5.1fC" % (s2[1]))
      tmp = tmp.replace("%S2_PRES%", "%6.1fhPa" % (s2[2]))

      if self._buffer[i] != tmp:
        self._buffer[i] = tmp
        chg[i] = True

    return chg


  # param is (time, [ [ h1, t1, p1 ], [ h2, t2, p2 ] ])

  def _fire(self, param):

    if self._i2cdev == None:
      return False

    # send to the display only lines that acutally changed

    for i, _ in filter(lambda x: x[1], enumerate(self._refresh(param[0], param[1][0], param[1][1]))):
      self._i2cdev.show(self._buffer[i], i + 1)

    return True


  def set(self):
    pass


class I2CSensor(Sensor):

  def __init__(self, xm, xt, xc, tick_period, mname, xcprefix):

    Sensor.__init__(self, xc, tick_period, xcprefix)
    I2CDevice.__init__(self, xm, xt, xc, mname, xcprefix)


  def _get(self):

    if self._i2cdev == None:
      return None

    return self._i2cdev.get()


  def set(self):
    pass


class RemoteSensor(Sensor):

  _req_ptn = re.compile("^\s*([0-9]+)\s+([0-9]+\.[0-9]+)\s+([0-9]+\.[0-9]+)\s+([0-9]+\.[0-9]+)\s*$")

  def __init__(self, xt, xc, tick_period, xcprefix):

    Sensor.__init__(self, xc, tick_period, xcprefix)

    self._webclt = None

    host = xc.get_str(xcprefix + "_HOST", "")
    port = xc.get_int(xcprefix + "_PORT", 10, 0)
    path = xc.get_str(xcprefix + "_PATH", "/")

    if len(host) > 0 and port > 0 and port < 0xffff and len(path) > 0:

      m = __import__("webclient")

      self._webclt = m.HTTPRequest()
      self._webclt.set(host, path, port)


  def _get(self):

    if self._webclt == None:
      return None

    rv = self._webclt.request()

    # error

    if rv[0] != 0:
      self._webclt.reset()
      return 0.0, 0.0, 0.0

    # success, but not done yet

    if rv[1] != 10:
      return None

    # success and done; get response

    rv = self._webclt.get_response()
    self._webclt.reset()

    # anything other than 200 OK is an error

    if rv[0][0] != 200:
      return 0.0, 0.0, 0.0

    # parse result

    rv = RemoteSensor._req_ptn.match(rv[2])

    # invalid result?

    if rv == None:
      return 0.0, 0.0, 0.0

    return float(rv.group(2)), float(rv.group(3)), float(rv.group(4))


  def set(self):
    pass
  

class ModDevice(object):

  def __init__(self, xm, xt, xc, tick_period, xcprefix):

    self._device = None
    module = xc.get_str(xcprefix + "_MODULE", "").lower()

    if module == "http":
      self._device = RemoteSensor(xm, xc, tick_period, xcprefix)
    elif module in [ "bme280", "sht30" ]:
      self._device = I2CSensor(xm, xt, xc, tick_period, module, xcprefix)
    elif module in [ "hd44780" ]:
      self._device = I2CDisplay(xm, xt, xc, tick_period, module, xcprefix)


  def tick(self, param):

    if self._device != None:
      self._device.tick(param)


  def set(self, *args, **kwargs):
  
    if self._device != None:
      self._device.set(*args, **kwargs)


class NTP(Periodic):

  def __init__(self, xc, tick_period, xcprefix):

    self._xmod = None
    self._host = xc.get_str(xcprefix + "_HOST", "")

    if len(self._host) > 0:
      self._xmod = __import__("xntptime")

    Periodic.__init__(self, xc, tick_period, xcprefix)


  def _fire(self, param):

    if self._xmod == None:
      return False

    self._xmod.update(self._host, 1)

    return True


class LED(object):

  def __init__(self, xc, xcprefix):

    self._dev = None
    self._inv = False

    pin = xc.get_str(xcprefix + "_PIN", "")

    if len(pin) > 0:

      try:
        pin = int(pin)
      except:
        pass

      m = __import__("machine")
      self._dev = m.Pin(pin, mode=m.Pin.OUT)
      self._inv = xc.get_bool(xcprefix + "_INVERT", False)

      self._dev.value(1 if self._inv else 0)


  def set(self, state):

    # i  s  i xor s
    # 0  0  0
    # 0  1  1
    # 1  0  1
    # 1  1  0

    if self._dev != 0:
      self._dev.value(self._inv ^ state)


class WS():

  def __init__(self, xc, xcprefix):

    self._websrv = None
    self._vmap = None
    self._path = xc.get_str(xcprefix + "_PATH", "/")
    self._template = xc.get_str(xcprefix + "_TEMPLATE", "")

    port = xc.get_int(xcprefix + "_PORT", 10, 0)
    to = xc.get_int(xcprefix + "_TIMEOUT", 10, 60)

    if port > 0 and port < 0xffff and len(self._path) > 0:

      # init vmap

      self._vmap = [
        [0, "%TS%", "%16d", False],
        [0.0, "%S1_HUMI%", "%7.3f", False],
        [0.0, "%S1_TEMP%", "%7.3f", False],
        [0.0, "%S1_PRES%", "%8.3f", False],
        [0.0, "%S2_HUMI%", "%7.3f", False],
        [0.0, "%S2_TEMP%", "%7.3f", False],
        [0.0, "%S2_PRES%", "%8.3f", False]
      ]

      for i in self._vmap:
        i[3] = self._template.find(i[1]) >= 0

      # init ws

      m = __import__("webserver")
      self._websrv = m.Webserver(xt, port=port, timeout=to)

      # start

      self.set()
      self._websrv.start()


  def set(self, now=None, htp=None):

    if self._websrv == None:
      return

    # update vmap

    if now != None:
      self._vmap[0][0] = (now // 1000) + xtime.EPOCH_OFFSET

    if htp != None:
      for i in range(0,3):
        self._vmap[i + 1][0] = htp[0][i]
        self._vmap[i + 4][0] = htp[1][i]

    # generate content string

    content = self._template

    for i in filter(lambda x: x[3], self._vmap):
      content = content.replace(i[1], i[2] % (i[0],))

    # set new reqmap

    self._websrv.set( { self._path: content + "\r\n" } )


  def serve(self, now):

    if self._websrv == None:
      return

    self._websrv.serve(now)


# connect to wifi

wifi.connect(verbose=True)

# initialise stuff

xc = xconfig.XConfig(path="clock_sensor.conf")
xt = xtime.XTime()
xm = xmachine.XMachine(bus=xc.get_int("I2C_BUS"), sda=xc.get_int("I2C_PIN_SDA"), scl=xc.get_int("I2C_PIN_SCL"))

tick_period = xc.get_int("TICK_PERIOD", 10, 1000)

# init devices

sensor1 = ModDevice(xm, xt, xc, tick_period, "SENSOR1")
sensor2 = ModDevice(xm, xt, xc, tick_period, "SENSOR2")
display = ModDevice(xm, xt, xc, tick_period, "DISPLAY")

# init webserver

websrv = WS(xc, "WEBSRV")

# init ntp sync

ntp = NTP(xc, tick_period, "NTP")

# init led

led = LED(xc, "LED")

# we don't need this anymore

del xc

# init global variables

htp = [ [ 0.0 ] * 3 ] + [ [ 0.0 ] * 3 ]

# start main loop

while True:

  t_start = xt.tp_now()
  t_now = xt.time_ms()

  # LED on

  led.set(True)

  # run periodic stuff

  display.tick((t_now, htp))

  sensor1.tick(htp[0])
  sensor2.tick(htp[1])

  # serve any pending webserver requests

  websrv.set(t_now, htp)
  websrv.serve(t_now)

  # sync time

  ntp.tick(None)

  # LED off

  led.set(False)

  # sleep until the end of the tick period

  t_diff = xt.tp_diff(xt.tp_now(), t_start)

  if t_diff < tick_period:
    xt.sleep_ms(tick_period - t_diff)

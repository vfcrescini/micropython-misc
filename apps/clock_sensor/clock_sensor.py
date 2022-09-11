
# Copyright (C) 2022 Vino Fernando Crescini <vfcrescini@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

# 2021-12-05 clock_sensor.py

# clock weather sensor webserver for ESP32/ESP8266/RP2040


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


  def _fire(self, now):

    return True


  def tick(self, now):

    if self._tick_cnt >= self._tick_max:

      if self._fire(now):
        self._tick_cnt = 0

    else:

      self._tick_cnt = self._tick_cnt + 1


class Sensor(Periodic):

  def __init__(self, xc, tick_period, xcprefix):

    Periodic.__init__(self, xc, tick_period, xcprefix)

    self._listeners = set()

  def _fire(self, now):

    rv = self._get()

    if rv == None:
      return False

    for listener in self._listeners:
      listener(now, list(rv) + [ 0.0 ] * (3 - len(rv)))

    return True


  # fn(now, htp)

  def add_listener(self, fn):

    self._listeners.add(fn)


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
    
    self._xt = xt
    self._templates = None
    self._vmap = None
    self._uset = None

    if self._i2cdev != None:

      # init line templates

      tmp = xc.get_str(xcprefix + "_TEMPLATE", "").split(":")
      self._templates = list(map(lambda x: x.replace("%NBSP%", " ",).replace("%COLON%", ":"), tmp))

      # init vmap

      self._vmap = [
        [(2000, 1), "%SDATE%", "%02d/%02d", set()],
        [(1, 1, 2000), "%LDATE%", "%02d/%02d/%04d", set()],
        [(0, 0, 0), "%TIME%", "%02d:%02d:%02d", set()],
        [(0.0,), "%S1_HUMI%", "%5.1f%%", set()],
        [(0.0,), "%S1_TEMP%", "%5.1fC", set()],
        [(0.0,), "%S1_PRES%", "%6.1fhPa", set()],
        [(0.0,), "%S2_HUMI%", "%5.1f%%", set()],
        [(0.0,), "%S2_TEMP%", "%5.1fC", set()],
        [(0.0,), "%S2_PRES%", "%6.1fhPa", set()]
      ]

      for i, template in enumerate(self._templates):
        for vm in self._vmap:
          if template.find(vm[1]) >= 0:
            vm[3].add(i)

      # init update set with all lines to force initial update

      self._uset = { i for i in range(0, len(self._templates)) }

      # send a clear command to display

      self._i2cdev.clear()


  def _fire(self, now):

    if self._i2cdev == None:
      return False

    # update time

    self.set(now, None, None)

    # go through each line that needs to be updated

    for i in self._uset:

      line = self._templates[i]

      # go through vmap items that are required by this line
      # then perform string replacement

      for vm in filter(lambda x: i in x[3], self._vmap):
        line = line.replace(vm[1], vm[2] % vm[0])

      # send to display

      self._i2cdev.show(line, i + 1)

    # clear update set

    self._uset.clear()

    return True


  def set(self, now, htp1, htp2):

    # update time variables in vmap 

    if now != None:
      lt = self._xt.localtime(now // 1000)
      if self._vmap[0][0] != (lt[2], lt[1]):
        self._vmap[0][0] = (lt[2], lt[1])
        self._uset.update(self._vmap[0][3])
      
      if self._vmap[1][0] != (lt[2], lt[1], lt[0]):
        self._vmap[1][0] = (lt[2], lt[1], lt[0])
        self._uset.update(self._vmap[1][3])
      
      if self._vmap[2][0] != (lt[3], lt[4], lt[5]):
        self._vmap[2][0] = (lt[3], lt[4], lt[5])
        self._uset.update(self._vmap[2][3])

    # update sensor variables in vmap 

    for i in range(0, 3):
      if htp1 != None:
        if self._vmap[i + 3][0] != (htp1[i],):
          self._vmap[i + 3][0] = (htp1[i],)
          self._uset.update(self._vmap[i + 3][3])
      if htp2 != None:
        if self._vmap[i + 6][0] != (htp2[i],):
          self._vmap[i + 6][0] = (htp2[i],)
          self._uset.update(self._vmap[i + 6][3])


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


  def tick(self, now):

    if self._device != None:
      self._device.tick(now)


  def set(self, *args, **kwargs):

    if self._device != None:
      self._device.set(*args, **kwargs)


  def add_listener(self, fn):

    if self._device != None and isinstance(self._device, Sensor):
      self._device.add_listener(fn)


class NTP(Periodic):

  def __init__(self, xc, tick_period, xcprefix):

    self._xmod = None
    self._host = xc.get_str(xcprefix + "_HOST", "")

    if len(self._host) > 0:
      self._xmod = __import__("xntptime")

    Periodic.__init__(self, xc, tick_period, xcprefix)


  def _fire(self, now):

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

  def __init__(self, xt, xc, xcprefix):

    self._websrv = None
    self._vmap = None
    self._path = xc.get_str(xcprefix + "_PATH", "/")
    self._template = xc.get_str(xcprefix + "_TEMPLATE", "")

    port = xc.get_int(xcprefix + "_PORT", 10, 0)
    tout = xc.get_int(xcprefix + "_TIMEOUT", 10, 60)

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

      for vm in self._vmap:
        vm[3] = self._template.find(vm[1]) >= 0

      # init ws

      m = __import__("webserver")
      self._websrv = m.Webserver(xt, port=port, timeout=tout)

      # start

      self.set(None, None, None)
      self._websrv.start()


  def set(self, now, htp1, htp2):

    if self._websrv == None:
      return

    # update vmap

    if now != None:
      self._vmap[0][0] = (now // 1000) + xtime.EPOCH_OFFSET

    for i in range(0, 3):
      if htp1 != None:
        self._vmap[i + 1][0] = htp1[i]
      if htp2 !=  None:
       self._vmap[i + 4][0] = htp2[i]

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

websrv = WS(xt, xc, "WEBSRV")

# init ntp sync

ntp = NTP(xc, tick_period, "NTP")

# init led

led = LED(xc, "LED")

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

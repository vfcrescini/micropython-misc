
# Copyright (C) 2022 Vino Fernando Crescini <vfcrescini@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

# 2021-11-18 blink_primes.py

# Flash the first 100 prime numbers through the RPi Pico's on-board LED


import machine

PRIMES = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79, 83, 89, 97]

class Blinker():

  def __init__(self, freq, pin):

    self._i1 = 0
    self._i2 = 0
    self._buffer = []

    self._set()

    self._pin = machine.Pin(pin, machine.Pin.OUT)
    self._timer = machine.Timer(freq = freq, mode = machine.Timer.PERIODIC, callback = lambda a: Blinker.on_tick(self))


  def _next(self):

    out = self._buffer[self._i2]

    self._i2 = self._i2 + 1

    if self._i2 >= len(self._buffer):

      self._i1 = self._i1 + 1
      self._i2 = 0
 
      if self._i1 >= len(PRIMES):
        self._i1 = 0
        self._i2 = 0

      self._set()

    return out


  def _set(self):

    self._buffer = [False] + (([False] + [True]) * PRIMES[self._i1]) + [False, False]


  def _on_tick(self):

    self._pin.value(1 if self._next() else 0)


  def on_tick(blinker):

    blinker._on_tick()

  on_tick = staticmethod(on_tick)


# main

timer = Blinker(2, 25)

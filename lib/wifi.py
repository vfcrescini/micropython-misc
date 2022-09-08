#!/usr/bin/python3

# Copyright (C) 2022 Vino Fernando Crescini <vfcrescini@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

# 2021-11-18 wifi.py

# wifi helper

import network
import time

import xconfig


# read in wifi credentials
#   path: path to a file containing:
#     essid = <the ESSID of the wifi network to connect to>
#     passwd = <the wifi password>

def _get_cred(path, verbose):

  xc = xconfig.XConfig(path)

  if not xc.load():

    if verbose:
      print("[wifi] unable load %s" % (path))

    return (None, None)

  return xc.get_str("essid", default=None), xc.get_str("passwd", default=None)


# disable ap interface

def _set_ap_off(verbose):

  try:
    network.WLAN(network.AP_IF).active(False)
  except:
    if verbose:
      print("[wifi] failed to disable AP interface")

  if verbose:
    print("[wifi] AP interface disabled")


# connect to WIFI

def connect(path="wifi.conf", verbose=False, disable_ap=True):

  if disable_ap:
    _set_ap_off(verbose)

  net = network.WLAN(network.STA_IF)
  essid, passwd = _get_cred(path, verbose)

  if essid == None or passwd == None:

    if verbose:
      print("[wifi] missing essid or passwd configuration")

    return False

  net.active(False)
  time.sleep(1)
  net.active(True)

  # dump wifi scan

  found = False

  for sessid in map(lambda x: str(x[0], "utf-8"),  net.scan()):

    if verbose:
      print("[wifi] found ap: %s" % (sessid))

    if sessid == essid:
      found = True

  # did we find the one we want?

  if not found:
    if verbose:
      print("[wifi] unable to find %s" % (essid))
    return False

  # connect

  if verbose:
    print("[wifi] connecting to %s..." %  (essid))

  net.connect(essid, passwd)

  for i in range(1, 30):

    if net.isconnected():

      if verbose:
        print("[wifi] connected")

      params = net.ifconfig()

      if verbose:
        print("[wifi] ip:      %s" % params[0])
        print("[wifi] subnet:  %s" % params[1])
        print("[wifi] gateway: %s" % params[2])
        print("[wifi] dns:     %s" % params[3])

      return True

    time.sleep(1)

  if verbose:
    print("[wifi] connect failed")

  return False

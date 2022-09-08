#!/usr/bin/python3

# Copyright (C) 2022 Vino Fernando Crescini <vfcrescini@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

# 2022-01-14 xconfig.py

# very simple name-value configuration parser


class XConfig:

  # path: path to config file

  def __init__(self, path="config.conf"):

    self._path = path
    self._config = None


  # parses self._path, calls fn(name, value, param) for each parsed n-v pair.
  # stops at EOF, or when fn() returns False

  def _parse(self, fn, param):

    f = None

    try:
      f = open(self._path, "r")
    except Exception as e:
      return False

    for line in f:

      line = line.split("#", 1)[0].strip()

      if len(line) == 0:
        continue

      name, value = map(lambda x: x.strip(), line.split('=', 1))

      if len(name) == 0:
        continue

      if not fn(name, value, param):
        break

    f.close()

    return True


  def _get(self, name):

    # param: name, [result]

    def _fn_find(name, value, param):
      if name != param[0]:
        return True
      param[1][0] = value
      return False

    # we have a loaded dict

    if self._config != None:

      if name not in self._config:
        return None

      return self._config[name]

    # need to parse

    res = [ None ]
    self._parse(_fn_find, (name, res))

    return res[0]


  # parses given config file
  #   preload: if given, a dict that contains the initial config params
  #   returns: True on success, False otherwise

  def load(self, preload=None):

    def _fn_store(name, value, param):
      param[name] = value
      return True

    if self._config == None:
      self._config = {}

    if preload != None and isinstance(preload, dict):
      self._config.update(preload)

    return self._parse(_fn_store, self._config)


  # attempt to retrieve a string config param
  #   name: the name of the config param
  #   default: the string to return if param is not in dict

  def get_str(self, name, default=""):

    value = self._get(name)

    if value == None:
      return default

    return str(value)


  # attempt to retrieve an int config param as an int of the given base
  #   name: the name of the config param
  #   base: base of the int (e.g. 10 for dec, 16 for hex)
  #   default: the int to return if param is not in dict, or is not an int

  def get_int(self, name, base=10, default=0):

    value = default

    try:
      value = int(self._get(name), base)
    except:
      pass

    return value


  # attempt to retrieve a boolean config param
  #   name: the name of the config param
  #   default: the boolean to return if param is not in dict, or is not a bool

  def get_bool(self, name, default=False):

    value = default

    try:
      value = self._get(name).lower() in ["true", "yes", "y"]
    except:
      pass

    return value

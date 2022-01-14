#!/usr/bin/python3

# Copyright (C) 2022 Vino Fernando Crescini <vfcrescini@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

# 2021-11-21 webserver_test.py


import os
import sys
import getopt

sys.path.append(os.path.join("..", "lib"))

import xtime
import webserver


if __name__ == "__main__":

  opts = None
  args = None

  port = 8080
  interval = 1000
  reqmap = {}

  # parse options

  try:
    opts, args = getopt.getopt(sys.argv[1:], "hp:i:m:", ["help", "port=", "interval=", "map="])
  except Exception as e:
    sys.stderr.write("Failed to parse arguments: %s\n" % (e))
    sys.exit(1)

  for o, a in opts:
    if o == "-h" or o == "--help":
      sys.stdout.write("Usage: %s [-h] [-p <port>] [-i <interval>] [-m <path1>=<text1> [-m <path2>=<text2>]]\n" % (sys.argv[0]))
      sys.exit(0)
    elif o == "-p" or o == "--port":
      try:
        port = int(a)
      except Exception as e:
        sys.stderr.write("Invalid port. Valid range 1 to 65535\n")
        sys.exit(1)
      if port < 1 or port > 65535:
        sys.stderr.write("Invalid port. Valid range 1 to 65535\n")
        sys.exit(2)
    elif o == "-i" or o == "--interval":
      try:
        interval = int(a)
      except Exception as e:
        sys.stderr.write("Invalid interval. Valid range 5 msec to 30000 msec\n")
        sys.exit(3)
      if interval < 5 or interval > 30000:
        sys.stderr.write("Invalid interval. Valid range 5 msec to 30000 msec\n")
        sys.exit(4)
    elif o == "-m" or o == "--map":
      if "=" not in a:
        sys.stderr.write("Invalid map.\n")
        sys.exit(5)

      n, v = a.split("=", 1)
      reqmap[n.strip()] = v.strip()

  # now do stuff

  xt = xtime.XTime()
  ws = webserver.Webserver(xt, port=port)

  ws.start()

  while True:

    now = xt.time_ms()

    print("tick", now)

    ws.serve(reqmap, now)

    xt.sleep_ms(interval)

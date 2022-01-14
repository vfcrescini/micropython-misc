#!/bin/sh

# Copyright (C) 2022 Vino Fernando Crescini <vfcrescini@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

# 2021-11-19 tzdatagen.sh

# generates custom 100-year tzdata suitable for use with xtime.py
# output line format: <seconds since embedded epoch> <utc offset in seconds>


tzpath=/usr/share/zoneinfo/Australia/Sydney


filter ()
{
  awk -v epoch=${epoch} '
  {
    sprintf("date -d \"%s %s\" +%%s", $1, $2) | getline d;
    len = 7 - length($3);
    off = len > 0 ? sprintf("%s%0*d", $3, len, 0) : "";
    printf "%d %s\n", d - epoch, off;
  }
  '
}


while [ ${#} -ge 1 ]; do
  if [ "${1}" = "-h" ]; then
    echo "usage: tzdatagen.sh [options]"
    echo "options:"
    echo "  -h         print this usage and exit"
    echo "  -z tzpath  path to tzdata"
    exit 0
  elif [ "${1}" = "-z" ]; then
    if [ -n "${2}" ]; then
      tzpath="${2}"
      shift 1
    fi
  fi
  shift 1
done

epoch=`date -d '2000-01-01 00:00:00' -u  +%s`
year=`date +%Y`

zdump -c ${year},$((${year}+100)) -i ${tzpath} | tail -n +4 | filter | sed -e "s/^\([0-9]\+\) \([+-]\)\([0-9]\{2\}\)\([0-9]\{2\}\)\([0-9]\{2\}\)$/\1 \2\ \3 \4 \5/" | while read ts op hh mm ss; do
  h=$((10#${hh} * 3600))
  m=$((10#${mm} * 60))
  s=$((10#${ss}))
  printf "%s %s%s\n" "${ts}" "${op}" $((${h} + ${m} + ${s}))
done

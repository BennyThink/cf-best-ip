#!/usr/local/bin/python3
# coding: utf-8

# cf-best-ip - speedtest.py
# 5/3/22 10:55
#

__author__ = "Benny <benny.think@gmail.com>"

import logging
import random
import socket
import time
from concurrent.futures import ThreadPoolExecutor

import requests
import requests.packages.urllib3.util.connection as urllib3_cn
import urllib3
from forcediphttpsadapter.adapters import ForcedIPHTTPSAdapter
from tqdm import tqdm
from common import sizeof_fmt, apply_log_formatter

apply_log_formatter()
urllib3.disable_warnings()
TIMEOUT = 12
executor = ThreadPoolExecutor(max_workers=10)
old_gai_family = urllib3_cn.allowed_gai_family
result = []


def get_ip_list(ipv6=False):
    if ipv6:
        urllib3_cn.allowed_gai_family = lambda: socket.AF_INET6
    else:
        urllib3_cn.allowed_gai_family = lambda: socket.AF_INET
    url = "https://service.baipiao.eu.org"
    text = requests.get(url, headers={"User-Agent": "curl"}).text
    return text.split()[4:]


def test_download_speed(ip: "str"):
    urllib3_cn.allowed_gai_family = old_gai_family
    logging.info("Testing download speed for ip: %s" % ip)
    url = "https://cdn.cloudflare.steamstatic.com/steam/apps/256843155/movie_max.mp4"
    session = requests.Session()
    session.mount(url, ForcedIPHTTPSAdapter(dest_ip=ip))

    t0 = time.time()
    total_length = 0
    req = session.get(url, verify=False, stream=True)
    # total size is 203MB, we fetch 1Mi B each time
    for chunk in req.iter_content(1024 * 1024):
        total_length += len(chunk)

    speed = int(total_length / (time.time() - t0))
    speed_fmt = sizeof_fmt(speed)
    speed = {
        "ip": ip,
        "speed_fmt": speed_fmt,
        "speed": speed
    }
    logging.info("IP %s download speed: %s" % (ip, speed_fmt))
    result.append(speed)


def run_get_ip_list():
    v4_list = get_ip_list()
    try:
        v6_list = get_ip_list(ipv6=True)
    except Exception:
        v6_list = []
    return v4_list, v6_list


def run_tester():
    v4_list, v6_list = run_get_ip_list()

    v4_list = random.sample(v4_list, 5)
    v6_list = random.sample(v6_list, 5)
    # test v4
    try:
        list(tqdm(executor.map(test_download_speed, v4_list, timeout=TIMEOUT), total=len(v4_list)))
    except Exception as e:
        logging.error("Test timeout for %s", e)
    result.sort(key=lambda x: x['speed'], reverse=True)

    fastest_ipv4 = result[0] if result else None

    result.clear()

    # test v6
    try:
        list(tqdm(executor.map(test_download_speed, v6_list), total=len(v4_list)))
    except Exception as e:
        logging.error("Test timeout for %s", e)
    result.sort(key=lambda x: x['speed'], reverse=True)

    fastest_ipv6 = result[0] if result else None

    logging.info("Fastest IPv4: %s", fastest_ipv4)
    logging.info("Fastest IPv6: %s", fastest_ipv6)
    return fastest_ipv4, fastest_ipv6

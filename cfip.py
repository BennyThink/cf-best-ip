#!/usr/local/bin/python3
# coding: utf-8

# untitled - cfip.py
# 5/2/22 19:00
#

__author__ = "Benny <benny.think@gmail.com>"

import argparse
import contextlib
import logging
import random
import socket
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import requests
import requests.packages.urllib3.util.connection as urllib3_cn
import urllib3
from beautifultable import BeautifulTable
from forcediphttpsadapter.adapters import ForcedIPHTTPSAdapter
from tqdm import tqdm

urllib3.disable_warnings()
TIMEOUT = 12
executor = ThreadPoolExecutor(max_workers=10)

parser = argparse.ArgumentParser(description='Find best Cloudflare IP and restart cloudflared')
parser.add_argument('--save', action='store_true')
parser.add_argument('--service', dest='service', help='systemd service file name')
parser.add_argument('--host', dest='host', help='hostname for your tunnel')

old_gai_family = urllib3_cn.allowed_gai_family
result = []

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s %(filename)s:%(lineno)d %(levelname).1s] %(message)s',
    datefmt="%Y-%m-%d %H:%M:%S"
)


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


def sizeof_fmt(num: int, suffix='B'):
    for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)


def run_get_ip_list():
    v4_list = get_ip_list()
    try:
        v6_list = get_ip_list(ipv6=True)
    except Exception:
        v6_list = []
    return v4_list, v6_list


def run_tester():
    table = BeautifulTable()
    table.columns.header = ["IP", "speed", "speed_fmt"]

    v4_list, v6_list = run_get_ip_list()

    v4_list = random.sample(v4_list, 5)
    v6_list = random.sample(v6_list, 5)
    # test v4
    try:
        list(tqdm(executor.map(test_download_speed, v4_list, timeout=TIMEOUT), total=len(v4_list)))
    except Exception as e:
        logging.error("Test timeout for %s", e)
    result.sort(key=lambda x: x['speed'], reverse=True)

    for item in result:
        table.rows.append(item.values())
    fastest_ipv4 = result[0] if result else None

    result.clear()
    table.rows.append(["", "", ""])

    # test v6
    try:
        list(tqdm(executor.map(test_download_speed, v6_list), total=len(v4_list)))
    except Exception as e:
        logging.error("Test timeout for %s", e)
    result.sort(key=lambda x: x['speed'], reverse=True)

    for item in result:
        table.rows.append(item.values())
    fastest_ipv6 = result[0] if result else None

    logging.info("Fastest IPv4: %s", fastest_ipv4)
    logging.info("Fastest IPv6: %s", fastest_ipv6)
    print(table)
    return fastest_ipv4, fastest_ipv6


if __name__ == '__main__':
    args = parser.parse_args()
    save = args.save
    service = args.service
    host = args.host

    if save and host is None:
        logging.critical("--host is required when --save is specified")
        sys.exit(1)

    v4, v6 = run_tester()
    if save:
        logging.info("Changing hosts...")
        old_hosts = open("/etc/hosts").read()
        new_hosts = ""

        for i in old_hosts.split("\n"):
            if host not in i:
                new_hosts += i + "\n"
        v4_entry = v6_entry = ""
        if v4:
            v4_entry = f"{v4['ip']} {host}"
        if v6:
            v6_entry = f"{v6['ip']} {host}"

        new_entry = f"{v4_entry}\n{v6_entry}"
        new_hosts += new_entry
        with open("/etc/hosts", "w") as f:
            f.write(new_hosts)

        logging.info("Changing hosts done.")

    if service:
        logging.info("Restarting service %s", service)
        subprocess.check_output(["systemctl", "restart", service])
        logging.info("Restarting service done.")

    sys.exit(0)

#!/usr/local/bin/python3
# coding: utf-8

# untitled - cfip.py
# 5/2/22 19:00
#

__author__ = "Benny <benny.think@gmail.com>"

import argparse
import logging
import subprocess
import sys
from builtin.speedtest import run_tester as builtin_tester
from external.speedtest import run_tester as external_tester
from common import apply_log_formatter
from beautifultable import BeautifulTable

parser = argparse.ArgumentParser(description='Find best Cloudflare IP and restart cloudflared')
parser.add_argument('--save', action='store_true')
parser.add_argument('--service', dest='service', help='systemd service file name')
parser.add_argument('--host', dest='host', help='hostname for your tunnel')
parser.add_argument('--runner', default='external', const='runner', nargs='?', choices=['external', 'builtin'],
                    help='Choose default speedtest runner(default: %(default)s)')

apply_log_formatter()


def draw_table(results):
    table = BeautifulTable()
    table.columns.header = ["IP", "speed", "speed_fmt"]
    for item in results:
        table.rows.append(item.values())
    print(table)


def update_hosts():
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


def restart_service():
    logging.info("Restarting service %s", service)
    subprocess.check_output(["systemctl", "restart", service])
    logging.info("Restarting service done.")


if __name__ == '__main__':
    args = parser.parse_args()
    save = args.save
    service = args.service
    host = args.host
    runner = args.runner

    if save and host is None:
        logging.critical("--host is required when --save is specified")
        sys.exit(1)

    if runner == "external":
        v4, v6 = external_tester()
    else:
        v4, v6 = builtin_tester()

    draw_table(v4 + v6)

    if save:
        update_hosts()

    if service:
        restart_service()

    sys.exit(0)

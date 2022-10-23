#!/usr/local/bin/python3
# coding: utf-8

# cf-best-ip - speedtest.py
# 5/3/22 11:01
#

__author__ = "Benny <benny.think@gmail.com>"

import csv
import logging
import requests
import tarfile
import tempfile
import pathlib
import subprocess
from common import apply_log_formatter
import os

import zipfile

apply_log_formatter()

wd = pathlib.Path(__file__).parent


def get_download_link():
    arch_map = {
        "x86_64": "amd64",
        "aarch64": "arm64",
        "armv7l": "arm",
        "i386": "386",
        "mips": "mips",
    }
    api = "https://api.github.com/repos/XIU2/CloudflareSpeedTest/releases/latest"
    assets = requests.get(api).json()["assets"]
    download_link = {item["name"]: item["browser_download_url"] for item in assets}
    system = os.uname()
    sysname = system.sysname.lower()
    arch = arch_map.get(system.machine, "amd64")
    filename = f"CloudflareST_{sysname}_{arch}"

    for key, value in download_link.items():
        if filename in key:
            return value


def download_and_extract():
    # download from above link
    if wd.joinpath("CloudflareST").exists() and \
            wd.joinpath("ip.txt").exists() and wd.joinpath("ipv6.txt").exists():
        logging.info("CloudflareST already exists")
        return

    link = get_download_link()
    logging.info("Downloading binary from %s", link)
    r = requests.get(link)
    with tempfile.NamedTemporaryFile() as f:
        f.write(r.content)
        f.flush()
        if link.endswith(".zip"):
            zipfile.ZipFile(f.name).extractall(wd)
            os.chmod(wd.joinpath("CloudflareST").as_posix(), 0o755)
        else:
            with tarfile.open(f.name) as tar:
                def is_within_directory(directory, target):
                    
                    abs_directory = os.path.abspath(directory)
                    abs_target = os.path.abspath(target)
                
                    prefix = os.path.commonprefix([abs_directory, abs_target])
                    
                    return prefix == abs_directory
                
                def safe_extract(tar, path=".", members=None, *, numeric_owner=False):
                
                    for member in tar.getmembers():
                        member_path = os.path.join(path, member.name)
                        if not is_within_directory(path, member_path):
                            raise Exception("Attempted Path Traversal in Tar File")
                
                    tar.extractall(path, members, numeric_owner=numeric_owner) 
                    
                
                safe_extract(tar, wd)


def run_tester():
    download_and_extract()

    logging.info("Running CloudflareST for IPv4...")
    cmd = wd.joinpath("CloudflareST").as_posix()
    subprocess.call([cmd], cwd=wd, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    v4 = read_csv()

    logging.info("Running CloudflareST for IPv6...")
    subprocess.call([cmd, "-f", "ipv6.txt", "-ipv6"], cwd=wd, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    v6 = read_csv()

    return v4, v6


def read_csv():
    results = []
    with open(wd.joinpath("result.csv")) as f:
        next(f)
        reader = csv.reader(f)
        for row in reader:
            results.append({
                "ip": row[0],
                "speed_fmt": f"{row[-1]} MiB",
                "speed": float(row[-1]) * 1024 * 1024
            })

    results.sort(key=lambda x: x['speed'], reverse=True)
    wd.joinpath("result.csv").unlink()
    return results


if __name__ == '__main__':
    ipv4, ipv6 = run_tester()
    print(ipv4)
    print(ipv6)

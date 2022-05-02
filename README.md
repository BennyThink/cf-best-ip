# cf-best-ip

Intended for cloudfwared

# Installation

```shell
virtualenv venv
source venv/bin/activate
pip install -r requirements.txt
```

# Usage

```shell
usage: cfip.py [-h] [--save] [--service SERVICE] [--host HOST]

Find best Cloudflare IP and restart cloudflared

optional arguments:
  -h, --help         show this help message and exit
  --save
  --service SERVICE  systemd service file name
  --host HOST        hostname for your tunnel
  

# get the best ip, both IPv4 and IPv6
python3 cfip.py

# write result to hosts
python3 cfip.py --save --host=your.domain.name
# write result to hosts and restart service
python3 cfip.py --save --host=your.domain.name --service=cf-service-name
```


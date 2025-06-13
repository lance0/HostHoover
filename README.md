# HostHoover

HostHoover is a Python 3 utility that collects running configuration files from network devices and archives them.

## Features

- Pings each host in the provided subnet and skips unreachable devices.
- Connects over SSH using [Netmiko](https://github.com/ktbyers/netmiko).
- Saves each configuration to a file named after the device hostname.
- Creates a ZIP archive containing all collected configuration files.

## Requirements

- Python 3.8 or higher
- `netmiko` Python package

Install the dependencies with:

```bash
pip install -r requirements.txt
```

## Usage

```bash
python3 hosthoover.py <network_cidr> -u <username> -p <password> [options]
```

Common options:

- `-d`, `--device-type`  Netmiko device type (default: `cisco_ios`)
- `-o`, `--output`       Directory to save configs (default: `configs`)
- `-z`, `--zip-name`     Name of the zip file (default: `configs.zip`)
- `-c`, `--command`      CLI command to run (default: `show running-config`)

Example:

```bash
python3 hosthoover.py 192.168.1.0/24 -u admin -p password
```

The script processes the hosts in the `/24` network and stores the results in the specified output directory.

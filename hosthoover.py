#!/usr/bin/env python3

import argparse
import ipaddress
import os
import zipfile
import re
import subprocess
import platform
from netmiko import ConnectHandler, NetmikoTimeoutException, NetmikoAuthenticationException


def is_reachable(host, count=1, timeout=1):
    """Ping a host to check reachability in a cross-platform way."""
    system = platform.system().lower()
    if system == 'windows':
        # Windows ping uses milliseconds for timeout
        cmd = ["ping", "-n", str(count), "-w", str(timeout * 1000), host]
    else:
        cmd = ["ping", "-c", str(count), "-W", str(timeout), host]

    try:
        subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return True
    except subprocess.CalledProcessError:
        return False


def backup_configs(network, username, password, device_type, output_dir,
                   zip_name, command, ping_count=1, ping_timeout=1):
    # Parse network and get all hosts in the subnet
    net = ipaddress.ip_network(network, strict=False)
    hosts = list(net.hosts())

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    successes = []
    failures = []

    for ip in hosts:
        host = str(ip)
        # Skip if host is unreachable
        if not is_reachable(host, count=ping_count, timeout=ping_timeout):
            print(f"{host} is unreachable, skipping.")
            failures.append(host)
            continue

        device_params = {
            'device_type': device_type,
            'host': host,
            'username': username,
            'password': password,
        }
        try:
            print(f"Connecting to {host}...")
            connection = ConnectHandler(**device_params)
            cmd = command if command else 'show running-config'
            print(f"Running command: {cmd}")
            config = connection.send_command(cmd)

            # Extract hostname from running-config, fallback to IP
            match = re.search(r'^hostname\s+(\S+)', config, re.MULTILINE)
            filename_base = match.group(1) if match else host

            # Save running config to file named after hostname
            filename = os.path.join(output_dir, f"{filename_base}.cfg")
            with open(filename, 'w') as file:
                file.write(config)
            print(f"Config saved: {filename}")
            connection.disconnect()
            successes.append(host)

        except (NetmikoTimeoutException, NetmikoAuthenticationException) as error:
            print(f"Failed for {host}: {error}")
            failures.append(host)

    # Create zip archive of all .cfg files
    zip_path = os.path.join(output_dir, zip_name)
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for cfg_file in os.listdir(output_dir):
            if cfg_file.endswith('.cfg'):
                zipf.write(os.path.join(output_dir, cfg_file), cfg_file)
    print(f"All configs zipped into {zip_path}")

    # Print summary of results
    print("\nSummary:")
    print(f"  Successful: {len(successes)}")
    if successes:
        print("    " + ", ".join(successes))
    print(f"  Failed/Skipped: {len(failures)}")
    if failures:
        print("    " + ", ".join(failures))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Backup running-config from all reachable hosts in a subnet, naming files by hostname, and zip them."
    )
    parser.add_argument('network', help='Network in CIDR notation, e.g., 192.168.1.0/24')
    parser.add_argument(
        '-u', '--username',
        default=os.getenv('SSH_USERNAME'),
        help='SSH username (or set SSH_USERNAME env var)'
    )
    parser.add_argument(
        '-p', '--password',
        default=os.getenv('SSH_PASSWORD'),
        help='SSH password (or set SSH_PASSWORD env var)'
    )
    parser.add_argument('-d', '--device-type', default='cisco_ios', help='Netmiko device type (default: cisco_ios)')
    parser.add_argument('-o', '--output', default='configs', help='Directory to save configs (default: configs)')
    parser.add_argument('-z', '--zip-name', default='configs.zip', help='Name of the zip file (default: configs.zip)')
    parser.add_argument('-c', '--command', help="CLI command to run (default: 'show running-config')")
    parser.add_argument('--ping-count', type=int, default=1, help='Number of ping attempts (default: 1)')
    parser.add_argument('--ping-timeout', type=int, default=1, help='Ping timeout in seconds (default: 1)')
    args = parser.parse_args()

    if not args.username or not args.password:
        parser.error('SSH username and password required via options or environment variables')

    backup_configs(
        args.network,
        args.username,
        args.password,
        args.device_type,
        args.output,
        args.zip_name,
        args.command,
        ping_count=args.ping_count,
        ping_timeout=args.ping_timeout
    )

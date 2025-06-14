"""
HostHoover v2.0 - Enterprise Network Configuration Management
"""

import argparse
import ipaddress
import logging
import os
import smtplib
import subprocess
import sys
from concurrent.futures import ThreadpoolExecutor, as_completed
from datetime import datetime
from email.mime.text import MIMEText
from getpass import getpass
from pathlib import Path
from typing import Dict, List, Optional

import netmiko
import yaml
from netmiko import ConnectHandler
from netmiko.ssh_exception import NetmikoAuthenticationException, NetmikoTimeoutException

# Configure logging
logging.basicConfig(
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    'username': None,
    'password': None,
    'device_type': 'cisco_ios',
    'subnet': '192.168.1.0/24',
    'output_dir': 'backups',
    'max_workers': 15,
    'smtp': None,
    'git': False,
    'ssh_key': None
}

def load_config(args: argparse.Namespace) -> Dict:
    """Load configuration from YAML file and merge with CLI args"""
    config = DEFAULT_CONFIG.copy()
    
    if args.config:
        with open(args.config) as f:
            file_config = yaml.safe_load(f)
            config.update(file_config)
    
    # CLI args override config file
    for key in ['username', 'password', 'device_type', 'subnet', 'output_dir']:
        if getattr(args, key):
            config[key] = getattr(args, key)
    
    return config

def generate_ips(subnet: str) -> List[str]:
    """Generate IP list from subnet using ipaddress module"""
    try:
        network = ipaddress.ip_network(subnet)
        return [str(host) for host in network.hosts()]
    except ValueError as e:
        logger.error(f"Invalid subnet: {e}")
        sys.exit(1)

def send_email(smtp_config: Dict, subject: str, body: str) -> bool:
    """Send email notification using SMTP configuration"""
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = smtp_config['sender']
    msg['To'] = smtp_config['recipient']

    try:
        with smtplib.SMTP(smtp_config['server'], smtp_config['port']) as server:
            server.starttls()
            server.login(smtp_config['username'], smtp_config['password'])
            server.send_message(msg)
        return True
    except Exception as e:
        logger.error(f"Email send failed: {e}")
        return False

def git_commit(file_path: str, message: str) -> bool:
    """Commit file to git repository"""
    try:
        subprocess.run(['git', 'add', file_path], check=True)
        subprocess.run(['git', 'commit', '-m', message], check=True)
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Git commit failed: {e}")
        return False

def backup_device(device: Dict) -> Optional[str]:
    """Execute backup command with SSH key support"""
    conn_params = {
        'device_type': device['device_type'],
        'host': device['ip'],
        'username': device['username'],
        'password': device['password'],
        'use_keys': device['ssh_key'] is not None,
        'key_file': device['ssh_key']
    }

    try:
        with ConnectHandler(**conn_params) as conn:
            return conn.send_command(device['command'])
    except (NetmikoAuthenticationException, NetmikoTimeoutException) as e:
        logger.error(f"Connection failed to {device['ip']}: {e}")
    return None

def process_device(config: Dict, ip: str) -> Dict:
    """Process single device with all features"""
    device = {
        'ip': ip,
        'username': config['username'],
        'password': config['password'],
        'device_type': config['device_type'],
        'ssh_key': config['ssh_key'],
        'command': 'show running-config'
    }

    result = {'ip': ip, 'status': 'success'}
    
    # Backup logic
    config_data = backup_device(device)
    if not config_data:
        result['status'] = 'failed'
        if config.get('smtp'):
            send_email(config['smtp'], 
                      f"Backup Failed - {ip}",
                      f"Failed to backup device {ip}")
        return result

    # File handling
    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    filename = f"{config['output_dir']}/{ip}_{timestamp}.cfg"
    try:
        Path(config['output_dir']).mkdir(exist_ok=True)
        with open(filename, 'w') as f:
            f.write(config_data)
    except IOError as e:
        logger.error(f"File write failed: {e}")
        result['status'] = 'write_error'
        return result

    # Git integration
    if config.get('git'):
        git_commit(filename, f"Backup {ip} {timestamp}")
    
    return result

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', help='Configuration YAML file')
    parser.add_argument('-u', '--username', help='SSH username')
    parser.add_argument('-p', '--password', help='SSH password')
    parser.add_argument('-k', '--ssh-key', help='SSH private key path')
    parser.add_argument('-d', '--device-type', help='Netmiko device type')
    parser.add_argument('-s', '--subnet', help='Network subnet')
    parser.add_argument('-o', '--output-dir', help='Output directory')
    args = parser.parse_args()

    config = load_config(args)
    
    if not config['username'] or not (config['password'] or config['ssh_key']):
        logger.error("Missing authentication credentials")
        sys.exit(1)

    ips = generate_ips(config['subnet'])
    
    with ThreadPoolExecutor(max_workers=config['max_workers']) as executor:
        futures = [executor.submit(process_device, config, ip) for ip in ips]
        
        for future in as_completed(futures):
            result = future.result()
            logger.info(f"{result['ip']}: {result['status'].upper()}")

if __name__ == "__main__":
    main()

"""
HostHoover v2.2 - Network Configuration Backup Tool with Multi-Format Archiving
"""

import argparse
import ipaddress
import logging
import os
import smtplib
import subprocess
import sys
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from email.mime.text import MIMEText
from getpass import getpass
from pathlib import Path
from typing import Dict, List, Optional

import yaml
from netmiko import ConnectHandler
from netmiko.ssh_exception import NetmikoAuthenticationException, NetmikoTimeoutException

try:
    import py7zr
except ImportError:
    py7zr = None

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
    'ssh_key': None,
    'archive_format': 'zip'  # zip/7z/rar
}

def load_config(args: argparse.Namespace) -> Dict:
    """Load configuration from YAML file and merge with CLI args"""
    config = DEFAULT_CONFIG.copy()
    if args.config:
        with open(args.config) as f:
            file_config = yaml.safe_load(f)
            if file_config:
                config.update(file_config)
    # CLI args override config file
    for key in ['username', 'password', 'device_type', 'subnet', 'output_dir', 'ssh_key']:
        if getattr(args, key, None):
            config[key] = getattr(args, key)
    if getattr(args, 'archive_format', None):
        config['archive_format'] = args.archive_format
    return config

def generate_ips(subnet: str) -> List[str]:
    """Generate IP list from subnet using ipaddress module"""
    try:
        network = ipaddress.ip_network(subnet, strict=False)
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
    }
    if device['ssh_key']:
        conn_params['use_keys'] = True
        conn_params['key_file'] = device['ssh_key']
    else:
        conn_params['password'] = device['password']
    try:
        with ConnectHandler(**conn_params) as conn:
            return conn.send_command(device['command'])
    except (NetmikoAuthenticationException, NetmikoTimeoutException) as e:
        logger.error(f"Connection failed to {device['ip']}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error with {device['ip']}: {e}")
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
    config_data = backup_device(device)
    if not config_data:
        result['status'] = 'failed'
        if config.get('smtp'):
            send_email(config['smtp'],
                       f"Backup Failed - {ip}",
                       f"Failed to backup device {ip}")
        return result
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
    if config.get('git'):
        git_commit(filename, f"Backup {ip} {timestamp}")
    return result

def create_archive(output_dir: str, format: str) -> str:
    """Create compressed archive of backup files"""
    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    archive_base = f"{output_dir}/hosthoover_backup_{timestamp}"
    try:
        if format == 'zip':
            archive_path = f"{archive_base}.zip"
            with zipfile.ZipFile(archive_path, 'w') as zipf:
                for file in Path(output_dir).glob('*.cfg'):
                    zipf.write(file, arcname=file.name)
            return archive_path
        elif format == '7z':
            if not py7zr:
                raise RuntimeError("py7zr module required for 7z support")
            archive_path = f"{archive_base}.7z"
            with py7zr.SevenZipFile(archive_path, 'w') as z7f:
                for file in Path(output_dir).glob('*.cfg'):
                    z7f.write(file, arcname=file.name)
            return archive_path
        elif format == 'rar':
            archive_path = f"{archive_base}.rar"
            rar_cmd = ['rar', 'a', '-ep1', archive_path, f"{output_dir}/*.cfg"]
            result = subprocess.run(rar_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise RuntimeError(f"RAR failed: {result.stderr}")
            return archive_path
        else:
            raise ValueError(f"Unsupported archive format: {format}")
    except Exception as e:
        logger.error(f"Archive creation failed: {e}")
        raise

def main():
    parser = argparse.ArgumentParser(description="HostHoover - Network Configuration Backup Tool")
    parser.add_argument('--config', help='Configuration YAML file')
    parser.add_argument('-u', '--username', help='SSH username')
    parser.add_argument('-p', '--password', help='SSH password')
    parser.add_argument('-k', '--ssh-key', help='SSH private key path')
    parser.add_argument('-d', '--device-type', help='Netmiko device type')
    parser.add_argument('-s', '--subnet', help='Network subnet')
    parser.add_argument('-o', '--output-dir', help='Output directory')
    parser.add_argument('--archive-format', help='Archive format: zip, 7z, or rar')
    args = parser.parse_args()

    config = load_config(args)
    if not config['username'] or not (config['password'] or config['ssh_key']):
        logger.error("Missing authentication credentials")
        sys.exit(1)
    if not config['password'] and not config['ssh_key']:
        config['password'] = getpass(prompt='SSH Password: ')
    ips = generate_ips(config['subnet'])
    results = {'success': 0, 'failed': 0, 'write_error': 0}
    with ThreadPoolExecutor(max_workers=config['max_workers']) as executor:
        futures = [executor.submit(process_device, config, ip) for ip in ips]
        for future in as_completed(futures):
            result = future.result()
            status = result['status']
            results[status] = results.get(status, 0) + 1
            logger.info(f"{result['ip']}: {status.upper()}")
    # Archive backups
    try:
        archive_path = create_archive(config['output_dir'], config['archive_format'])
        logger.info(f"Created {config['archive_format'].upper()} archive: {archive_path}")
    except Exception as e:
        logger.error(f"Archive creation failed: {e}")
        sys.exit(1)
    # Print summary
    print("\nBackup Summary:")
    for key, val in results.items():
        print(f"{key.capitalize()}: {val}")

if __name__ == "__main__":
    main()

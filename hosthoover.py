"""
HostHoover - Parallel Network Configuration Backup Tool
Optimized for performance and reliability
"""

import logging
import argparse
import os
import sys
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from getpass import getpass
from typing import Dict, Tuple, Optional

import netmiko
from netmiko import ConnectHandler
from netmiko.ssh_exception import NetmikoAuthenticationException, NetmikoTimeoutException
import paramiko
import requests.exceptions

# Configure logging
logging.basicConfig(
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

DEFAULT_DEVICE_TYPE = 'cisco_ios'
CONFIG_COMMAND = 'show running-config'
MAX_WORKERS = 15  # Optimal for most network devices
PING_TIMEOUT = 2  # Seconds

def ping_device(ip: str) -> bool:
    """Check device availability using ICMP ping with system command."""
    param = '-n' if os.name == 'nt' else '-c'
    command = ['ping', param, '1', '-w', str(PING_TIMEOUT), ip]
    return os.system(' '.join(command)) == 0

def backup_device(device: Dict[str, str], command: str) -> Optional[str]:
    """Execute backup command on network device with error handling."""
    try:
        with ConnectHandler(**device) as conn:
            output = conn.send_command(command)
            conn.disconnect()
        return output
    except (NetmikoAuthenticationException, NetmikoTimeoutException) as e:
        logger.error(f"Connection failed to {device['host']}: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error with {device['host']}: {str(e)}")
    return None

def process_device(args: Tuple[str, str, str, str, str]) -> Dict[str, str]:
    """Process single device with ping check and backup."""
    ip, username, password, device_type, output_dir = args
    
    if not ping_device(ip):
        return {'ip': ip, 'status': 'unreachable'}
    
    device = {
        'device_type': device_type,
        'host': ip,
        'username': username,
        'password': password,
    }
    
    config = backup_device(device, CONFIG_COMMAND)
    if not config:
        return {'ip': ip, 'status': 'backup_failed'}
    
    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    filename = f"{output_dir}/{ip}_{timestamp}.cfg"
    
    try:
        with open(filename, 'w') as f:
            f.write(config)
        return {'ip': ip, 'status': 'success', 'file': filename}
    except IOError as e:
        logger.error(f"File write failed for {ip}: {str(e)}")
        return {'ip': ip, 'status': 'write_failed'}

def main():
    parser = argparse.ArgumentParser(description='Network Configuration Backup Tool')
    parser.add_argument('subnet', help='Network subnet (e.g., 192.168.1.0/24)')
    parser.add_argument('-u', '--username', required=True, help='SSH username')
    parser.add_argument('-d', '--device-type', default=DEFAULT_DEVICE_TYPE, 
                       help=f'Netmiko device type (default: {DEFAULT_DEVICE_TYPE})')
    parser.add_argument('-o', '--output-dir', default='backups',
                       help='Output directory (default: backups)')
    args = parser.parse_args()
    
    password = getpass(prompt='SSH Password: ')
    
    # Create output directory if needed
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Generate IP list from subnet (simplified example)
    # In production, use ipaddress module for proper subnet handling
    base_ip = '.'.join(args.subnet.split('.')[:3])
    ips = [f"{base_ip}.{i}" for i in range(1, 255)]
    
    # Prepare thread arguments
    task_args = [(ip, args.username, password, args.device_type, args.output_dir) 
                for ip in ips]
    
    results = {'success': 0, 'failed': 0, 'unreachable': 0}
    
    try:
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = [executor.submit(process_device, arg) for arg in task_args]
            
            for future in as_completed(futures):
                result = future.result()
                if result['status'] == 'success':
                    results['success'] += 1
                    logger.info(f"Backup succeeded: {result['ip']}")
                elif result['status'] == 'unreachable':
                    results['unreachable'] += 1
                    logger.warning(f"Device unreachable: {result['ip']}")
                else:
                    results['failed'] += 1
                    logger.error(f"Backup failed: {result['ip']}")
                    
    except KeyboardInterrupt:
        logger.info("\nOperation cancelled by user")
        sys.exit(1)
        
    # Print summary
    print("\nBackup Summary:")
    print(f"Successful: {results['success']}")
    print(f"Unreachable: {results['unreachable']}")
    print(f"Failed: {results['failed']}")

if __name__ == "__main__":
    main()

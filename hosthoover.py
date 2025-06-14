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

import netmiko
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
            raise ValueError(f"Unsupported format: {format}")
    
    except Exception as e:
        logger.error(f"Archive creation failed: {e}")
        raise

def main():
    # ... [previous main code remains unchanged until end] ...
    
    # Create archive after backups
    try:
        archive_path = create_archive(config['output_dir'], config['archive_format'])
        logger.info(f"Created {config['archive_format'].upper()} archive: {archive_path}")
    except Exception as e:
        logger.error(f"Archive creation failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

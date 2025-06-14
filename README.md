# HostHoover

**Automated, Parallel Network Configuration Backup Tool**

---

## Features

- ⚡ **Parallel Backups:** Fast, multi-threaded configuration collection across large networks.
- 🗂️ **Subnet Support:** Accurate IP address generation using Python’s `ipaddress` module.
- 🔑 **SSH Key & Password Auth:** Use SSH keys or passwords for device authentication.
- 🛠️ **Flexible Configuration:** Centralized YAML config file, with CLI override support.
- 📧 **Email Alerts:** SMTP notifications for failed backups.
- 🗃️ **Version Control:** Optional Git integration for automatic config tracking.
- 📁 **Organized Output:** Timestamped backups, organized per device.

---

## Quick Start

### 1a. Install Core Dependencies

```pip install netmiko pyyaml```

OR

### 1b. Install All Dependencies

```pip install -r requirements.txt```

### 2. Prepare Your Config File (optional)

Create a `config.yaml` (see example below).

### 3. Run HostHoover

Using a config file

```python hosthoover.py --config config.yaml```

Or override config file with CLI arguments

```python hosthoover.py --subnet 192.168.1.0/24 -u admin -k ~/.ssh/id_rsa --archive-format zip```

---

## Example `config.yaml`
```
username: admin
password: your_password # Optional if using SSH key
ssh_key: ~/.ssh/id_rsa # Optional, use instead of password
device_type: cisco_ios
subnet: 192.168.1.0/24
output_dir: ./backups
max_workers: 20

smtp:
server: smtp.example.com
port: 587
sender: backups@example.com
recipient: admin@example.com
username: smtp_user
password: smtp_pass

git: true
```
---

## Command-Line Arguments

| Argument         | Description                                | Example                          |
|------------------|--------------------------------------------|----------------------------------|
| `--config`       | Path to YAML configuration file            | `--config config.yaml`           |
| `-u`, `--username` | SSH username                             | `-u admin`                       |
| `-p`, `--password` | SSH password                             | `-p mypass`                      |
| `-k`, `--ssh-key`  | SSH private key path                     | `-k ~/.ssh/id_rsa`               |
| `-d`, `--device-type` | Netmiko device type                   | `-d cisco_ios`                   |
| `-s`, `--subnet`     | Network subnet (CIDR)                  | `-s 10.0.0.0/24`                 |
| `-o`, `--output-dir` | Output directory for backups            | `-o ./backups`                   |

*CLI arguments override config file settings.*

---

## Output

- Each device’s config is saved as:  
  `output_dir/device_ip_YYYYMMDD-HHMMSS.cfg`
- If enabled, every backup is auto-committed to the local Git repo.
- Failed backups trigger an email alert if SMTP is configured.

---
## Archive Formats

HostHoover supports three compression formats:

| Format | Requirements                          | Notes                              |
|--------|---------------------------------------|------------------------------------|
| ZIP    | Built-in                              | Default format, cross-platform     |
| 7Z     | `pip install py7zr`                   | Better compression ratio           |
| RAR    | Install [RARLAB](https://www.rarlab.com/) | Proprietary format, Windows-first |

Configure in `config.yaml`:

## Requirements

- Python 3.7+
- [Netmiko](https://github.com/ktbyers/netmiko)
- [PyYAML](https://pyyaml.org/)

---

## Best Practices

- Use SSH keys for authentication where possible.
- Store your config file securely and restrict permissions.
- Set up your Git repository before enabling version control.
- Use environment variables or a secrets manager for SMTP credentials in production.

---

## Example Usage

Backup all devices in a subnet using SSH key authentication

```python hosthoover.py --subnet 10.0.1.0/24 -u netadmin -k ~/.ssh/id_rsa```

Use a YAML config file for all settings

```python hosthoover.py --config config.yaml```

---

## Troubleshooting

- **Authentication errors:** Double-check your username, password, or SSH key path.
- **Subnet errors:** Ensure your subnet is valid (e.g., `192.168.1.0/24`).
- **SMTP issues:** Verify your SMTP server, port, and credentials.
- **Git errors:** Make sure your output directory is a Git repository (`git init`).

---

## License

MIT License

---

## Credits

- Built with [Netmiko](https://github.com/ktbyers/netmiko)
- Inspired by network automation best practices

---

## Contributing

Pull requests and suggestions are welcome! Please open an issue or submit a PR.


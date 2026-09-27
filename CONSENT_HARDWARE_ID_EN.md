# Consent for Hardware Identifier Collection

## Why This Is Needed

To lock server installations to a device, **hardware identifiers** (hardware ID) are collected. This is necessary to bind the installation to a specific PC and protect against unauthorized copying.

## What Is Collected

| Component | Description | Stability |
|-----------|-------------|-----------|
| **CPU ID** | Unique processor identifier | Does not change with software updates |
| **Motherboard Serial Number** | Motherboard serial number | Does not change with software updates |
| **Disk Serial Number** | System disk serial number | Does not change with OS reinstallation |
| **BIOS Serial Number** | BIOS/UEFI serial number | Does not change with software updates |

## How It Works

1. On first launch, the starter collects hardware identifiers
2. A **fingerprint** (SHA-256 hash) is generated from them
3. The fingerprint is saved locally and bound to the installation
4. On reinstallation, fingerprint match is verified

## What Is NOT Collected

- ❌ File and folder names
- ❌ Disk contents
- ❌ User data
- ❌ Passwords and keys
- ❌ Network activity
- ❌ Geolocation

## Data Transmission

- Data is **NOT shared** with third parties
- Data is stored **only locally** on your device
- Data is used **exclusively** for installation binding

## If You Do Not Consent

You can decline hardware identifier collection. In this case, a **basic fingerprint** (hostname + MAC address + installation path) will be used, which is less stable and may change when:
- Renaming the computer
- Changing the network card
- Moving the starter folder

## Contact

For privacy questions, contact: support@myidon.site

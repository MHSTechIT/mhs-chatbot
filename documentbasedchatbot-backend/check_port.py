#!/usr/bin/env python3
"""Check what process is using port 9000."""

import socket
import subprocess
import sys

def check_port(port=9000):
    """Check if a port is in use."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('127.0.0.1', port))
    sock.close()

    if result == 0:
        print(f"[IN USE] Port {port} is ALREADY IN USE")
        print(f"\nFinding process using port {port}...")
        try:
            # This works on Windows
            output = subprocess.check_output(
                f'netstat -ano | findstr ":{port}"',
                shell=True,
                text=True
            )
            print("\nNetstat output:")
            print(output)
            print("\nTo kill the process, run:")
            print("  taskkill /PID <PID> /F")
            print("\nOr restart your computer.")
        except Exception as e:
            print(f"Could not find process: {e}")
        return False
    else:
        print(f"[OK] Port {port} is available")
        return True

if __name__ == "__main__":
    if check_port():
        print("\nYou can start the backend server now.")
    else:
        print("\n" + "="*60)
        print("ACTION REQUIRED: Kill the process using port 9000")
        print("="*60)

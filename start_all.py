#!/usr/bin/env python3
import subprocess
import time
import os
import sys
from pathlib import Path

# Change to project directory
project_root = Path(__file__).parent
os.chdir(project_root)

print("=" * 60)
print("Starting Document-Based Chatbot Services...")
print("=" * 60)

# Ports configuration
BACKEND_PORT = 8004
FRONTEND_PORT = 5173

print(f"\n[1/2] Starting Backend on port {BACKEND_PORT}...")
print("-" * 60)

# Start backend
backend_process = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "main:app",
     f"--host", "0.0.0.0",
     f"--port", str(BACKEND_PORT),
     "--no-access-log"],
    cwd=str(project_root / "documentbasedchatbot-backend"),
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

print(f"✓ Backend process started (PID: {backend_process.pid})")
time.sleep(3)

print(f"\n[2/2] Starting Frontend on port {FRONTEND_PORT}...")
print("-" * 60)

# Start frontend
frontend_process = subprocess.Popen(
    [sys.executable, "-m", "pip", "show", "vite"],  # Check if vite is available
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE
)

# For frontend, we need npm
frontend_process = subprocess.Popen(
    ["npm", "run", "dev"],
    cwd=str(project_root / "documentbasedchatbot-frontend"),
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

print(f"✓ Frontend process started (PID: {frontend_process.pid})")
time.sleep(5)

print("\n" + "=" * 60)
print("SERVICES RUNNING!")
print("=" * 60)
print(f"\n🔗 Frontend:  http://localhost:{FRONTEND_PORT}")
print(f"🔗 Backend:   http://localhost:{BACKEND_PORT}")
print(f"📚 API Docs:  http://localhost:{BACKEND_PORT}/docs")
print("\n" + "=" * 60)

print("\nWaiting for services to stabilize... (Press Ctrl+C to stop all services)")
print("=" * 60 + "\n")

try:
    # Keep the script running
    while True:
        # Check if processes are still running
        if backend_process.poll() is not None:
            print(f"\n⚠️  Backend process died (exit code: {backend_process.poll()})")
            # Print any output
            stdout, stderr = backend_process.communicate()
            if stderr:
                print("Backend error:", stderr[:500])

        if frontend_process.poll() is not None:
            print(f"\n⚠️  Frontend process died (exit code: {frontend_process.poll()})")
            stdout, stderr = frontend_process.communicate()
            if stderr:
                print("Frontend error:", stderr[:500])

        time.sleep(2)
except KeyboardInterrupt:
    print("\n\n🛑 Shutting down services...")
    backend_process.terminate()
    frontend_process.terminate()

    # Wait for graceful shutdown
    try:
        backend_process.wait(timeout=5)
        frontend_process.wait(timeout=5)
        print("✓ Services stopped cleanly")
    except subprocess.TimeoutExpired:
        print("⚠️  Forcing shutdown...")
        backend_process.kill()
        frontend_process.kill()
        backend_process.wait()
        frontend_process.wait()
        print("✓ Services force-stopped")

    sys.exit(0)

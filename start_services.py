"""
Startup script to run the unified backend system with integrated LangGraph.

Run: python start_services.py
"""

import subprocess
import time
import sys
import os
from pathlib import Path

# Project root
PROJECT_ROOT = Path(__file__).parent

# Service configuration
SERVICE = {
    "name": "Backend API (with LangGraph)",
    "cwd": PROJECT_ROOT / "backend",
    "command": ["uvicorn", "app.main:app", "--reload", "--port", "8000"],
    "port": 8000,
    "url": "http://localhost:8000/health",
}


def check_port_available(port: int) -> bool:
    """Check if a port is already in use."""
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('127.0.0.1', port))
            return True
    except OSError:
        return False


def start_services():
    """Start the backend service."""
    print("=" * 60)
    print("Starting Beauty Shop Backend System")
    print("(with integrated LangGraph chat)")
    print("=" * 60)
    print()
    
    name = SERVICE["name"]
    cwd = SERVICE["cwd"]
    command = SERVICE["command"]
    port = SERVICE["port"]
    
    # Check if port is available
    if not check_port_available(port):
        print(f"✗ Port {port} is already in use")
        print(f"  Stop the service using port {port} first")
        return False
    
    print(f"Starting {name} on port {port}...")
    
    try:
        process = subprocess.Popen(
            command,
            cwd=str(cwd),
            stdout=None,
            stderr=None,
        )
        print(f"✓ Service started (PID: {process.pid})")
    except Exception as e:
        print(f"✗ Error starting service: {e}")
        return False
    
    print()
    print("=" * 60)
    print("✓ Backend running!")
    print("=" * 60)
    print()
    print("API URLs:")
    print("  Backend:       http://localhost:8000")
    print("  API Docs:      http://localhost:8000/docs")
    print("  Chat endpoint: POST http://localhost:8000/api/chat")
    print("  Health:        http://localhost:8000/health")
    print()
    print("All services integrated in one API!")
    print("Press Ctrl+C to stop")
    print()
    
    try:
        # Monitor process
        while True:
            if process.poll() is not None:
                print(f"✗ Service exited with code {process.returncode}")
                return False
            
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n" + "=" * 60)
        print("Shutting down service...")
        print("=" * 60)
        
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        
        print("✓ Service stopped")
        return True


if __name__ == "__main__":
    success = start_services()
    sys.exit(0 if success else 1)

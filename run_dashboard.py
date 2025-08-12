#!/usr/bin/env python3
import subprocess
import sys
import os

print("🏫 Starting EduMap Kenya Dashboard...")

if not os.path.exists("EduMap_FINAL.csv"):
    print("❌ EduMap_FINAL.csv not found!")
    print("Please ensure the data file is in this directory.")
    exit(1)

print("✅ Data file found")
print("🚀 Opening dashboard at http://localhost:8501")
print("Press Ctrl+C to stop")

try:
    subprocess.run([sys.executable, "-m", "streamlit", "run", "edumap_comprehensive_dashboard.py"])
except KeyboardInterrupt:
    print("\n👋 Dashboard stopped")
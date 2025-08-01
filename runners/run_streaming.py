# runners/run_streaming.py

import os
import sys

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from data.collector import start_streaming

if __name__ == "__main__":
    start_streaming()
    input("🛑 Press Enter to stop...\n")

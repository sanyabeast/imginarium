#!/usr/bin/env python
"""
Universal wrapper script for running Python scripts with proper encoding handling.
This wrapper ensures UTF-8 encoding for all I/O operations and handles encoding errors gracefully.

Usage:
    python run_script.py <script_name> [arguments...]
    
Example:
    python run_script.py generate.py --num 5 --workflow flux_dev
    python run_script.py db.py --trim
    python run_script.py search.py --tags "landscape, photorealistic"
"""

import sys
import os
import subprocess
import argparse
import re
import time
import threading

def clean_text(text):
    """Remove non-ASCII characters from text."""
    return ''.join(c if ord(c) < 128 else ' ' for c in text)

def parse_args():
    parser = argparse.ArgumentParser(
        description="Run a Python script with proper encoding handling"
    )
    parser.add_argument(
        "script", 
        help="The Python script to run (e.g., generate.py, db.py, search.py)"
    )
    parser.add_argument(
        "args", 
        nargs=argparse.REMAINDER,
        help="Arguments to pass to the script"
    )
    parser.add_argument(
        "--raw", 
        action="store_true",
        help="Don't filter non-ASCII characters"
    )
    return parser.parse_args()

class OutputFilter:
    """Filter to clean non-ASCII characters from output."""
    
    def __init__(self, original_stream, raw=False):
        self.original_stream = original_stream
        self.raw = raw
    
    def write(self, text):
        if not self.raw:
            cleaned_text = clean_text(text)
            self.original_stream.write(cleaned_text)
        else:
            self.original_stream.write(text)
    
    def flush(self):
        self.original_stream.flush()
    
    def isatty(self):
        return hasattr(self.original_stream, 'isatty') and self.original_stream.isatty()

def stream_output(process, raw=False):
    """Stream output from the process to stdout in a non-blocking way."""
    def read_stream():
        for line in iter(process.stdout.readline, ''):
            if not raw:
                line = clean_text(line)
            sys.stdout.write(line)
            sys.stdout.flush()
    
    # Start a thread to read the output
    thread = threading.Thread(target=read_stream)
    thread.daemon = True
    thread.start()
    return thread

def main():
    # Parse command line arguments
    args = parse_args()
    
    # Ensure the script exists
    if not os.path.exists(args.script):
        print(f"Error: Script '{args.script}' not found.")
        sys.exit(1)
    
    # Ensure UTF-8 encoding for all I/O operations
    if sys.stdout.encoding != 'utf-8':
        os.environ['PYTHONIOENCODING'] = 'utf-8'
    
    # Replace stdout with our filtered version
    if not args.raw:
        sys.stdout = OutputFilter(sys.stdout)
        sys.stderr = OutputFilter(sys.stderr)
    
    # Construct the command to run the script
    cmd = [sys.executable, args.script] + args.args
    
    print(f"Running: {' '.join(cmd)}")
    
    try:
        # Run the script with proper encoding settings
        process = subprocess.Popen(
            cmd,
            text=True,
            encoding='utf-8',
            errors='replace',
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,  # Line buffered for real-time output
            universal_newlines=True,
        )
        
        # Stream the output in a non-blocking way
        output_thread = stream_output(process, args.raw)
        
        # Wait for process to complete
        while process.poll() is None:
            time.sleep(0.1)  # Small sleep to avoid CPU hogging
        
        # Make sure we've read all the output
        output_thread.join(timeout=2.0)
        
        # Get any remaining output
        remaining_output = process.stdout.read()
        if remaining_output:
            if not args.raw:
                remaining_output = clean_text(remaining_output)
            sys.stdout.write(remaining_output)
            sys.stdout.flush()
        
        # Return the same exit code
        sys.exit(process.returncode)
    except KeyboardInterrupt:
        print("\nProcess interrupted by user.")
        sys.exit(130)  # Standard exit code for SIGINT
    except Exception as e:
        print(f"Error running {args.script}: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

import os
import sys
import subprocess
import time

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.link import TCLink


def enforce_executable():
    scripts = [
        "run_experiment.py",
        "server.py",
        "client.py",
        "nagle.py"
    ]
    for script in scripts:
        os.system(f"chmod +x {script}")
    print("Set execute permissions on all scripts")

def set_results_directory():
    dir_path = "results"
    os.makedirs(dir_path, exist_ok=True)
    print(f"Results directory ensured: {dir_path}")
    return dir_path

def run_tcp_experiment():
    print("Initiating TCP/IP test with Nagle and Delayed ACK configurations...")
    print("Testing four scenarios; estimated runtime: 8-10 minutes")
    print("Please wait...")
    cmd = ["sudo", "python3", "run_experiment.py"]
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError:
        print("✗ Test encountered errors. Check above messages.")
        return False
    # Update directory permissions on results
    os.system("sudo chown -R $USER:$USER results")
    return True

def show_outcomes():
    outcome_file = "results/analysis.txt"
    if os.path.isfile(outcome_file):
        with open(outcome_file, 'r') as f:
            print("\n" + "="*80)
            print("EXPERIMENT OUTCOMES:")
            print("="*80)
            print(f.read())
    else:
        print("✗ Outcome file missing. Experiment may have failed.")

def main():
    print("=" * 80)
    print("TCP/IP Performance Analysis: Nagle & Delayed ACK Evaluation")
    print("=" * 80)
    
    
    enforce_executable()
    set_results_directory()
    
    if run_tcp_experiment():
        show_outcomes()

if __name__ == "__main__":
    main()

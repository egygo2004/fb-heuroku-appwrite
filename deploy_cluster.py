import os
import subprocess
import time

# Configuration
TOTAL_NODES = 10
BASE_APP = "fb-mob-bot"

def run_cmd(cmd, shell=True):
    try:
        result = subprocess.run(cmd, shell=shell, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        return None

def main():
    print(f"Starting Cluster Deployment (Target: {TOTAL_NODES} nodes)")
    
    # 1. Update Main Node
    print("\n--- Deploying to Main Node (fb-mob-bot) ---")
    run_cmd("git push heroku main:master")
    print("Main node deployed.")

    # 2. Update Worker Nodes
    for i in range(2, TOTAL_NODES + 1):
        app_name = f"{BASE_APP}-{i}"
        remote_name = f"heroku-{i}"
        print(f"\n--- Deploying to Node {i}: {app_name} ---")
        
        # Ensure remote exists (idempotent)
        run_cmd(f"git remote add {remote_name} https://git.heroku.com/{app_name}.git")
        
        # Push
        print(f"Pushing to {remote_name}...")
        res = run_cmd(f"git push {remote_name} main:master")
        if res:
            print("Success.")
        
        # Sleep slightly to prevent git race/rate limits locally?
        time.sleep(1)

    print("\n\nCluster Deployment Complete! 🚀")

if __name__ == "__main__":
    main()

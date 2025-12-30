import subprocess
import re

BASE_APP = "fb-mob-bot"
TOTAL_NODES = 10

def check_app(app_name):
    try:
        # Run heroku ps
        result = subprocess.run(
            f"heroku ps -a {app_name}", 
            shell=True, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            text=True
        )
        output = result.stdout
        
        # Check for worker.1 up
        if "worker.1: up" in output:
            return "✅ UP"
        elif "worker.1: crashed" in output:
            return "❌ CRASHED"
        elif "No dynos on" in output:
            return "⚠️  SCALED DOWN (0)"
        else:
            return f"❓ UNKNOWN STATE\n{output[:100]}..."
            
    except Exception as e:
        return f"Error: {str(e)}"

def main():
    print(f"Checking status for {TOTAL_NODES} nodes...\n")
    
    for i in range(1, TOTAL_NODES + 1):
        if i == 1:
            app_name = BASE_APP
        else:
            app_name = f"{BASE_APP}-{i}"
            
        status = check_app(app_name)
        print(f"Node {i} ({app_name}): {status}")

if __name__ == "__main__":
    main()

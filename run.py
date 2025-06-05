import subprocess
import sys
import os
import webbrowser
import threading

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Define host and port
host = "localhost"
port = "8502"
url = f"http://{host}:{port}"

# Open the browser after a short delay to make sure the server is up
def open_browser():
    import time
    time.sleep(2)
    webbrowser.open(url)

# Start browser thread
threading.Thread(target=open_browser).start()

# Run Streamlit without auto-opening browser
subprocess.run([
    sys.executable, "-m", "streamlit", "run", "app/main.py",
    "--server.address", host,
    "--server.port", port,
    "--server.headless", "true"
])

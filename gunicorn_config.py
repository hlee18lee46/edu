# gunicorn_config.py
import os
import multiprocessing

# Bind to the dynamic port DigitalOcean provides (default 8080)
bind = f"0.0.0.0:{os.getenv('PORT', '8080')}"

# Use one worker per CPU core, up to a reasonable limit
workers = min(4, multiprocessing.cpu_count())

# Optional: handle short-lived requests better on small instances
threads = 2

# Set a reasonable timeout (in seconds)
timeout = 120

# Preload the app for slightly faster worker startup
preload_app = True

# Keep temp files in shared memory to avoid /tmp I/O
worker_tmp_dir = "/dev/shm"

# Optional: log config
accesslog = "-"
errorlog = "-"
loglevel = "info"

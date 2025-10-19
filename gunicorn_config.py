import os
bind = f"0.0.0.0:{os.getenv('PORT', '8080')}"
workers = 3
timeout = 120
preload_app = True
worker_tmp_dir = "/dev/shm"

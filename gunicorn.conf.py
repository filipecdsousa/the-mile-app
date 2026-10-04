import os

bind = '0.0.0.0:' + os.environ.get('PORT', '8000')
workers = 1
threads = 4
timeout = 60
accesslog = None  # Never log activation links or document titles in URLs.
errorlog = '-'


#!/usr/bin/env python3
import os,sys

sys.path.append('../')
sys.path.insert(0, os.getcwd())
from swagger_server.app import app
from swagger_server import constants
flo_env = os.environ.get(constants.ENV_NAME)


if __name__ == '__main__':
    if flo_env == "local":
        app.run(port=8087,debug=True)
    else:
        app.run(port=80)

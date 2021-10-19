#!/bin/bash

# Start the first process
#./my_first_process -D
nohup /usr/share/filebeat/bin/filebeat -c /etc/filebeat/filebeat.yml -path.home /usr/share/filebeat -path.config /etc/filebeat -path.data /var/lib/filebeat -path.logs /var/log/filebeat &

status=$?
if [ $status -ne 0 ]; then
  echo "Failed to start filebeat : $status"
  exit $status
fi

# Start the second process
python36 -m swagger_server
status=$?
if [ $status -ne 0 ]; then
  echo "Failed to start swagger server : $status"
  exit $status
fi


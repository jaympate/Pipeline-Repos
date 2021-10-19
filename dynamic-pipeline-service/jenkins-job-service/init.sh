#!/bin/bash
echo "initializing"


if [ -z $APP_ENV ] ; then
	echo "ERROR:APP_ENV env variable is not set exiting"
	exit
fi
echo "APP_ENV is $APP_ENV"

cp conf/${APP_ENV}/filebeat.yml /etc/filebeat/filebeat.yml
if [ "$?" != "0" ]; then
	echo "ERROR: failed copy filebeat.yml"
	exit 1
fi

cp conf/${APP_ENV}/supervisord.conf /etc/supervisord.conf
if [ "$?" != "0" ]; then
        echo "ERROR: failed copy supervisord.conf"
        exit 1
fi
mkdir -p /var/log/supervisord/
echo "starting supervisord"
/usr/bin/supervisord -c /etc/supervisord.conf

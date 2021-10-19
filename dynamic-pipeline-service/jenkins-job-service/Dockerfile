FROM nexus.company.com:8090/verified/baseimage_python3.7:v5

MAINTAINER dynamic-pipeline_Dev@company.com

ARG NEXUS_HOST=nexus.company.com
ARG App_path=/usr/src/app
ARG pip_path=/usr/local/bin/pip3.7

#Copying all dependent files to image

RUN mkdir -p $App_path
COPY . $App_path

WORKDIR $App_path

COPY swagger_server.conf /etc/httpd/conf.d
RUN rm -rf swagger_server.conf

COPY httpd.conf /etc/httpd/conf
RUN rm -rf httpd.conf

RUN   echo "LoadModule wsgi_module modules/mod_wsgi.so" >> /etc/httpd/conf.modules.d/dynamic-pipeline-wsgi.conf

RUN $pip_path install --index-url  https://$NEXUS_HOST/repository/pypi-repo/simple  --no-cache-dir -r requirements.txt

RUN mkdir -p /var/log/dynamic-pipeline && \
    chown  -R apache:apache /var/log/dynamic-pipeline && \
    chmod u+rwx /var/log/dynamic-pipeline

RUN chown -R apache:apache /etc/ && \
    chown -R apache:apache /var/log/

RUN mkdir -p /var/lib/filebeat && \
    chown -R apache:apache /var/lib/filebeat

EXPOSE  8000

RUN chmod -R a+rwx /var/run && \
    chown -R apache:apache /var/run

RUN chmod u+x init.sh
USER apache

CMD ["sh","/usr/src/app/init.sh"]

FROM alpine:3.5
RUN apk add --no-cache --update sudo bash git py-lxml py2-yaml py-setuptools libxslt-dev gcc python-dev libxml2-dev musl-dev && \
    easy_install-2.7 --always-unzip https://github.com/containers-tools/cct/archive/master.zip && \
    apk del libxslt-dev gcc python-dev libxml2-dev musl-dev

# Color the git output by default
RUN git config --global color.ui true
# Set default value for the user name
RUN git config --global user.name "dogen"
# Set default value for the user email address
RUN git config --global user.email "dogen@jboss.org"

COPY requirements.txt setup.py launch.sh README.rst /tmp/dogen/
COPY dogen /tmp/dogen/dogen

RUN cd /tmp/dogen && cp launch.sh / && easy_install-2.7 .

ENTRYPOINT ["/launch.sh"]

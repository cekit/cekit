FROM alpine:3.3
RUN apk add --update sudo bash py-setuptools git && rm -rf /var/cache/apk/*

ENV DOGEN_VERSION 2.0.0rc2

# Color the git output by default
RUN git config --global color.ui true
# Set default value for the user name
RUN git config --global user.name "dogen"
# Set default value for the user email address
RUN git config --global user.email "dogen@jboss.org"

RUN easy_install-2.7 https://github.com/jboss-dockerfiles/dogen/archive/$DOGEN_VERSION.zip

ADD launch.sh /

ENTRYPOINT ["/launch.sh"]

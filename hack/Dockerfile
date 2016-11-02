FROM alpine:3.3
RUN apk add --update sudo bash py-setuptools git && rm -rf /var/cache/apk/*

ENV DOGEN_VERSION master

# Color the git output by default
RUN git config --global color.ui true
# Set default value for the user name
RUN git config --global user.name "dogen"
# Set default value for the user email address
RUN git config --global user.email "dogen@jboss.org"

ADD dogen.tar /tmp/dogen

RUN cd /tmp/dogen && tar xf dogen.tar && easy_install-2.7 . && cp launch.sh /launch.sh

ENTRYPOINT ["/launch.sh"]

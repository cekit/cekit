FROM centos:7

ENV HOME="/home/dogen"

RUN mkdir -p /home/dogen
WORKDIR /home/dogen

# Add required files
RUN yum -y install python-setuptools git && yum clean all

# Color the git output by default
RUN git config --global color.ui true
# Set default value for the user name
RUN git config --global user.name "DoGen"
# Set default value for the user email address
RUN git config --global user.email "dogen@jboss.org"

ADD dogen $HOME/dogen/
ADD requirements.txt setup.py LICENSE README.rst MANIFEST.in $HOME/

RUN easy_install --user .

ENTRYPOINT ["/home/dogen/.local/bin/dogen"]
CMD ["--scripts", "/scripts", "/input/image.yaml", "/output"]

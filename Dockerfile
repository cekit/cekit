FROM centos:7

RUN mkdir /opt/dogen
WORKDIR /opt/dogen

# Install required pacakges
RUN yum -y install python-setuptools git && yum clean all

# Color the git output by default
RUN git config --global color.ui true
# Set default value for the user name
RUN git config --global user.name "dogen"
# Set default value for the user email address
RUN git config --global user.email "dogen@jboss.org"

ADD dogen /opt/dogen/dogen/
ADD launch.sh requirements.txt setup.py LICENSE README.rst MANIFEST.in /opt/dogen/

RUN easy_install .

ENTRYPOINT ["/opt/dogen/launch.sh"]

FROM fedora:23

RUN mkdir /opt/dogen
WORKDIR /opt/dogen

# Install required pacakges
RUN dnf -y install python-pip git && dnf clean all

# Color the git output by default
RUN git config --global color.ui true
# Set default value for the user name
RUN git config --global user.name "dogen"
# Set default value for the user email address
RUN git config --global user.email "dogen@jboss.org"

ADD dogen /opt/dogen/dogen/
ADD launch.sh requirements.txt setup.py LICENSE README.rst MANIFEST.in /opt/dogen/

RUN pip install .

ENTRYPOINT ["/opt/dogen/launch.sh"]

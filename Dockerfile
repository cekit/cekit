FROM centos:7

ENV HOME="/home/dogen"

# Create a user to run the generator as
RUN groupadd -r dogen -g 1000 && useradd -u 1000 -r -g dogen -m -d $HOME -s /sbin/nologin dogen

# Add required files
RUN yum -y install python-setuptools git && yum clean all

WORKDIR /home/dogen

ADD dogen $HOME/dogen/
ADD requirements.txt setup.py LICENSE README.rst MANIFEST.in $HOME/
RUN chown dogen:dogen $HOME -R

USER dogen

RUN easy_install --user .

# Color the git output by default
RUN git config --global color.ui true
# Set default value for the user name
RUN git config --global user.name "DoGen"
# Set default value for the user email address
RUN git config --global user.email "dogen@jboss.org"

ENTRYPOINT ["/home/dogen/.local/bin/dogen"]
CMD ["--scripts", "/scripts", "/input/image.yaml", "/output"]

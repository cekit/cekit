FROM centos:7

ENV HOME="/home/dogen"

# Create a user to run the generator as
RUN groupadd -r dogen -g 1000 && useradd -u 1000 -r -g dogen -m -d $HOME -s /sbin/nologin dogen

# Add required files
RUN yum -y install python-setuptools && yum clean all

WORKDIR /home/dogen

ADD dogen $HOME/dogen/
ADD requirements.txt setup.py LICENSE README.rst MANIFEST.in $HOME/
RUN chown dogen:dogen $HOME -R

USER dogen

RUN easy_install --user .

ENTRYPOINT ["/home/dogen/.local/bin/dogen"]
CMD ["--scripts", "/scripts", "/input/image.yaml", "/output"]

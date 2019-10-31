FROM python:3.7
LABEL maintainer="ktower@uw.edu"
LABEL description="A container with the OpenStack CLI tools and Python shade libraries installed"
LABEL version "20191011"
COPY requirements.txt .

RUN pip install -r requirements.txt

CMD [ "openstack" ]
FROM hyperledger/fabric-tools:1.4.3

# Install kubectl, curl and netcat
RUN apt-get update && \
  apt-get install -y curl netcat apt-transport-https vim && \
  curl -s https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add - && \
  echo "deb https://apt.kubernetes.io/ kubernetes-xenial main" | tee -a /etc/apt/sources.list.d/kubernetes.list && \
  apt-get update && \
  apt-get install -y kubectl

# Install grpcurl for convenience
RUN wget https://github.com/fullstorydev/grpcurl/releases/download/v1.3.0/grpcurl_1.3.0_linux_x86_64.tar.gz && \
  tar xvzf grpcurl_1.3.0_linux_x86_64.tar.gz && \
  mv grpcurl /bin

COPY ./setup-hfc-binaries.sh .

RUN ./setup-hfc-binaries.sh

COPY ./bin/* /usr/local/bin/

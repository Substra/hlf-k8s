FROM hyperledger/fabric-tools:2.2.1

# Install curl and netcat
RUN apk update && \
  apk add curl vim

# Install kubectl
RUN curl -LO https://storage.googleapis.com/kubernetes-release/release/v1.16.6/bin/linux/amd64/kubectl && \
  chmod +x ./kubectl && \
  mv ./kubectl /bin

# Install grpcurl for convenience
RUN wget https://github.com/fullstorydev/grpcurl/releases/download/v1.3.0/grpcurl_1.3.0_linux_x86_64.tar.gz && \
  tar xvzf grpcurl_1.3.0_linux_x86_64.tar.gz && \
  mv grpcurl /bin

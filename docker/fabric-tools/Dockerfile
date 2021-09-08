FROM hyperledger/fabric-tools:2.4

# Install curl and netcat
RUN apk update && \
  apk add curl netcat-openbsd vim libc6-compat

# Install fabric-ca-client
RUN curl -SL https://github.com/hyperledger/fabric-ca/releases/download/v1.5.1/hyperledger-fabric-ca-linux-amd64-1.5.1.tar.gz | tar xz --strip-components=1 && \
  mv ./fabric-ca-client /bin

# Install kubectl
RUN curl -LO https://storage.googleapis.com/kubernetes-release/release/v1.16.6/bin/linux/amd64/kubectl && \
  chmod +x ./kubectl && \
  mv ./kubectl /bin

# Install grpcurl for convenience
RUN wget https://github.com/fullstorydev/grpcurl/releases/download/v1.3.0/grpcurl_1.3.0_linux_x86_64.tar.gz && \
  tar xvzf grpcurl_1.3.0_linux_x86_64.tar.gz && \
  mv grpcurl /bin

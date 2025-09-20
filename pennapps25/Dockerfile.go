FROM codercom/code-server:latest

# Switch to root to install packages
USER root

# Install Go, Python, and development tools
RUN apt-get update && \
    apt-get install -y \
    golang-go \
    python3 \
    python3-pip \
    git \
    curl \
    wget \
    vim \
    nano \
    htop \
    tree \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create symlinks for convenience
RUN ln -s /usr/bin/python3 /usr/bin/python

# Set Go environment
ENV GOPATH=/home/coder/go
ENV PATH=$GOPATH/bin:/usr/local/go/bin:$PATH

# Create Go workspace
RUN mkdir -p /home/coder/go/src /home/coder/go/bin /home/coder/go/pkg

# Switch back to coder user
USER coder

# Set working directory
WORKDIR /home/coder/workspace

# Expose port
EXPOSE 8080

# Start code-server
CMD ["code-server", "--bind-addr", "0.0.0.0:8080", "--auth", "password", "/home/coder/workspace"]

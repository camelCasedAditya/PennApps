FROM codercom/code-server:latest

# Switch to root to install packages
USER root

# Install Java, Maven, Gradle, and development tools
RUN apt-get update && \
    apt-get install -y \
    openjdk-17-jdk \
    maven \
    gradle \
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

# Set JAVA_HOME
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ENV PATH=$JAVA_HOME/bin:$PATH

# Switch back to coder user
USER coder

# Set working directory
WORKDIR /home/coder/workspace

# Expose port
EXPOSE 8080

# Start code-server
CMD ["code-server", "--bind-addr", "0.0.0.0:8080", "--auth", "password", "/home/coder/workspace"]

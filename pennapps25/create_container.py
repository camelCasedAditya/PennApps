#!/usr/bin/env python3
"""
Docker Container Workspace Creator

This script creates development workspaces with appropriate Docker configurations
for different programming languages.
"""

import os
import sys
import shutil
from pathlib import Path
from workspace_functions import (
    create_workspace_directory,
    create_dockerfile,
    create_docker_compose,
    create_sample_files,
    create_start_script
)

# Docker file templates for different languages
DOCKER_TEMPLATES = {
    "python": """FROM codercom/code-server:latest

# Switch to root to install packages
USER root

# Install Python and development tools
RUN apt-get update && \\
    apt-get install -y \\
    python3 \\
    python3-pip \\
    python3-venv \\
    git \\
    curl \\
    wget \\
    vim \\
    nano \\
    htop \\
    tree \\
    && rm -rf /var/lib/apt/lists/*

# Create symlink for python command
RUN ln -s /usr/bin/python3 /usr/bin/python

# Switch back to coder user
USER coder

# Set working directory
WORKDIR /home/coder/workspace

# Expose port
EXPOSE 8080

# Start code-server
CMD ["code-server", "--bind-addr", "0.0.0.0:8080", "--auth", "password", "/home/coder/workspace"]
""",

    "nodejs": """FROM codercom/code-server:latest

# Switch to root to install packages
USER root

# Install Node.js, Python, and development tools
RUN apt-get update && \\
    curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && \\
    apt-get install -y \\
    nodejs \\
    python3 \\
    python3-pip \\
    python3-venv \\
    git \\
    curl \\
    wget \\
    vim \\
    nano \\
    htop \\
    tree \\
    build-essential \\
    && rm -rf /var/lib/apt/lists/*

# Create symlinks for convenience
RUN ln -s /usr/bin/python3 /usr/bin/python

# Install global npm packages
RUN npm install -g yarn pnpm typescript ts-node nodemon

# Switch back to coder user
USER coder

# Set working directory
WORKDIR /home/coder/workspace

# Expose port
EXPOSE 8080

# Start code-server
CMD ["code-server", "--bind-addr", "0.0.0.0:8080", "--auth", "password", "/home/coder/workspace"]
""",

    "java": """FROM codercom/code-server:latest

# Switch to root to install packages
USER root

# Install Java, Maven, Gradle, and development tools
RUN apt-get update && \\
    apt-get install -y \\
    openjdk-17-jdk \\
    maven \\
    gradle \\
    python3 \\
    python3-pip \\
    git \\
    curl \\
    wget \\
    vim \\
    nano \\
    htop \\
    tree \\
    build-essential \\
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
""",

    "go": """FROM codercom/code-server:latest

# Switch to root to install packages
USER root

# Install Go, Python, and development tools
RUN apt-get update && \\
    apt-get install -y \\
    golang-go \\
    python3 \\
    python3-pip \\
    git \\
    curl \\
    wget \\
    vim \\
    nano \\
    htop \\
    tree \\
    build-essential \\
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
""",

    "rust": """FROM codercom/code-server:latest

# Switch to root to install packages
USER root

# Install Rust, Python, and development tools
RUN apt-get update && \\
    apt-get install -y \\
    python3 \\
    python3-pip \\
    git \\
    curl \\
    wget \\
    vim \\
    nano \\
    htop \\
    tree \\
    build-essential \\
    && rm -rf /var/lib/apt/lists/*

# Install Rust
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# Create symlinks for convenience
RUN ln -s /usr/bin/python3 /usr/bin/python

# Switch back to coder user
USER coder

# Set working directory
WORKDIR /home/coder/workspace

# Expose port
EXPOSE 8080

# Start code-server
CMD ["code-server", "--bind-addr", "0.0.0.0:8080", "--auth", "password", "/home/coder/workspace"]
"""
}

# Language configurations with port mappings
LANGUAGE_CONFIG = {
    "python": {"port": 8080, "dockerfile": "Dockerfile.python"},
    "nodejs": {"port": 8081, "dockerfile": "Dockerfile.nodejs"},
    "java": {"port": 8082, "dockerfile": "Dockerfile.java"},
    "go": {"port": 8083, "dockerfile": "Dockerfile.go"},
    "rust": {"port": 8084, "dockerfile": "Dockerfile.rust"}
}

def show_language_options():
    """Display available language options to the user"""
    print("\n🚀 Available Languages:")
    print("=" * 40)
    for i, (lang, config) in enumerate(LANGUAGE_CONFIG.items(), 1):
        print(f"{i}. {lang.title()} (Port: {config['port']})")
    print("=" * 40)

def get_language_choice():
    """Get and validate language choice from user"""
    while True:
        show_language_options()
        try:
            choice = input("\nSelect a language (1-5 or name): ").strip().lower()
            
            # Handle numeric input
            if choice.isdigit():
                choice_num = int(choice)
                if 1 <= choice_num <= len(LANGUAGE_CONFIG):
                    language = list(LANGUAGE_CONFIG.keys())[choice_num - 1]
                    return language
                else:
                    print(f"❌ Please enter a number between 1 and {len(LANGUAGE_CONFIG)}")
                    continue
            
            # Handle language name input
            if choice in LANGUAGE_CONFIG:
                return choice
            
            # Handle common aliases
            aliases = {
                "js": "nodejs",
                "javascript": "nodejs",
                "node": "nodejs",
                "py": "python",
                "golang": "go"
            }
            
            if choice in aliases:
                return aliases[choice]
            
            print(f"❌ Invalid choice: '{choice}'. Please try again.")
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            sys.exit(0)
        except Exception as e:
            print(f"❌ Error: {e}. Please try again.")

def get_workspace_name():
    """Get and validate workspace name from user"""
    while True:
        try:
            workspace_name = input("\n📁 Enter workspace name: ").strip()
            
            if not workspace_name:
                print("❌ Workspace name cannot be empty!")
                continue
            
            # Validate workspace name (no special characters except hyphens and underscores)
            if not workspace_name.replace('-', '').replace('_', '').replace('.', '').isalnum():
                print("❌ Workspace name can only contain letters, numbers, hyphens, underscores, and dots!")
                continue
            
            # Check if workspace already exists
            workspace_path = Path(f"workspace-{workspace_name}")
            if workspace_path.exists():
                overwrite = input(f"⚠️  Workspace '{workspace_name}' already exists. Overwrite? (y/N): ").strip().lower()
                if overwrite not in ['y', 'yes']:
                    continue
            
            return workspace_name
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            sys.exit(0)
        except Exception as e:
            print(f"❌ Error: {e}. Please try again.")
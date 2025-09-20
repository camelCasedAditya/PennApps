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

def create_workspace_directory(workspace_name):
    """Create workspace directory and basic files"""
    workspace_path = Path(f"workspace-{workspace_name}")
    
    # Remove existing workspace if it exists
    if workspace_path.exists():
        shutil.rmtree(workspace_path)
    
    # Create workspace directory
    workspace_path.mkdir(exist_ok=True)
    print(f"📁 Created workspace directory: {workspace_path}")
    
    return workspace_path

def create_dockerfile(language, workspace_name):
    """Create Dockerfile for the specified language"""
    dockerfile_path = Path(f"Dockerfile.{workspace_name}")
    
    with open(dockerfile_path, 'w') as f:
        f.write(DOCKER_TEMPLATES[language])
    
    print(f"🐳 Created Dockerfile: {dockerfile_path}")
    return dockerfile_path

def create_docker_compose(language, workspace_name):
    """Create docker-compose.yml for the workspace"""
    config = LANGUAGE_CONFIG[language]
    
    docker_compose_content = f"""version: '3.8'

services:
  {workspace_name}-editor:
    build:
      context: .
      dockerfile: Dockerfile.{workspace_name}
    container_name: {workspace_name}-code-editor
    ports:
      - "{config['port']}:8080"
    environment:
      - PASSWORD=password123
    volumes:
      - ./workspace-{workspace_name}:/home/coder/workspace
    restart: unless-stopped

volumes:
  {workspace_name}-config:
"""
    
    compose_path = Path(f"docker-compose.{workspace_name}.yml")
    with open(compose_path, 'w') as f:
        f.write(docker_compose_content)
    
    print(f"🐙 Created docker-compose file: {compose_path}")
    return compose_path

def create_sample_files(language, workspace_path):
    """Create sample files for the workspace based on language"""
    samples = {
        "python": {
            "main.py": '''#!/usr/bin/env python3
"""
Sample Python application
"""

def main():
    print("Hello from Python!")
    print("Your Python development environment is ready!")

if __name__ == "__main__":
    main()
''',
            "requirements.txt": '''# Python dependencies
# Add your required packages here
# Example:
# requests>=2.28.0
# numpy>=1.21.0
''',
            "README.md": '''# Python Workspace

This is a Python development workspace created automatically.

## Getting Started

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the sample application:
   ```bash
   python main.py
   ```

## Development

This workspace includes:
- Python 3
- pip and venv
- Common development tools

Happy coding! 🐍
'''
        },
        
        "nodejs": {
            "index.js": '''/**
 * Sample Node.js application
 */

console.log("Hello from Node.js!");
console.log("Your Node.js development environment is ready!");

// Example async function
async function greet(name = "Developer") {
    return `Welcome ${name}! 🚀`;
}

greet().then(console.log);
''',
            "package.json": '''{
  "name": "nodejs-workspace",
  "version": "1.0.0",
  "description": "Node.js development workspace",
  "main": "index.js",
  "scripts": {
    "start": "node index.js",
    "dev": "nodemon index.js"
  },
  "keywords": ["nodejs", "development"],
  "author": "Developer",
  "license": "MIT",
  "devDependencies": {
    "nodemon": "^3.0.0"
  }
}
''',
            "README.md": '''# Node.js Workspace

This is a Node.js development workspace created automatically.

## Getting Started

1. Install dependencies:
   ```bash
   npm install
   ```

2. Run the sample application:
   ```bash
   npm start
   ```

3. For development with auto-reload:
   ```bash
   npm run dev
   ```

## Development

This workspace includes:
- Node.js 18
- npm, yarn, and pnpm
- TypeScript and ts-node
- nodemon for development

Happy coding! 🚀
'''
        },
        
        "java": {
            "HelloWorld.java": '''/**
 * Sample Java application
 */
public class HelloWorld {
    public static void main(String[] args) {
        System.out.println("Hello from Java!");
        System.out.println("Your Java development environment is ready!");
        
        // Example method call
        greet("Developer");
    }
    
    public static void greet(String name) {
        System.out.println("Welcome " + name + "! ☕");
    }
}
''',
            "pom.xml": '''<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 
         http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>
    
    <groupId>com.example</groupId>
    <artifactId>java-workspace</artifactId>
    <version>1.0.0</version>
    <packaging>jar</packaging>
    
    <name>Java Workspace</name>
    <description>Java development workspace</description>
    
    <properties>
        <maven.compiler.source>17</maven.compiler.source>
        <maven.compiler.target>17</maven.compiler.target>
        <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
    </properties>
    
    <dependencies>
        <!-- Add your dependencies here -->
    </dependencies>
</project>
''',
            "README.md": '''# Java Workspace

This is a Java development workspace created automatically.

## Getting Started

1. Compile the application:
   ```bash
   javac HelloWorld.java
   ```

2. Run the application:
   ```bash
   java HelloWorld
   ```

### Using Maven

1. Build with Maven:
   ```bash
   mvn compile
   ```

2. Run with Maven:
   ```bash
   mvn exec:java -Dexec.mainClass="HelloWorld"
   ```

## Development

This workspace includes:
- OpenJDK 17
- Maven and Gradle
- Common development tools

Happy coding! ☕
'''
        },
        
        "go": {
            "main.go": '''package main

import "fmt"

func main() {
    fmt.Println("Hello from Go!")
    fmt.Println("Your Go development environment is ready!")
    
    // Example function call
    greet("Developer")
}

func greet(name string) {
    fmt.Printf("Welcome %s! 🐹\\n", name)
}
''',
            "go.mod": '''module workspace

go 1.21

// Add your dependencies here
// require (
//     github.com/gin-gonic/gin v1.9.1
// )
''',
            "README.md": '''# Go Workspace

This is a Go development workspace created automatically.

## Getting Started

1. Initialize Go module (if not done):
   ```bash
   go mod init workspace
   ```

2. Run the application:
   ```bash
   go run main.go
   ```

3. Build the application:
   ```bash
   go build -o app main.go
   ./app
   ```

## Development

This workspace includes:
- Go compiler and tools
- Full Go standard library
- Common development tools

Happy coding! 🐹
'''
        },
        
        "rust": {
            "main.rs": '''fn main() {
    println!("Hello from Rust!");
    println!("Your Rust development environment is ready!");
    
    // Example function call
    greet("Developer");
}

fn greet(name: &str) {
    println!("Welcome {}! 🦀", name);
}
''',
            "Cargo.toml": '''[package]
name = "rust-workspace"
version = "0.1.0"
edition = "2021"

[dependencies]
# Add your dependencies here
# serde = { version = "1.0", features = ["derive"] }
# tokio = { version = "1.0", features = ["full"] }
''',
            "README.md": '''# Rust Workspace

This is a Rust development workspace created automatically.

## Getting Started

1. Build the application:
   ```bash
   cargo build
   ```

2. Run the application:
   ```bash
   cargo run
   ```

3. Run tests:
   ```bash
   cargo test
   ```

## Development

This workspace includes:
- Rust compiler and Cargo
- Complete Rust toolchain
- Common development tools

Happy coding! 🦀
'''
        }
    }
    
    if language in samples:
        for filename, content in samples[language].items():
            file_path = workspace_path / filename
            with open(file_path, 'w') as f:
                f.write(content)
            print(f"📄 Created sample file: {file_path}")

def create_start_script(language, workspace_name):
    """Create a start script for the workspace"""
    config = LANGUAGE_CONFIG[language]
    
    start_script_content = f'''#!/bin/bash

# Start script for {workspace_name} ({language}) development environment

echo "🚀 Starting {workspace_name} development environment..."
echo "Language: {language.title()}"
echo "Port: {config['port']}"
echo "Workspace: workspace-{workspace_name}"
echo ""

# Build and start the container
docker-compose -f docker-compose.{workspace_name}.yml up --build -d

echo ""
echo "✅ Environment started successfully!"
echo "🌐 Access your development environment at: http://localhost:{config['port']}"
echo "🔑 Password: password123"
echo ""
echo "To stop the environment:"
echo "docker-compose -f docker-compose.{workspace_name}.yml down"
'''
    
    script_path = Path(f"start-{workspace_name}.sh")
    with open(script_path, 'w') as f:
        f.write(start_script_content)
    
    # Make script executable
    os.chmod(script_path, 0o755)
    
    print(f"🎬 Created start script: {script_path}")
    return script_path

def main():
    """Main program function"""
    print("🐳 Docker Container Workspace Creator")
    print("="*50)
    print("Create development workspaces with Docker support!")
    
    try:
        # Get user choices
        language = get_language_choice()
        workspace_name = get_workspace_name()
        
        print(f"\n🔨 Creating {language.title()} workspace: '{workspace_name}'")
        print("="*50)
        
        # Create workspace components
        workspace_path = create_workspace_directory(workspace_name)
        dockerfile_path = create_dockerfile(language, workspace_name)
        compose_path = create_docker_compose(language, workspace_name)
        create_sample_files(language, workspace_path)
        script_path = create_start_script(language, workspace_name)
        
        # Success message
        config = LANGUAGE_CONFIG[language]
        print("\n" + "="*60)
        print("🎉 SUCCESS! Workspace created successfully!")
        print("="*60)
        print(f"📁 Workspace: workspace-{workspace_name}")
        print(f"🗂️  Language: {language.title()}")
        print(f"🌐 Port: {config['port']}")
        print(f"🐳 Dockerfile: {dockerfile_path}")
        print(f"🐙 Compose file: {compose_path}")
        print(f"🎬 Start script: {script_path}")
        
        print("\n🚀 Quick Start:")
        print(f"   ./{script_path.name}")
        print(f"   # OR")
        print(f"   docker-compose -f {compose_path.name} up --build -d")
        
        print(f"\n🌐 Access your environment at: http://localhost:{config['port']}")
        print("🔑 Password: password123")
        
        print("\n🛑 To stop:")
        print(f"   docker-compose -f {compose_path.name} down")
        
        # Ask if user wants to start the environment
        start_now = input("\n❓ Would you like to start the environment now? (y/N): ").strip().lower()
        if start_now in ['y', 'yes']:
            print("\n🚀 Starting environment...")
            os.system(f"./{script_path.name}")
        
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
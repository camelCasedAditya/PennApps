#!/usr/bin/env python3

import os
from pathlib import Path
import shutil

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

def create_dockerfile(language, workspace_name, docker_templates):
    """Create Dockerfile for the specified language"""
    dockerfile_path = Path(f"Dockerfile.{workspace_name}")
    
    with open(dockerfile_path, 'w') as f:
        f.write(docker_templates[language])
    
    print(f"🐳 Created Dockerfile: {dockerfile_path}")
    return dockerfile_path

def create_docker_compose(language, workspace_name, language_config):
    """Create docker-compose.yml for the workspace"""
    config = language_config[language]
    
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

## development

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

def create_start_script(language, workspace_name, language_config):
    """Create a start script for the workspace"""
    config = language_config[language]
    
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
# Multi-Language Code Editor Platform

A comprehensive local VS Code experience supporting multiple programming languages using code-server in Docker.

## 🚀 Quick Start

### Start All Languages
```bash
./start.sh
```

### Start Specific Language
```bash
./start.sh python    # Python only
./start.sh nodejs    # Node.js only
./start.sh java      # Java only
./start.sh go        # Go only
./start.sh rust      # Rust only
```

## 🌐 Available Editors

| Language | Port | URL | Workspace |
|----------|------|-----|-----------|
| **Python** | 8080 | http://localhost:8080 | `./workspace-python/` |
| **Node.js** | 8081 | http://localhost:8081 | `./workspace-nodejs/` |
| **Java** | 8082 | http://localhost:8082 | `./workspace-java/` |
| **Go** | 8083 | http://localhost:8083 | `./workspace-go/` |
| **Rust** | 8084 | http://localhost:8084 | `./workspace-rust/` |
| **Simple** | 8085 | http://localhost:8085 | `./workspace-simple/` |

**Password for all editors:** `password123`

## ✨ Features

- **Full VS Code experience** in your browser
- **Multi-language support** with dedicated containers
- **Persistent workspaces** for each language
- **Integrated terminals** with language-specific tools
- **Git support** in all environments
- **File system access** to your local files

## 🛠️ Language-Specific Tools

### Python (Port 8080)
- Python 3.11, pip, venv
- Git, vim, nano, htop, tree

### Node.js (Port 8081)
- Node.js 18, npm, yarn, pnpm
- TypeScript, ts-node, nodemon

### Java (Port 8082)
- Java 17, Maven, Gradle
- Full JDK with development tools

### Go (Port 8083)
- Go compiler and tools
- GOPATH setup and workspace

### Rust (Port 8084)
- Rust compiler and Cargo
- Full Rust development environment

## 📁 Project Structure

```
pennapps25/
├── docker-compose.yml
├── start.sh
├── Dockerfile.python
├── Dockerfile.nodejs
├── Dockerfile.java
├── Dockerfile.go
├── Dockerfile.rust
├── workspace-python/     # Python projects
├── workspace-nodejs/     # Node.js projects
├── workspace-java/       # Java projects
├── workspace-go/         # Go projects
├── workspace-rust/       # Rust projects
└── workspace-simple/     # Basic editor
```

## 🎯 Usage Examples

### Python Development
```bash
./start.sh python
# Open http://localhost:8080
# Terminal: python3 hello.py
```

### Node.js Development
```bash
./start.sh nodejs
# Open http://localhost:8081
# Terminal: npm start
```

### Java Development
```bash
./start.sh java
# Open http://localhost:8082
# Terminal: javac HelloWorld.java && java HelloWorld
```

## 📚 Documentation

- **Language Guide**: See `LANGUAGE_GUIDE.md` for detailed instructions
- **Terminal Guide**: See `workspace/terminal_guide.md` for terminal usage

## 🔧 Management Commands

```bash
# Start all editors
./start.sh

# Start specific language
./start.sh <language>

# Stop all containers
docker-compose down

# View running containers
docker-compose ps

# View logs
docker-compose logs <service-name>

# Rebuild containers
docker-compose up -d --build
```

## 🛑 Troubleshooting

- **Port conflicts**: Each language uses a different port
- **Container issues**: `docker-compose down && docker-compose up -d`
- **Build problems**: `docker-compose up -d --build`
- **Check logs**: `docker-compose logs <service-name>`

This setup provides a complete multi-language development environment with VS Code's powerful features for each programming language!

# Multi-Language Development Guide

This setup provides VS Code environments for multiple programming languages, each with their own container and workspace.

## 🌐 Available Editors

| Language | Port | URL | Workspace | Tools Included |
|----------|------|-----|-----------|----------------|
| **Python** | 8080 | http://localhost:8080 | `./workspace-python/` | Python 3, pip, venv, git, vim |
| **Node.js** | 8081 | http://localhost:8081 | `./workspace-nodejs/` | Node.js, npm, yarn, TypeScript |
| **Java** | 8082 | http://localhost:8082 | `./workspace-java/` | Java 17, Maven, Gradle |
| **Go** | 8083 | http://localhost:8083 | `./workspace-go/` | Go, GOPATH setup |
| **Rust** | 8084 | http://localhost:8084 | `./workspace-rust/` | Rust, Cargo |
| **Simple** | 8085 | http://localhost:8085 | `./workspace-simple/` | Basic editor |

**Password for all editors:** `password123`

## 🚀 Quick Start

### Start All Editors
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

## 🐍 Python Development

**Access:** http://localhost:8080

### Commands
```bash
# Check Python version
python3 --version

# Run Python files
python3 hello.py
python3 test_python.py

# Create virtual environment
python3 -m venv myenv
source myenv/bin/activate

# Install packages
pip install requests numpy pandas

# Deactivate environment
deactivate
```

### Sample Files
- `hello.py` - Basic Python script
- `test_python.py` - Python functionality test

## 🟢 Node.js Development

**Access:** http://localhost:8081

### Commands
```bash
# Check Node.js version
node --version
npm --version

# Install dependencies
npm install

# Run application
npm start
node index.js

# Development mode
npm run dev

# Install packages
npm install express cors
npm install -D typescript @types/node
```

### Sample Files
- `package.json` - Node.js project configuration
- `index.js` - Express.js server

## ☕ Java Development

**Access:** http://localhost:8082

### Commands
```bash
# Check Java version
java -version
javac -version

# Compile Java files
javac HelloWorld.java

# Run Java programs
java HelloWorld

# Maven commands
mvn compile
mvn test
mvn package

# Gradle commands
gradle build
gradle run
```

### Sample Files
- `HelloWorld.java` - Basic Java application

## 🔵 Go Development

**Access:** http://localhost:8083

### Commands
```bash
# Check Go version
go version

# Run Go programs
go run main.go

# Build Go programs
go build main.go

# Initialize Go module
go mod init myproject

# Install packages
go get github.com/gin-gonic/gin
```

### Sample Files
- `main.go` - Go application with examples

## 🦀 Rust Development

**Access:** http://localhost:8084

### Commands
```bash
# Check Rust version
rustc --version
cargo --version

# Run Rust programs
cargo run

# Build Rust programs
cargo build

# Create new project
cargo new myproject

# Add dependencies
cargo add serde
```

### Sample Files
- `main.rs` - Rust application with examples
- `Cargo.toml` - Rust project configuration

## 🛠️ Development Workflow

### 1. Choose Your Language
```bash
# Start specific language
./start.sh python
```

### 2. Open Browser
- Navigate to the appropriate URL
- Enter password: `password123`

### 3. Open Terminal
- Press `Ctrl + `` (backtick) in VS Code
- Or go to `View > Terminal`

### 4. Start Coding
- Create new files in the workspace
- Use the integrated terminal for commands
- Install language-specific extensions

## 📁 Workspace Structure

```
pennapps25/
├── workspace-python/     # Python projects
├── workspace-nodejs/     # Node.js projects
├── workspace-java/       # Java projects
├── workspace-go/         # Go projects
├── workspace-rust/       # Rust projects
└── workspace-simple/     # Basic editor
```

## 🔧 VS Code Extensions

Each environment comes with code-server. Install language-specific extensions:

### Python
- Python (ms-python.python)
- Pylance (ms-python.vscode-pylance)

### Node.js
- JavaScript (ms-vscode.vscode-typescript-next)
- ES7+ React/Redux/React-Native snippets

### Java
- Extension Pack for Java (vscjava.vscode-java-pack)

### Go
- Go (golang.go)

### Rust
- rust-analyzer (rust-lang.rust-analyzer)

## 🐳 Container Management

### View Running Containers
```bash
docker-compose ps
```

### View Logs
```bash
docker-compose logs python-editor
docker-compose logs nodejs-editor
```

### Stop All Containers
```bash
docker-compose down
```

### Rebuild Containers
```bash
docker-compose up -d --build
```

## 💡 Tips

1. **Resource Management**: Each language runs in its own container
2. **File Persistence**: Files are saved in workspace directories
3. **Port Management**: Each language uses a different port
4. **Extension Installation**: Install extensions through VS Code UI
5. **Terminal Access**: Use `Ctrl + `` for integrated terminal
6. **Git Integration**: All environments include git support

## 🔄 Switching Between Languages

1. **Stop current containers**: `docker-compose down`
2. **Start specific language**: `./start.sh <language>`
3. **Or start all**: `./start.sh`

This setup gives you a complete multi-language development environment with VS Code's powerful features for each programming language!

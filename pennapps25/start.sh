#!/bin/bash

echo "🚀 Starting Multi-Language Code Editors..."

# Create workspace directories if they don't exist
mkdir -p workspace-python workspace-nodejs workspace-java workspace-go workspace-rust workspace-simple

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker Desktop first."
    exit 1
fi

# Parse command line arguments
LANGUAGE=""
if [ "$1" != "" ]; then
    LANGUAGE=$1
fi

# Start the containers
echo "📦 Starting Docker containers..."
if [ "$LANGUAGE" != "" ]; then
    echo "🎯 Starting $LANGUAGE editor only..."
    docker-compose up -d ${LANGUAGE}-editor
else
    echo "🌍 Starting all language editors..."
    docker-compose up -d
fi

# Wait a moment for containers to start
sleep 8

# Check if containers are running
if docker-compose ps | grep -q "Up"; then
    echo "✅ Code editors are running!"
    echo ""
    echo "🌐 Access your editors at:"
    echo "   • Python:     http://localhost:8080 (password: password123)"
    echo "   • Node.js:    http://localhost:8081 (password: password123)"
    echo "   • Java:       http://localhost:8082 (password: password123)"
    echo "   • Go:         http://localhost:8083 (password: password123)"
    echo "   • Rust:       http://localhost:8084 (password: password123)"
    echo "   • Simple:     http://localhost:8085 (password: password123)"
    echo ""
    echo "📁 Your workspace files are in:"
    echo "   • ./workspace-python/  - Python projects"
    echo "   • ./workspace-nodejs/  - Node.js/JavaScript projects"
    echo "   • ./workspace-java/    - Java projects"
    echo "   • ./workspace-go/      - Go projects"
    echo "   • ./workspace-rust/    - Rust projects"
    echo "   • ./workspace-simple/  - Basic editor"
    echo ""
    echo "💡 Usage:"
    echo "   • ./start.sh python    - Start only Python editor"
    echo "   • ./start.sh nodejs    - Start only Node.js editor"
    echo "   • ./start.sh java      - Start only Java editor"
    echo "   • ./start.sh go        - Start only Go editor"
    echo "   • ./start.sh rust      - Start only Rust editor"
    echo "   • ./start.sh           - Start all editors"
    echo ""
    echo "🛑 To stop: docker-compose down"
else
    echo "❌ Failed to start containers. Check logs with: docker-compose logs"
fi

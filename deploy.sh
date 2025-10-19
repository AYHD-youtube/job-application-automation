#!/bin/bash
# deploy.sh - Quick deployment script for Docker

set -e

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                                                              ║"
echo "║     🐳 Job Application Automation - Docker Deploy           ║"
echo "║                                                              ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    echo "   Run: curl -fsSL https://get.docker.com -o get-docker.sh && sudo sh get-docker.sh"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install it first."
    echo "   Run: sudo apt install docker-compose -y"
    exit 1
fi

echo "✅ Docker and Docker Compose are installed"
echo ""

# Create data directories
echo "📁 Creating data directories..."
mkdir -p data/uploads
mkdir -p data/user_credentials
mkdir -p data/databases
echo "✅ Data directories created"
echo ""

# Generate secret key if .env doesn't exist
if [ ! -f .env ]; then
    echo "🔐 Generating secret key..."
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null || openssl rand -hex 32)
    cat > .env << EOF
SECRET_KEY=$SECRET_KEY
FLASK_ENV=production
EOF
    echo "✅ Created .env file with secret key"
else
    echo "✅ .env file already exists"
fi
echo ""

# Build the Docker image
echo "🔨 Building Docker image..."
docker-compose build
echo "✅ Docker image built successfully"
echo ""

# Start the containers
echo "🚀 Starting containers..."
docker-compose up -d
echo "✅ Containers started"
echo ""

# Wait for app to be ready
echo "⏳ Waiting for app to be ready..."
sleep 5

# Check if app is running
if curl -f http://localhost:8001 > /dev/null 2>&1; then
    echo "✅ App is running!"
else
    echo "⚠️  App might not be ready yet. Check logs with: docker-compose logs -f"
fi
echo ""

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                                                              ║"
echo "║     ✅ DEPLOYMENT COMPLETE!                                  ║"
echo "║                                                              ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "🌐 Access your app at:"
echo "   • Local: http://localhost:8001"
echo "   • Server: http://$(hostname -I | awk '{print $1}'):8001"
echo ""
echo "📋 Useful commands:"
echo "   • View logs:    docker-compose logs -f"
echo "   • Stop app:     docker-compose down"
echo "   • Restart app:  docker-compose restart"
echo "   • Update app:   git pull && docker-compose up -d --build"
echo ""
echo "📚 For more info, see DOCKER_DEPLOYMENT.md"
echo ""


# 🐳 Docker Deployment Guide

Complete guide to deploy the Job Application Automation web app using Docker on your server.

---

## 📋 Prerequisites

- Docker installed on your server
- Docker Compose installed
- Domain name (optional, for reverse proxy)
- Port 8001 available

---

## 🚀 Quick Start

### 1. Clone the Repository

```bash
cd /srv/flaskapp
git clone https://github.com/AYHD-youtube/job-application-automation.git
cd job-application-automation
```

### 2. Build and Run with Docker Compose

```bash
# Build the image
docker-compose build

# Start the container
docker-compose up -d

# Check logs
docker-compose logs -f
```

### 3. Access the App

- **Local:** http://localhost:8001
- **Server:** http://your-server-ip:8001
- **Domain:** http://yourdomain.com:8001

---

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# .env
SECRET_KEY=your-super-secret-key-change-this
FLASK_ENV=production
```

Generate a secure secret key:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### Port Configuration

To change the port, edit `docker-compose.yml`:

```yaml
ports:
  - "8001:8001"  # Change first port for external access
```

---

## 🌐 Reverse Proxy Setup (Nginx)

### Option 1: Nginx Reverse Proxy

Create `/etc/nginx/sites-available/job-automation`:

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://localhost:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support (if needed)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
```

Enable the site:
```bash
sudo ln -s /etc/nginx/sites-available/job-automation /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### Option 2: SSL with Let's Encrypt

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Get SSL certificate
sudo certbot --nginx -d yourdomain.com

# Auto-renewal is set up automatically
```

---

## 📁 Data Persistence

Docker volumes are used to persist data:

```
./data/uploads/          - User resume uploads
./data/user_credentials/ - OAuth credentials
./data/databases/        - SQLite databases
```

These folders are created automatically and mounted to the container.

---

## 🔄 Docker Commands

### Start/Stop

```bash
# Start
docker-compose up -d

# Stop
docker-compose down

# Restart
docker-compose restart

# Stop and remove volumes (⚠️ deletes data)
docker-compose down -v
```

### Logs

```bash
# View logs
docker-compose logs

# Follow logs
docker-compose logs -f

# Last 100 lines
docker-compose logs --tail=100
```

### Update Application

```bash
# Pull latest code
git pull

# Rebuild and restart
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Shell Access

```bash
# Access container shell
docker-compose exec web bash

# Run commands in container
docker-compose exec web python -c "print('Hello')"
```

---

## 🐛 Troubleshooting

### Port Already in Use

```bash
# Check what's using port 8001
sudo lsof -i :8001

# Kill the process
sudo kill -9 <PID>

# Or change port in docker-compose.yml
```

### Container Won't Start

```bash
# Check logs
docker-compose logs web

# Check container status
docker-compose ps

# Rebuild from scratch
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Permission Issues

```bash
# Fix permissions on data folders
sudo chown -R $USER:$USER ./data

# Or run with sudo
sudo docker-compose up -d
```

### Database Locked

```bash
# Stop container
docker-compose down

# Remove lock files
rm -f data/databases/*.db-shm data/databases/*.db-wal

# Restart
docker-compose up -d
```

---

## 🔒 Security Best Practices

### 1. Change Secret Key

Never use the default secret key in production!

```bash
# Generate new key
python3 -c "import secrets; print(secrets.token_hex(32))"

# Add to .env file
echo "SECRET_KEY=your-generated-key" > .env
```

### 2. Use HTTPS

Always use SSL/TLS in production:
- Set up Nginx reverse proxy
- Get Let's Encrypt certificate
- Force HTTPS redirects

### 3. Firewall Rules

```bash
# Allow only necessary ports
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable

# Block direct access to 8001 (if using reverse proxy)
sudo ufw deny 8001/tcp
```

### 4. Regular Updates

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Update Docker images
docker-compose pull
docker-compose up -d
```

---

## 📊 Monitoring

### Health Check

The container includes a health check:

```bash
# Check health status
docker-compose ps

# Manual health check
curl http://localhost:8001/
```

### Resource Usage

```bash
# Check container stats
docker stats job-automation-app

# Check disk usage
docker system df
```

---

## 🔄 Backup & Restore

### Backup

```bash
# Create backup directory
mkdir -p backups

# Backup data
tar -czf backups/backup-$(date +%Y%m%d).tar.gz data/

# Backup to remote server (optional)
rsync -avz data/ user@backup-server:/backups/job-automation/
```

### Restore

```bash
# Stop container
docker-compose down

# Restore data
tar -xzf backups/backup-YYYYMMDD.tar.gz

# Start container
docker-compose up -d
```

---

## 🚀 Production Deployment Checklist

- [ ] Change SECRET_KEY in .env
- [ ] Set up Nginx reverse proxy
- [ ] Configure SSL with Let's Encrypt
- [ ] Set up firewall rules
- [ ] Configure automatic backups
- [ ] Set up monitoring/alerts
- [ ] Test all features
- [ ] Document custom configuration

---

## 📝 Example: Complete Setup on Ubuntu Server

```bash
# 1. Update system
sudo apt update && sudo apt upgrade -y

# 2. Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# 3. Install Docker Compose
sudo apt install docker-compose -y

# 4. Clone repository
cd /srv/flaskapp
git clone https://github.com/AYHD-youtube/job-application-automation.git
cd job-application-automation

# 5. Create .env file
cat > .env << EOF
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
FLASK_ENV=production
EOF

# 6. Build and start
docker-compose build
docker-compose up -d

# 7. Check status
docker-compose ps
docker-compose logs -f

# 8. Access app
curl http://localhost:8001
```

---

## 🌐 Domain Setup Example

### With Nginx + SSL

```bash
# 1. Install Nginx
sudo apt install nginx -y

# 2. Create config
sudo nano /etc/nginx/sites-available/job-automation

# Paste the Nginx config from above

# 3. Enable site
sudo ln -s /etc/nginx/sites-available/job-automation /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# 4. Get SSL certificate
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d yourdomain.com

# 5. Test
curl https://yourdomain.com
```

---

## 📞 Support

### Logs Location

- Container logs: `docker-compose logs`
- Nginx logs: `/var/log/nginx/`
- Application logs: Inside container at `/app/`

### Common Issues

1. **Port conflict:** Change port in docker-compose.yml
2. **Permission denied:** Run with sudo or fix permissions
3. **Database locked:** Stop container, remove lock files
4. **Out of memory:** Increase Docker memory limit

---

## 🎉 Success!

Your app should now be running at:
- **http://localhost:8001** (local)
- **http://your-server-ip:8001** (server)
- **https://yourdomain.com** (with reverse proxy)

Users can:
1. Register accounts
2. Upload credentials.json
3. Authorize Gmail
4. Start automating job applications!

---

**Need help?** Check the troubleshooting section or create an issue on GitHub.


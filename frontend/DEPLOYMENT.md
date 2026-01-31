# Deployment Guide

This guide covers deploying the Text2DSL frontend to various platforms.

## Build Process

Before deploying, build the production-optimized bundle:

```bash
npm run build
```

This creates an optimized build in the `dist/` directory:
- Minified JavaScript and CSS
- Optimized assets
- Production-ready static files

## Deployment Options

### Option 1: Static Hosting (Recommended)

Deploy the frontend separately from the backend to a static hosting service.

#### Vercel

```bash
# Install Vercel CLI
npm install -g vercel

# Deploy
cd frontend
npm run build
vercel --prod
```

**Configuration** (`vercel.json`):
```json
{
  "rewrites": [
    { "source": "/api/(.*)", "destination": "https://your-backend.com/api/$1" },
    { "source": "/(.*)", "destination": "/index.html" }
  ]
}
```

#### Netlify

```bash
# Install Netlify CLI
npm install -g netlify-cli

# Deploy
cd frontend
npm run build
netlify deploy --prod --dir=dist
```

**Configuration** (`netlify.toml`):
```toml
[build]
  command = "npm run build"
  publish = "dist"

[[redirects]]
  from = "/api/*"
  to = "https://your-backend.com/api/:splat"
  status = 200

[[redirects]]
  from = "/*"
  to = "/index.html"
  status = 200
```

#### AWS S3 + CloudFront

```bash
# Build
npm run build

# Upload to S3
aws s3 sync dist/ s3://your-bucket-name --delete

# Create CloudFront distribution
# Point to S3 bucket
# Enable custom domain with SSL
```

**S3 Bucket Policy**:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PublicReadGetObject",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::your-bucket-name/*"
    }
  ]
}
```

### Option 2: Served from Backend

Serve the frontend directly from the FastAPI backend.

#### Setup

1. **Build frontend**:
```bash
cd frontend
npm run build
```

2. **Update backend** (`src/text2x/api/app.py`):
```python
from fastapi.staticfiles import StaticFiles

# After all route registrations
app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="frontend")
```

3. **Deploy backend** with frontend included:
```bash
# Build Docker image with frontend
docker build -t text2dsl:latest .

# Run container
docker run -p 8000:8000 text2dsl:latest
```

#### Dockerfile Example

```dockerfile
FROM node:18 AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim
WORKDIR /app
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist
COPY requirements.txt ./
RUN pip install -r requirements.txt
COPY src/ ./src/
CMD ["uvicorn", "src.text2x.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Option 3: Docker Compose

Deploy frontend and backend together using Docker Compose.

**docker-compose.prod.yml**:
```yaml
version: '3.8'

services:
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.prod
    ports:
      - "80:80"
    environment:
      - VITE_API_URL=http://backend:8000
    depends_on:
      - backend

  backend:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - OPENSEARCH_URL=${OPENSEARCH_URL}
    depends_on:
      - postgres
      - redis
      - opensearch

  nginx:
    image: nginx:alpine
    ports:
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - frontend
      - backend
```

**Frontend Dockerfile.prod**:
```dockerfile
FROM node:18 AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

## Environment Configuration

### Production Environment Variables

Create `.env.production`:

```env
# Backend API URL (MUST be absolute URL in production)
VITE_API_URL=https://api.text2dsl.com
VITE_WS_URL=wss://api.text2dsl.com
```

Build with production env:
```bash
npm run build
```

### Dynamic Configuration

For runtime configuration, create `public/config.js`:

```javascript
window.APP_CONFIG = {
  API_URL: 'https://api.text2dsl.com',
  WS_URL: 'wss://api.text2dsl.com',
  ENVIRONMENT: 'production'
}
```

Load in `index.html`:
```html
<script src="/config.js"></script>
```

Use in code:
```javascript
const API_URL = window.APP_CONFIG?.API_URL || import.meta.env.VITE_API_URL
```

## SSL/TLS Configuration

### Nginx SSL Configuration

```nginx
server {
    listen 80;
    server_name text2dsl.com www.text2dsl.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name text2dsl.com www.text2dsl.com;

    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    root /usr/share/nginx/html;
    index index.html;

    # Frontend
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API proxy
    location /api/ {
        proxy_pass http://backend:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    # WebSocket proxy
    location /ws/ {
        proxy_pass http://backend:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    add_header Content-Security-Policy "default-src 'self' https: wss: data: 'unsafe-inline' 'unsafe-eval'" always;
}
```

## Performance Optimization

### Compression

Enable gzip compression in Nginx:

```nginx
gzip on;
gzip_vary on;
gzip_min_length 1024;
gzip_types text/plain text/css text/xml text/javascript
           application/x-javascript application/xml+rss
           application/javascript application/json;
```

### Caching

Configure cache headers:

```nginx
location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}

location = /index.html {
    add_header Cache-Control "no-cache";
}
```

### CDN Integration

Use a CDN for static assets:

1. **Upload assets to CDN**:
```bash
aws s3 sync dist/assets s3://cdn-bucket/
```

2. **Update asset URLs** in build:
```javascript
// vite.config.js
export default defineConfig({
  build: {
    rollupOptions: {
      output: {
        assetFileNames: (assetInfo) => {
          return `https://cdn.text2dsl.com/assets/[name]-[hash][extname]`
        }
      }
    }
  }
})
```

## Monitoring

### Health Checks

Add health check endpoint for monitoring:

```javascript
// public/health.json
{
  "status": "ok",
  "version": "1.0.0",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### Error Tracking

Integrate error tracking (e.g., Sentry):

```javascript
// src/main.jsx
import * as Sentry from "@sentry/react"

Sentry.init({
  dsn: "your-sentry-dsn",
  environment: import.meta.env.MODE,
  tracesSampleRate: 1.0,
})
```

### Analytics

Add analytics (e.g., Google Analytics):

```html
<!-- index.html -->
<script async src="https://www.googletagmanager.com/gtag/js?id=GA_MEASUREMENT_ID"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'GA_MEASUREMENT_ID');
</script>
```

## CI/CD Pipeline

### GitHub Actions

`.github/workflows/deploy-frontend.yml`:

```yaml
name: Deploy Frontend

on:
  push:
    branches: [main]
    paths:
      - 'frontend/**'

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Setup Node.js
      uses: actions/setup-node@v3
      with:
        node-version: '18'
        cache: 'npm'
        cache-dependency-path: frontend/package-lock.json

    - name: Install dependencies
      run: |
        cd frontend
        npm ci

    - name: Build
      run: |
        cd frontend
        npm run build
      env:
        VITE_API_URL: ${{ secrets.API_URL }}
        VITE_WS_URL: ${{ secrets.WS_URL }}

    - name: Deploy to S3
      uses: jakejarvis/s3-sync-action@master
      with:
        args: --delete
      env:
        AWS_S3_BUCKET: ${{ secrets.AWS_S3_BUCKET }}
        AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
        AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        SOURCE_DIR: 'frontend/dist'

    - name: Invalidate CloudFront
      run: |
        aws cloudfront create-invalidation \
          --distribution-id ${{ secrets.CLOUDFRONT_DISTRIBUTION_ID }} \
          --paths "/*"
```

## Rollback Strategy

### Version Tracking

Tag releases for easy rollback:

```bash
# Tag release
git tag -a frontend-v1.0.0 -m "Frontend release v1.0.0"
git push origin frontend-v1.0.0

# Rollback to previous version
git checkout frontend-v0.9.0
npm run build
# Deploy
```

### Blue-Green Deployment

1. Deploy new version to "green" environment
2. Test thoroughly
3. Switch traffic to "green"
4. Keep "blue" for instant rollback

## Checklist

Before deploying to production:

- [ ] Build succeeds without errors
- [ ] All environment variables configured
- [ ] SSL certificates installed and valid
- [ ] CORS configured for production domain
- [ ] WebSocket endpoint accessible
- [ ] Error tracking enabled
- [ ] Analytics integrated (if needed)
- [ ] Performance optimized (compression, caching)
- [ ] Security headers configured
- [ ] Health check endpoint working
- [ ] Backup/rollback plan in place
- [ ] Monitoring and alerting set up
- [ ] Load testing completed
- [ ] Documentation updated

## Troubleshooting

### Build Fails

```bash
# Clear cache and rebuild
rm -rf node_modules dist .vite
npm install
npm run build
```

### Assets Not Loading

Check:
1. Base URL in `vite.config.js`
2. Public path configuration
3. CDN CORS settings

### WebSocket Connection Fails

Verify:
1. WSS (not WS) in production
2. Proxy/load balancer WebSocket support
3. Firewall rules allow WebSocket
4. Certificate valid for WebSocket domain

### CORS Errors

Update backend CORS settings:
```python
allow_origins=["https://text2dsl.com", "https://www.text2dsl.com"]
```

## Support

For deployment issues:
1. Check logs in browser console
2. Review backend logs
3. Verify network connectivity
4. Test with curl/wscat
5. Check firewall and security groups

## Resources

- [Vite Deployment Guide](https://vitejs.dev/guide/static-deploy.html)
- [Nginx Configuration](https://nginx.org/en/docs/)
- [WebSocket Deployment](https://developer.mozilla.org/en-US/docs/Web/API/WebSockets_API)
- [AWS CloudFront](https://aws.amazon.com/cloudfront/)

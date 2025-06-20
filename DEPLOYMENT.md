# DigitalOcean App Platform Deployment Guide

## Prerequisites
- DigitalOcean account
- GitHub repository with your bot code
- Environment variables ready

## Environment Variables
Set these in your DigitalOcean App Platform dashboard:

- `BOT_TOKEN` - Your Telegram bot token
- `DATABASE_URL_UNPOOLED` - Your PostgreSQL connection string
- `OPENAI_API_KEY` - Your OpenAI API key

## Deployment Steps

### Option 1: Using DigitalOcean CLI (doctl)

1. **Install doctl** (if not already installed)
   ```bash
   # macOS
   brew install doctl
   
   # Linux
   snap install doctl
   ```

2. **Authenticate with DigitalOcean**
   ```bash
   doctl auth init
   ```

3. **Deploy the app**
   ```bash
   doctl apps create --spec .do/app.yaml
   ```

### Option 2: Using DigitalOcean Dashboard

1. **Go to App Platform** in your DigitalOcean dashboard
2. **Click "Create App"**
3. **Connect your GitHub repository**
4. **Configure the app:**
   - **Source Directory**: `/` (root)
   - **Run Command**: `python main.py`
   - **Environment**: Python
   - **Instance Size**: Basic XXS (or your preferred size)

5. **Add Environment Variables:**
   - `BOT_TOKEN`
   - `DATABASE_URL_UNPOOLED`
   - `OPENAI_API_KEY`

6. **Configure Health Check:**
   - **HTTP Path**: `/health`
   - **Initial Delay**: 30 seconds
   - **Interval**: 10 seconds
   - **Timeout**: 5 seconds
   - **Success Threshold**: 1
   - **Failure Threshold**: 3

7. **Deploy the app**

## Health Check Configuration

The bot now includes a web server that responds to health checks on port 8080:

- **Endpoint**: `/health`
- **Response**: "OK" with 200 status
- **Port**: 8080

## Troubleshooting

### Health Check Fails
1. **Check logs** in DigitalOcean dashboard
2. **Verify port 8080** is exposed
3. **Ensure environment variables** are set correctly
4. **Check database connectivity**

### Bot Not Responding
1. **Verify BOT_TOKEN** is correct
2. **Check bot is running** in logs
3. **Ensure database** is accessible

### Common Issues
- **Port conflicts**: Make sure only port 8080 is used
- **Memory limits**: Basic XXS has 512MB RAM
- **Database timeouts**: Check connection string format

## Monitoring

- **Logs**: Available in DigitalOcean dashboard
- **Metrics**: CPU, memory, and network usage
- **Health Status**: Automatic monitoring via health checks

## Scaling

- **Vertical**: Increase instance size
- **Horizontal**: Increase instance count
- **Auto-scaling**: Configure based on CPU/memory usage 
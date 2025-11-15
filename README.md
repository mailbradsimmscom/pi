# REIMAGINED Telemetry Agent

Lightweight telemetry agent for collecting GPS data from Signal K and pushing to Supabase.

## Overview

This agent runs on the Raspberry Pi aboard the boat and:
- Connects to the local Signal K server
- Fetches GPS position data (lat/lon/altitude/speed/course)
- Stores telemetry in Supabase every 10 seconds

## Setup

### 1. Install Dependencies

```bash
# Activate virtual environment
source venv/bin/activate

# Install Python packages
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy example config
cp .env.example .env

# Edit with your credentials
nano .env
```

Required configuration:
- `SIGNALK_URL`: URL of your Signal K server (e.g., `http://localhost:3000`)
- `SUPABASE_URL`: Your Supabase project URL
- `SUPABASE_SERVICE_ROLE_KEY`: Supabase service role key (from main app)
- `BOAT_ID`: Boat identifier (currently: `REIMAGINED`)

### 3. Create Database Table

Run the SQL in `schema.sql` in your Supabase SQL Editor to create the `gps_position` table.

### 4. Run the Agent

```bash
# Manual run (for testing)
python telemetry_agent.py

# Run in background
nohup python telemetry_agent.py &

# Or use systemd (see below)
```

## Running as a Service

To run automatically on boot using systemd:

```bash
# Copy service file
sudo cp telemetry-agent.service /etc/systemd/system/

# Edit paths in service file if needed
sudo nano /etc/systemd/system/telemetry-agent.service

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable telemetry-agent
sudo systemctl start telemetry-agent

# Check status
sudo systemctl status telemetry-agent

# View logs
sudo journalctl -u telemetry-agent -f
```

## Logging

Logs are written to:
- **Console/stdout**: When running manually
- **File**: `telemetry_agent.log` in the project directory
- **systemd journal**: When running as a service

## Troubleshooting

### Signal K Connection Issues

Check that Signal K is running:
```bash
curl http://localhost:3000/signalk/v1/api/
```

### Supabase Connection Issues

Verify your credentials in `.env` and ensure the `gps_position` table exists.

### View Recent Data

Check Supabase dashboard or run:
```sql
SELECT * FROM gps_position ORDER BY created_at DESC LIMIT 10;
```

## Architecture

```
Signal K (NMEA 2000) → Telemetry Agent → Supabase → REIMAGINED App
```

This is a **lightweight sidecar** - no business logic, just data collection and forwarding.

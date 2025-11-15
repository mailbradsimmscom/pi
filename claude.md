# REIMAGINEDsv – Pi Telemetry Agent (Claude Notes)

This repo is **only** for the Raspberry Pi–side telemetry agent.

The goal:  
Take live boat data from the **Signal K** server running on the Pi, and push **normalized telemetry** (starting with GPS position) into the **REIMAGINED backend API**, which then writes to **Supabase/Postgres**.

This is a small, focused “sidecar” and **must not** contain business logic, AI workflows, or anything that belongs in the main app.

---

## High-Level Architecture

End-to-end flow:

```text
NMEA 2000 → Signal K (on Pi) → Pi Telemetry Agent (this repo)
→ REIMAGINED Backend API (Node on Render) → Supabase/Postgres
→ REIMAGINEDsv App UI / Agents / Analytics

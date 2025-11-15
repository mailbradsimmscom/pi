-- GPS Position Telemetry Table
-- Run this in Supabase SQL Editor to create the table

CREATE TABLE IF NOT EXISTS gps_position (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    boat_id TEXT NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    altitude DOUBLE PRECISION,
    speed_over_ground DOUBLE PRECISION,
    course_over_ground DOUBLE PRECISION,
    timestamp TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Indexes for common queries
    CONSTRAINT gps_position_boat_id_idx
        CHECK (boat_id IS NOT NULL AND boat_id <> '')
);

-- Index for querying by boat and time
CREATE INDEX IF NOT EXISTS idx_gps_position_boat_time
    ON gps_position(boat_id, timestamp DESC);

-- Index for recent positions
CREATE INDEX IF NOT EXISTS idx_gps_position_created
    ON gps_position(created_at DESC);

-- Optional: Enable Row Level Security (RLS)
-- ALTER TABLE gps_position ENABLE ROW LEVEL SECURITY;

-- Optional: Create policy for authenticated access
-- CREATE POLICY "Allow authenticated read access"
--     ON gps_position FOR SELECT
--     TO authenticated
--     USING (true);

COMMENT ON TABLE gps_position IS 'GPS telemetry data from Signal K on boat Raspberry Pi';
COMMENT ON COLUMN gps_position.boat_id IS 'Unique identifier for the boat (currently: REIMAGINED)';
COMMENT ON COLUMN gps_position.timestamp IS 'Timestamp from Signal K when position was recorded';
COMMENT ON COLUMN gps_position.created_at IS 'Timestamp when record was inserted into database';

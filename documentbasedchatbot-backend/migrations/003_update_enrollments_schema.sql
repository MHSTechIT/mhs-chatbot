-- Drop the old enrollments table and recreate with new schema
DROP TABLE IF EXISTS enrollments CASCADE;

-- Create new enrollments table with updated schema
CREATE TABLE enrollments (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    age INTEGER NOT NULL,
    location VARCHAR(255) NOT NULL,
    sugar_level VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Create indexes for better query performance
CREATE INDEX idx_enrollments_name ON enrollments(name);
CREATE INDEX idx_enrollments_phone ON enrollments(phone);
CREATE INDEX idx_enrollments_location ON enrollments(location);
CREATE INDEX idx_enrollments_created_at ON enrollments(created_at);

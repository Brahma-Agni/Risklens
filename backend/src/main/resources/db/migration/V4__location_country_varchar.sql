ALTER TABLE transactions
    ALTER COLUMN location_country TYPE VARCHAR(2)
    USING TRIM(location_country);

-- สร้างฐานสำหรับ Superset (metadata)
SELECT 'CREATE DATABASE superset_meta' 
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'superset_meta') 
\gexec;


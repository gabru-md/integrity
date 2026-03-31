-- Rasbhari database initialisation
-- Runs once when the postgres container is first created.
-- POSTGRES_DB (rasbhari) is already created by the official image.

CREATE DATABASE events;
CREATE DATABASE queue;
CREATE DATABASE notifications;
CREATE DATABASE thoughts;

# Setup and run

This guide explains how to configure and start the project's local development
services. See the [architecture diagram](../README.md#system-architecture-diagram)
for an overview of the application.

| Service | Implementation | Default host port |
| --- | --- | --- |
| `backend` | FastAPI on Python 3.13, served by Uvicorn | `5000` |
| `postgres` | PostgreSQL 18 | `5432` |
| `seaweedfs` | SeaweedFS 4.53 with an S3-compatible API | `8333` |

## 1. Prepare your environment

Install Git and Docker with the Compose v2 plugin. Docker Desktop includes
Compose; Linux users can use Docker Engine with the Compose plugin. The first
build needs internet access to download container images and Python packages.
Python and PostgreSQL do not need to be installed on your host.

Make sure Docker is running before continuing.

If you have not cloned the repository, clone it using a GitHub account and SSH
key with access to the private repository:

```bash
git clone git@github.com:lefkovitzj/CPS420-Project.git
cd CPS420-Project
```

For an existing clone, open its directory instead. Run every command below from
the repository root, where `compose.yaml` and `.env.example` are located. The
examples use a Bash-compatible terminal.

## 2. Configure `.env`

If `.env` already exists, edit it rather than overwriting it. On first setup,
copy the example configuration:

```bash
cp .env.example .env
```

Docker Compose reads this file automatically when you run commands from the
repository root; you do not need to source it in your shell.

Review these settings in your editor:

| Variable | Example value or guidance | Purpose |
| --- | --- | --- |
| `HOST` | `127.0.0.1` | Host interface for published service ports. |
| `BACKEND_PORT` | `5000` | Backend port on both the host and container. |
| `POSTGRES_PORT` | `5432` | Host port for PostgreSQL; the container uses `5432`. |
| `POSTGRES_DB` | `cps420` | Database created when PostgreSQL initializes an empty data directory. |
| `POSTGRES_USER` | `cps420` | PostgreSQL user created during initialization. |
| `POSTGRES_PASSWORD` | Choose a local development password. | Password for the PostgreSQL user. |
| `SEAWEEDFS_S3_PORT` | `8333` | Host port for the S3 API; the container uses `8333`. |
| `AWS_ACCESS_KEY_ID` | `cps420-dev` | Access key for the local SeaweedFS S3 API. |
| `AWS_SECRET_ACCESS_KEY` | Choose a local development secret. | Secret key for the local SeaweedFS S3 API. |
| `S3_BUCKET` | `cps420-uploads` | Bucket configured for the local SeaweedFS instance. |

`POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `AWS_ACCESS_KEY_ID`,
`AWS_SECRET_ACCESS_KEY`, and `S3_BUCKET` must all be nonempty. The values in
`.env.example` are development examples, not production credentials. The AWS
variable names configure the local S3-compatible service; an AWS account is not
required.

Keep `HOST=127.0.0.1` for local development. Changing it to `0.0.0.0` publishes all
three services on every host interface. If a port is already occupied, choose a
free port for that service in `.env`.

`.env` is ignored by Git. For literal `$` or `#` characters in a credential, 
enclose its value in single quotes in `.env`. Environment variables already 
exported in your terminal take precedence over `.env`, so unset conflicting 
exports if your settings seem to be ignored.

## 3. Build and start the services

Build the backend image and start all three services in the background:

```bash
docker compose up --build -d
```

The first run downloads the images and creates local data directories. Startup
can take a little time. Optionally check the container status:

```bash
docker compose ps
```

PostgreSQL should show `healthy` once it is ready. Database clients can connect
to `127.0.0.1` on `POSTGRES_PORT`, using the database name, user, and password
from `.env`.

Use `http://127.0.0.1:8333` as the endpoint for an S3-compatible client, along with
`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, and `S3_BUCKET` from `.env`. Replace
`8333` if you changed `SEAWEEDFS_S3_PORT`.

### Set up the first administrator

On a fresh database, open the [registration page](http://127.0.0.1:3000/register)
and create an account with your `@udayton.edu` email. Use your configured
`FRONTEND_PORT` if it differs from `3000`. From the repository root, run this
command with the email you registered to grant the account the admin role in PostgreSQL.

```bash
docker compose exec backend python -m admin_access <username>@udayton.edu
```

Log in and open **Admin dashboard**. From there, use **Make admin** to grant
access to other registered users.

## 4. Stop, restart, and rebuild

Stop the services while keeping their containers:

```bash
docker compose stop
```

Start them again, or apply changes made to `.env`:

```bash
docker compose up -d
```

Backend source files are copied into the image at build time. After changing
backend files or the Dockerfile, rebuild and recreate the backend:

```bash
docker compose up --build -d backend
```

To remove the project's containers and Compose network:

```bash
docker compose down
```

### Persistent data

Service data is stored in bind-mounted directories under the repository:

- `data/postgres/` contains PostgreSQL data.
- `data/seaweedfs/` contains SeaweedFS data.

Both directories are ignored by Git. They survive `docker compose down`, and
`docker compose down -v` does not remove them either. Preserve these directories
when you want to keep local data; stop the services before moving or removing
them. Removing them discards the stored database or objects.

PostgreSQL's initialization variables apply when its data directory is empty.
Editing `POSTGRES_DB`, `POSTGRES_USER`, or `POSTGRES_PASSWORD` in `.env` does not
rename an existing database, recreate users, or change an existing password.
Keep the settings consistent with existing data or make the corresponding
database changes explicitly.

## Troubleshooting

If a service fails to start, inspect its logs:

```bash
docker compose logs --tail=100
```

| Symptom | What to check |
| --- | --- |
| Docker daemon connection or socket permission error | Start Docker and verify your account can run `docker version`. On Linux, see Docker's [post-installation instructions](https://docs.docker.com/engine/install/linux-postinstall/). |
| Compose reports a missing variable | Check that `.env` is at the repository root and all six required values are nonempty. |
| A setting differs from `.env` | Check for an exported shell variable overriding it. |
| A port is already allocated | Choose an unused service port in `.env`, then rerun `docker compose up -d`. |
| PostgreSQL is unhealthy or credentials stopped working | Check `docker compose logs postgres` and whether existing data was initialized with different credentials. |
| Source changes do not appear | Rebuild the backend image with `docker compose up --build -d backend`. |

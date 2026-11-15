# Brevet Control Time Calculator

**Author:** Banyan Jullian

**Email:** bjullian@uoregon.edu

This Flask application calculates ACP brevet control opening and closing
times. Enter a brevet distance and start time, then enter control distances
in kilometers or miles. The page converts distances and updates times using
AJAX without reloading.

## Calculation rules

The calculator supports 200, 300, 400, 600, and 1000 km brevets. Control
distances are truncated to whole kilometers and capped at the selected brevet
distance for calculation. Times are rounded to the nearest minute and shown
in the start time's local wall-clock time.

Opening times use the following maximum speeds for successive distance bands:

| Distance band | Speed |
| --- | ---: |
| 0-200 km | 34 km/h |
| 200-400 km | 32 km/h |
| 400-600 km | 30 km/h |
| Beyond 600 km | 28 km/h |

Closing times use 15 km/h through 600 km and 11.428 km/h beyond 600 km.
For controls below 60 km, the closing time is distance / 20 + 1 hour after
the start. At the nominal finish, the overall limits take precedence:
13h30 for 200 km, 20h for 300 km, 27h for 400 km, 40h for 600 km, and
75h for 1000 km.

## Saving and displaying

**Submit** validates the entered controls and recalculates their times on the
server before saving a submission in MongoDB. At least one control distance
is required; locations are optional. Each submission is stored separately.
**Display** opens a page showing the saved submissions and their controls.
Errors are shown if validation or a database operation fails.

## Docker Compose

Install Docker Desktop or Docker Engine with Compose. From the project root:

```powershell
cd DockerMongo
docker compose up --build
```

Open http://localhost:5000. Stop the application with Ctrl+C, then run
`docker compose down` to remove its containers. The named MongoDB volume
retains saved submissions. The page also loads jQuery and Bootstrap from CDNs,
so those resources require an internet connection.

## Docker without Compose

From `DockerMongo`, create a network and database container, then build and
run the web container:

```powershell
docker network create brevet-net
docker run -d --name brevet-db --network brevet-net -v brevet-data:/data/db mongo:4.4.29
docker build -t brevet-calculator .
docker run --rm --name brevet-web --network brevet-net -p 5000:5000 -e MONGO_HOST=brevet-db brevet-calculator python -u app.py
```

After stopping the web container with Ctrl+C, run `docker stop brevet-db`,
`docker rm brevet-db`, and `docker network rm brevet-net`. The `brevet-data`
volume retains the saved submissions.

## Local installation

Python 3.11 and a MongoDB server listening on port 27017 are required. From
`DockerMongo` in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:MONGO_HOST = "127.0.0.1"
python app.py
```

Open http://localhost:5000. Use a compatible MongoDB server such as 4.4.29.

## Tests

With the Compose application running, execute:

```powershell
docker compose exec web python -m unittest -v test_acp_times test_submit test_display
```

These tests cover ACP calculations, the AJAX endpoint, Submit, and Display.
They can also be run with the same Python command from the local environment.

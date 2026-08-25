# Clinic Booking System

FastAPI backend for a clinic appointment booking system. Patients can view
available 30-minute slots, book, cancel, and reschedule appointments across
5 doctors.

## Section 1: System Design

### Models

**Doctor** — id, name

**WorkingHours** — id, doctor_id (FK), day_of_week, start_time, end_time

A doctor can have multiple rows for the same day (e.g. Monday 08:00-13:00
and 14:00-17:00), which represents a lunch break without any special-case
logic.

**Patient** — id, name, email, phone_number

Kept separate from Appointment to avoid duplicating patient details across
bookings.

**Appointment** — id, doctor_id (FK), patient_id (FK), slot_start_time,
status (confirmed/cancelled), cancellation_reason (nullable)

Only `slot_start_time` is stored, not an end time. Every appointment is a
fixed 30 minutes, so storing both risks inconsistent data for no benefit.

### Why there's no Slot table

Slots are generated on request from a doctor's WorkingHours rather than
stored.

For a given doctor and date, the system:

1. Looks up the doctor's working periods.
2. Generates 30-minute slots.
3. Removes slots occupied by confirmed appointments.
4. Removes slots that are in the past or within one hour of the current time.
5. Returns the remaining slots.

Storing every possible slot for every doctor for every future day would
create unnecessary data and could become stale whenever working hours change.

### Preventing double-booking

Checking whether a slot is free and then creating the appointment is not
atomic. Two requests could both pass the availability check before either
request creates the appointment.

The system therefore uses a PostgreSQL partial unique index on:

`(doctor_id, slot_start_time) WHERE status = 'confirmed'`

This makes double-booking impossible at the database level. If two requests
race for the same slot, the database rejects the second confirmed
appointment and the API returns `409 Conflict`.

The booking endpoint also independently validates every request rather than
trusting availability data that may have become outdated.

### Cancel and Reschedule

Cancelling changes the appointment status to `cancelled` and stores the
cancellation reason.

Because availability only excludes confirmed appointments, the cancelled
appointment's slot automatically becomes available again.

Cancelling an already-cancelled appointment returns `400 Bad Request`.

Rescheduling validates the new slot using the same rules as a new booking.
The original appointment is only changed after the new slot has been
validated successfully.

If the new slot is already occupied, the API returns `409 Conflict`.

### Timezone Handling


The clinic operates in **Africa/Nairobi (UTC+3)**.

All appointment timestamps are normalized and stored as **timezone-aware UTC values**.

The clinic's working hours are defined in **Nairobi time** and converted to UTC when generating availability slots.

For example:

* 09:00 Nairobi → 06:00 UTC
* 09:30 Nairobi → 06:30 UTC
* 16:30 Nairobi → 13:30 UTC

The availability endpoint currently returns slot times as UTC `time` values. Clients consuming the API should interpret these times as UTC and convert them to the user's local timezone for display.

### Scope decisions

- **Doctor leave/exceptions:** out of scope. WorkingHours represents a
  standing weekly schedule. A `DoctorAvailabilityException` model could be
  added later.
- **Patient registration:** out of scope. `POST /appointments` expects an
  existing `patient_id`.
- **Doctor and working-hour management:** out of scope for this assessment.
  Seed data is used for the initial clinic configuration.
- **1-hour minimum booking notice:** implemented as the bonus requirement.

---

## Section 2: API Implementation

### Structure

```text
app/
  models/       SQLAlchemy models
  schemas/      Pydantic request/response schemas
  services/     Business logic
  routes/       API route handlers
  database.py   Database engine, sessions and Base
  config.py     Environment settings
  main.py       FastAPI application

alembic/        Database migrations
scripts/        Database seed scripts
tests/          Automated API tests
```

### Technology Stack

- Python 3.14
- FastAPI
- SQLAlchemy 2.0
- Alembic
- Pydantic V2
- PostgreSQL — application database
- SQLite — isolated automated test database
- Docker
- Pytest
- GitHub Actions
- Render

PostgreSQL is used by the application, including the deployed
production environment. SQLite is used only for the automated test suite
so tests do not modify application data.

### Endpoints

**Book an appointment**

`POST /appointments`

Validates:
- Doctor exists
- Patient exists
- Slot is within working hours
- Slot is aligned to a 30-minute boundary
- Slot is not in the past
- Slot is at least one hour in the future
- Slot is not already booked

Returns `409 Conflict` if the slot is already booked.

**Check doctor availability**

`GET /doctors/{id}/availability?day=YYYY-MM-DD`

Returns available 30-minute slots for the specified doctor and date.

**Cancel an appointment**

`PATCH /appointments/{id}/cancel`

Request body:
```json
{
  "cancellation_reason": "Patient requested cancellation"
}
```

Returns `400 Bad Request` if the appointment has already been cancelled.

**Reschedule an appointment**

`PATCH /appointments/{id}/reschedule`

Request body:
```json
{
  "slot_start_time": "2026-08-26T15:00:00Z"
}
```

The new slot is validated using the same rules as a fresh booking.

Returns `400 Bad Request` if the appointment is cancelled and
`409 Conflict` if the new slot is already occupied.

**Get patient appointments**

`GET /patients/{id}/appointments`

Returns the patient's upcoming appointments sorted by appointment time.
This endpoint was implemented as the assessment bonus requirement.

### Running Locally

**Requirements**
- Python 3.14+
- PostgreSQL
- Git

Clone the repository:
```bash
git clone https://github.com/MwachiraD/clinic-booking-system.git
cd clinic-booking-system
```

Create and activate a virtual environment:
```bash
python -m venv .venv
```
Windows:
```bash
.venv\Scripts\Activate.ps1
```

Install dependencies:
```bash
pip install -r requirements.txt
```

Create a `.env` file:
```
DATABASE_URL=<your PostgreSQL connection string>
```

Run database migrations:
```bash
alembic upgrade head
```

Seed the database:
```bash
python -m scripts.seed
```

Start the API:
```bash
uvicorn app.main:app --reload
```

The API will be available at `http://127.0.0.1:8000`.
Interactive Swagger documentation: `http://127.0.0.1:8000/docs`.

### Automated Tests

The automated tests use a separate SQLite database so that running the test
suite does not modify the development or deployed PostgreSQL database.

Run:
```bash
pytest -v
```

Current test result:
```
13 passed
```

The tests cover scenarios including:
- Successful booking
- Doctor not found
- Patient not found
- Booking outside working hours
- Booking within one hour
- Double booking
- Cancellation
- Cancelling an already-cancelled appointment
- Rescheduling
- Rescheduling a cancelled appointment
- Other booking validation rules

The tests use a separate test database/session so that test execution does
not depend on manually created production appointments.

### Docker

The application includes a Dockerfile for containerized deployment.

Build the image:
```bash
docker build -t clinic-booking-api .
```

Run the container:
```bash
docker run --env-file .env -p 8000:8000 clinic-booking-api
```

The container uses the `PORT` environment variable for the Uvicorn
listening port. Render supplies this value automatically. For local
Docker testing, the `docker run` command above maps host port 8000 to
the container, but the container itself will only listen on port 8000
if `.env` sets `PORT=8000` — otherwise, map to whatever `PORT` is set to.

---

## Section 3: Deployment & CI/CD

The API is deployed as a Docker-based Render Web Service.

**Public API:** https://clinic-booking-system-dvd4.onrender.com

**Interactive API documentation:** https://clinic-booking-system-dvd4.onrender.com/docs

The root `/` endpoint is not defined because this is an API-only
application. Use `/docs` to interact with the API.

The application uses the PostgreSQL database hosted on Render through the
`DATABASE_URL` environment variable.

### Deployment

The application is packaged using Docker with Python 3.14-slim. Render
builds the Docker image and runs the FastAPI application with Uvicorn.

The container listens on port `8000` locally; Render provides the runtime
port through its environment.

- Platform: Render
- Runtime: Docker
- Deployment branch: `main`
- Database: PostgreSQL

Render is connected to the `main` branch and automatically deploys changes
after they are merged.

### CI/CD

A GitHub Actions workflow was added to run the automated test suite on
pull requests targeting `main`. The workflow:

1. Checks out the repository.
2. Sets up Python 3.14.
3. Installs dependencies from `requirements.txt`.
4. Runs the pytest test suite.

The CI environment uses SQLite for testing, while the deployed application
uses PostgreSQL hosted on Render.

The workflow configuration is in place and is running successfully:
GitHub Actions executes on pull requests targeting `main`, runs the test
suite against the SQLite test database, and the pull request was merged
into `main` after CI passed. Render deployment from `main` is working
correctly.

---

## Section 4: AI Reflection

AI tools were used throughout the assessment as a development and learning
aid. I remained responsible for reviewing suggestions, integrating the
code, running the application, testing the API behaviour, debugging
errors, and making the final implementation decisions.

**1. What did you use AI for across the four sections?**

AI was used for:

- Discussing and refining the system design and database models.
- Explaining FastAPI, SQLAlchemy and dependency injection concepts.
- Identifying validation rules and potential edge cases.
- Reviewing implementation approaches for booking, cancellation and
  rescheduling.
- Providing examples and initial structure for some implementation code.
- Providing an initial structure for the automated test suite.
- Troubleshooting API errors using stack traces and observed behaviour.
- Explaining Docker and GitHub Actions concepts while setting up deployment.
- Reviewing and structuring this README.

Some implementation code, including parts of the planned automated test
suite, was adapted from AI-generated suggestions. I reviewed and
integrated this code rather than treating the generated output as
automatically correct.

**2. One example where an AI suggestion improved your work**

One useful example was the database-level prevention of double-booking.

The initial approach could check whether a slot was available before
creating an appointment. AI pointed out that this check alone was not
atomic because two simultaneous requests could both see the slot as
available.

I therefore implemented a PostgreSQL partial unique index on the doctor,
slot and confirmed status. This moves the most important concurrency
guarantee into the database rather than relying only on application-level
checks.

**3. One example where AI output was wrong or incomplete**

During automated testing, the initial test implementation for the
reschedule endpoint used the wrong request field name.

The API expected `slot_start_time`, while the test initially sent
`new_slot_start_time`. This caused FastAPI to return `422 Unprocessable
Entity` rather than the expected business response.

I identified this by running the test suite, inspecting the actual API
route and schema, and correcting the test to match the application's
actual request contract.

This reinforced the importance of running and verifying AI-generated code
rather than assuming that generated code is correct.

A second example came from the seed script. It appeared correct on
inspection but failed when run from a fresh clone with an SQLAlchemy
error that `Appointment` could not be resolved for the `Doctor` model's
relationship. I reproduced the failure, traced it to model registration
(the `Appointment` class was never imported anywhere the seed script's
import chain touched, so SQLAlchemy's mapper configuration couldn't
resolve the string reference), and fixed it at the actual source — by
populating `app/models/__init__.py` to import all four models — rather
than adding an unused `Appointment` import directly into the seed
script just to silence the error.

**4. Two decisions I made without AI**

- **Database choice:** I chose PostgreSQL because the system requires
  relational data, foreign keys, transactions and database-level protection
  against concurrent double-booking.
- **No Slot table:** I decided to generate slots from working hours instead
  of storing every possible slot. Since appointments are fixed at 30
  minutes, the slot can be derived from the doctor's schedule, reducing
  unnecessary stored data and avoiding stale slot records.

---

## Known Limitations

- Timezone handling could be made more explicit and consistently use
  Africa/Nairobi with `zoneinfo`.
- Doctor leave/exceptions are outside the assessment scope.
- Patient registration is outside the assessment scope.
- Render free-tier services may spin down after inactivity, so the first
  request after inactivity may take longer.
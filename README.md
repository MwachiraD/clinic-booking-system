# Clinic Booking System

## Section 1: System Design

### The problem

A small clinic with 5 doctors needs an online booking system. Each doctor has
set working hours and works in 30-minute slots. Patients need to see which
slots are free for a doctor on a given day, book one, and cancel if needed.
Once a slot is booked, it must not be available to anyone else. The system
should be built to scale beyond the initial 5 doctors.

### Models

**Doctor**
- id
- name
- (other basic profile fields as needed)

**WorkingHours**
- id
- doctor_id (FK to Doctor)
- day_of_week
- start_time
- end_time

A doctor can have more than one WorkingHours row for the same day. This is
how a lunch break is represented, for example Monday 08:00-13:00 and Monday
14:00-17:00 as two separate rows, rather than inventing a separate
"lunch break" concept. It also means a doctor's schedule can differ by day
without any special-casing.

**Patient**
- id
- name
- contact details (phone/email)

Patient is a separate model rather than just fields on the appointment. The
brief says the clinic wants to grow, and a standalone Patient model is what
lets the bonus endpoint (a patient's upcoming appointments) exist at all,
and avoids duplicating a patient's details across every booking they make.

**Appointment**
- id
- doctor_id (FK to Doctor)
- patient_id (FK to Patient)
- slot_start_time
- status (confirmed / cancelled)
- cancellation_reason (nullable)

Only `slot_start_time` is stored, not an end time. Every appointment is a
fixed 30-minute slot, so the end time is always `slot_start_time + 30
minutes` and can be derived rather than stored. Storing both would allow
inconsistent data (an end time that doesn't actually match a 30-minute
appointment), for no real benefit.

### Why there is no Slot table

Slots are not stored. They are generated on request from a doctor's
WorkingHours for the requested day, split into 30-minute increments. A
slot is only ever a concept the API computes on the fly, not a row that
exists ahead of time. Storing every possible slot for every doctor for
every future day does not scale well and adds no real value, since the
slots are entirely predictable from the working hours.

### Availability algorithm

Given a doctor and a date:

1. Look up that doctor's WorkingHours rows for the day of the week.
2. Generate 30-minute slots within each working period (each row handles
   itself, so lunch breaks are automatically excluded since no working
   period covers them).
3. Remove any slot whose start time matches an existing **confirmed**
   appointment for that doctor.
4. Remove any slot that starts in the past.
5. (Bonus) Remove any slot starting less than 1 hour from the current time.
6. Return what is left as the available slots.

### Preventing double-booking (the race condition)

Checking availability in application code first and then creating the
appointment is not enough on its own. Two requests can both pass the
"is this slot free" check before either one finishes creating the
appointment, which would double-book the doctor.

To make this impossible rather than just unlikely, the database enforces
it directly: a partial unique constraint on `(doctor_id, slot_start_time)`,
scoped to rows where `status = 'confirmed'`. This means the database will
physically refuse to let two confirmed appointments exist for the same
doctor at the same time, no matter what the application code does.
Cancelled appointments are excluded from the constraint so a cancelled
slot can be rebooked. The exact mechanics of implementing this constraint
depend on the database and ORM chosen, and are worked out concretely in
Section 2 rather than assumed here.

When two booking requests race for the same slot, whichever insert reaches
the database first succeeds. The second insert fails with a database
integrity error. The API catches that error and returns a `409 Conflict`
with a clear message ("This slot is no longer available") instead of
letting the raw database error surface as a 500.

### Booking must re-validate, not trust, the requested time

A patient's booking request is independently validated against the same
rules used to generate availability: it must align to one of the
doctor's actual 30-minute slot boundaries (a request for 10:15 is
rejected even though 10:00-10:30 and 10:30-11:00 are valid), it must
fall within working hours, it must not be in the past, and it must not
already be taken. Availability data shown to a patient can go stale
between the time they view it and the time they submit a booking (another
patient may book the same slot in between), so the booking endpoint never
trusts that a slot is free just because it was listed as available a
moment earlier. The database's unique constraint is the final guarantee
if two requests still race past this validation.

### Cancel

Cancelling sets the appointment's status to cancelled and records a reason.
Because availability is computed by excluding only confirmed appointments,
the slot becomes bookable again automatically, no separate "release" step
is needed. Cancelling an appointment that is already cancelled returns an
error rather than silently succeeding.

### Timezone

The clinic operates in a single location, so all appointment times are
interpreted in the `Africa/Nairobi` timezone, not the server's local time.
This matters because most cloud platforms run servers on UTC by default.
If timestamps aren't explicitly handled as Africa/Nairobi, a patient
booking "9:00 AM" could be stored or compared as 9:00 UTC, which is
actually noon in Nairobi. This kind of bug would not show up in local
testing on a machine already set to East Africa Time, only after
deployment, so it's called out here as an explicit assumption rather than
left implicit.

### Reschedule

Reschedule is not two independent actions (cancel old, book new). It is
handled as a single atomic transaction:

1. Validate the new slot exactly as a fresh booking would be validated
   (working hours, not in the past, not already taken).
2. If valid, release the old slot and book the new one within the same
   transaction.
3. If the new slot is invalid or gets taken by someone else in the
   meantime, the whole operation rolls back and the original appointment
   is left untouched.

Doing this as two separate steps would risk a patient ending up with
no appointment at all if the server failed between releasing the old slot
and booking the new one. Attempting to reschedule an already-cancelled
appointment returns an error.

### Scope decisions and assumptions

- **Doctor leave / exceptions to regular working hours are out of scope.**
  The initial implementation assumes the configured WorkingHours represent
  a doctor's standing weekly schedule. Ad hoc changes (a doctor taking a
  specific day off) are not handled in this version. This is a deliberate
  scoping decision for a 3-5 day assessment rather than an oversight. A
  future version could add a `DoctorAvailabilityException` model to
  override the regular schedule for specific dates without changing this
  design's core structure.
- **Patient records are assumed to already exist before a booking is
  made**, rather than being created inline as part of `POST /appointments`.
  The required endpoint list does not include patient registration, and
  `POST /appointments` takes an existing `patient_id` rather than raw
  patient details. In a fuller system, patients would likely be created
  through a separate registration flow (e.g. at reception, or a dedicated
  endpoint outside this assessment's scope). Doctors and their working
  hours are seeded directly rather than created through the API for the
  same reason: the required endpoints don't call for a doctor-creation
  flow, and the clinic's 5 doctors are a fixed, known set.
- **The 1-hour-minimum-notice rule is treated as the bonus requirement it
  is**, implemented after the core booking flow is working, not before.

### Trade-offs considered

- Dynamically generating slots instead of storing them avoids a table that
  grows indefinitely and would need constant regeneration whenever working
  hours change, at the cost of a small amount of computation on every
  availability request. For a clinic of this size this is a clear win.
- A separate WorkingHours model instead of fields on Doctor costs one extra
  join, but avoids awkward representations of multi-period days and makes
  per-day schedules straightforward to extend later.
- Enforcing the no-double-booking rule at the database level instead of
  only in application code costs a small amount of upfront schema design,
  but is the only way to guarantee correctness under concurrent requests.
# Mergington High School Activities API

A super simple FastAPI application that allows students to view and sign up for extracurricular activities.

## Features

- View all available extracurricular activities
- Sign up for activities
- Staff login, activity management, registration dashboard, and audit log
- Participant details and removal are restricted to staff sessions

## Getting Started

1. Install the dependencies from the repository root:

   ```
   pip install -r requirements.txt
   ```

2. Configure a staff login and start the application from the `src` directory:

   ```
   export ADMIN_USERNAME=staff
   export ADMIN_PASSWORD='choose-a-strong-password'
   export ADMIN_ROLE=admin
   export ADMIN_COOKIE_SECURE=false
   uvicorn app:app --reload
   ```

   `ADMIN_ROLE` can be `admin` or `organizer`. Organizers can manage activities
   and registrations; only admins can archive activities or view the audit log.
   For HTTPS deployments, set `ADMIN_COOKIE_SECURE=true` (the default). Set it
   to `false` only for local HTTP development. Credentials are not stored in
   the repository.

3. Open your browser and go to:
   - API documentation: http://localhost:8000/docs
   - Alternative documentation: http://localhost:8000/redoc

## API Endpoints

| Method | Endpoint                                                          | Description                                                         |
| ------ | ----------------------------------------------------------------- | ------------------------------------------------------------------- |
| GET    | `/activities`                                                     | Get active activities and public capacity counts                    |
| POST   | `/activities/{activity_name}/signup?email=student@mergington.edu` | Sign up for an activity                                             |
| POST   | `/admin/login`                                                    | Sign in and establish an HTTP-only session                          |
| POST   | `/admin/logout`                                                   | Revoke the current session                                          |
| GET    | `/admin/dashboard`                                                | View staff dashboard and recent registrations                       |
| GET    | `/admin/activities`                                               | View activities and participant details                             |
| POST   | `/admin/activities`                                               | Create an activity                                                  |
| PATCH  | `/admin/activities/{activity_name}`                               | Update an activity                                                  |
| POST   | `/admin/activities/{activity_name}/archive`                       | Archive an activity (admin only)                                    |
| GET    | `/admin/activity-log`                                              | View administrative actions (admin only)                            |
| DELETE | `/activities/{activity_name}/unregister?email=...`                | Remove a participant (staff session required)                       |

## Data Model

The application uses a simple data model with meaningful identifiers:

1. **Activities** - Uses activity name as identifier:

   - Description
   - Schedule
   - Maximum number of participants allowed
   - List of student emails who are signed up

2. **Students** - Uses email as identifier:
   - Name
   - Grade level

All activity, registration, session, recent-registration, and audit-log data is
currently stored in memory and resets when the server restarts. Persistent
storage is tracked separately. Run the automated API tests from the repository
root with:

```
python -m unittest discover -s src -p 'test_*.py' -v
```

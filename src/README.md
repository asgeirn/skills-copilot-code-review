# Mergington High School Activities API

A super simple FastAPI application that allows students to view and sign up for extracurricular activities.

## Features

- View all available extracurricular activities
- Sign up for activities

## Getting Started

1. Install the dependencies:

   ```
   pip install fastapi uvicorn
   ```

2. Run the application:

   ```
   python app.py
   ```

3. Open your browser and go to:
   - API documentation: http://localhost:8000/docs
   - Alternative documentation: http://localhost:8000/redoc

## API Endpoints

| Method | Endpoint                                                          | Description                                                                                    |
| ------ | ----------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| GET    | `/activities`                                                     | Get all activities with their details and current participant count                            |
| POST   | `/activities/{activity_name}/signup?email=student@mergington.edu` | Sign up for an activity                                                                        |
| GET    | `/announcements?active_only=true`                                 | List announcements. `active_only=true` returns only started, unexpired ones                    |
| POST   | `/announcements?teacher_username=...`                             | Create an announcement (teacher only). Body: `title`, `message`, `start_date`, `expiration_date` |
| PUT    | `/announcements/{announcement_id}?teacher_username=...`           | Update an announcement (teacher only)                                                          |
| DELETE | `/announcements/{announcement_id}?teacher_username=...`           | Delete an announcement (teacher only)                                                          |

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

3. **Announcements** - Uses a generated id:
   - Title and message shown in the site banner
   - Optional `start_date` (defaults to immediately visible)
   - Required `expiration_date` after which the announcement is hidden
   - Author and audit timestamps

All data is stored in memory, which means data will be reset when the server restarts.

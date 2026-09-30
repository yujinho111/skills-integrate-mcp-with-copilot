"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

from datetime import datetime, timezone
import hmac
import os
from pathlib import Path
import secrets
import time

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

SESSION_COOKIE = "admin_session"
SESSION_TTL_SECONDS = 8 * 60 * 60
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
ADMIN_ROLE = os.getenv("ADMIN_ROLE", "admin").strip().lower()
ADMIN_COOKIE_SECURE = os.getenv("ADMIN_COOKIE_SECURE", "true").lower() == "true"
admin_sessions = {}
activity_log = []
recent_registrations = []


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=256)


class ActivityCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1, max_length=500)
    schedule: str = Field(min_length=1, max_length=200)
    max_participants: int = Field(gt=0)


class ActivityUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, min_length=1, max_length=500)
    schedule: str | None = Field(default=None, min_length=1, max_length=200)
    max_participants: int | None = Field(default=None, gt=0)


def record_action(actor: str, action: str, details: str):
    activity_log.insert(0, {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "actor": actor,
        "action": action,
        "details": details,
    })
    del activity_log[100:]


def require_staff(request: Request):
    token = request.cookies.get(SESSION_COOKIE)
    session = admin_sessions.get(token)
    if not session or session["expires_at"] <= time.time():
        if token:
            admin_sessions.pop(token, None)
        raise HTTPException(status_code=401, detail="Admin login required")
    if session["role"] not in {"admin", "organizer"}:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return {"username": session["username"], "role": session["role"]}


def require_admin(user=Depends(require_staff)):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Administrator role required")
    return user

# In-memory activity database
activities = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
    }
}

for activity in activities.values():
    activity["archived"] = False


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    return {
        name: {
            "description": activity["description"],
            "schedule": activity["schedule"],
            "max_participants": activity["max_participants"],
            "participant_count": len(activity["participants"]),
        }
        for name, activity in activities.items()
        if not activity["archived"]
    }


@app.post("/admin/login")
def login(credentials: LoginRequest, response: Response):
    if not ADMIN_USERNAME or not ADMIN_PASSWORD:
        raise HTTPException(status_code=503, detail="Admin credentials are not configured")
    if ADMIN_ROLE not in {"admin", "organizer"}:
        raise HTTPException(status_code=503, detail="Configured admin role is invalid")
    if not (
        hmac.compare_digest(credentials.username, ADMIN_USERNAME)
        and hmac.compare_digest(credentials.password, ADMIN_PASSWORD)
    ):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = secrets.token_urlsafe(32)
    admin_sessions[token] = {
        "username": ADMIN_USERNAME,
        "role": ADMIN_ROLE,
        "expires_at": time.time() + SESSION_TTL_SECONDS,
    }
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        secure=ADMIN_COOKIE_SECURE,
        samesite="strict",
        path="/",
    )
    record_action(ADMIN_USERNAME, "login", "Signed in")
    return {"username": ADMIN_USERNAME, "role": ADMIN_ROLE}


@app.post("/admin/logout")
def logout(request: Request, response: Response):
    token = request.cookies.get(SESSION_COOKIE)
    session = admin_sessions.pop(token, None) if token else None
    if session:
        record_action(session["username"], "logout", "Signed out")
    response.delete_cookie(
        key=SESSION_COOKIE,
        httponly=True,
        secure=ADMIN_COOKIE_SECURE,
        samesite="strict",
        path="/",
    )
    return {"message": "Signed out"}


@app.get("/admin/session")
def get_admin_session(user=Depends(require_staff)):
    return user


@app.get("/admin/dashboard", dependencies=[Depends(require_staff)])
def get_dashboard():
    active_activities = [activity for activity in activities.values() if not activity["archived"]]
    return {
        "activity_count": len(active_activities),
        "registration_count": sum(len(activity["participants"]) for activity in active_activities),
        "capacity_used": sum(len(activity["participants"]) for activity in active_activities),
        "capacity_total": sum(activity["max_participants"] for activity in active_activities),
        "recent_registrations": recent_registrations[:10],
    }


@app.get("/admin/activities", dependencies=[Depends(require_staff)])
def get_admin_activities():
    return activities


@app.post("/admin/activities", status_code=201)
def create_activity(payload: ActivityCreate, user=Depends(require_staff)):
    if payload.name in activities:
        raise HTTPException(status_code=409, detail="Activity already exists")
    activities[payload.name] = {
        "description": payload.description,
        "schedule": payload.schedule,
        "max_participants": payload.max_participants,
        "participants": [],
        "archived": False,
    }
    record_action(user["username"], "activity_created", payload.name)
    return {"message": f"Created {payload.name}"}


@app.patch("/admin/activities/{activity_name}")
def update_activity(
    activity_name: str,
    payload: ActivityUpdate,
    user=Depends(require_staff),
):
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    updates = {
        key: value
        for key, value in payload.model_dump(exclude_unset=True).items()
        if value is not None
    }
    new_name = updates.pop("name", activity_name)
    if new_name != activity_name and new_name in activities:
        raise HTTPException(status_code=409, detail="Activity already exists")

    activity = activities.pop(activity_name)
    activity.update(updates)
    activities[new_name] = activity
    record_action(user["username"], "activity_updated", new_name)
    return {"message": f"Updated {new_name}"}


@app.post("/admin/activities/{activity_name}/archive")
def archive_activity(activity_name: str, user=Depends(require_admin)):
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")
    activities[activity_name]["archived"] = True
    record_action(user["username"], "activity_archived", activity_name)
    return {"message": f"Archived {activity_name}"}


@app.get("/admin/activity-log", dependencies=[Depends(require_admin)])
def get_activity_log():
    return activity_log


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str):
    """Sign up a student for an activity"""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]
    if activity["archived"]:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Validate student is not already signed up
    if email in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is already signed up"
        )

    # Add student
    activity["participants"].append(email)
    recent_registrations.insert(0, {
        "activity": activity_name,
        "email": email,
        "registered_at": datetime.now(timezone.utc).isoformat(),
    })
    del recent_registrations[10:]
    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(activity_name: str, email: str, user=Depends(require_staff)):
    """Unregister a student from an activity"""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is signed up
    if email not in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is not signed up for this activity"
        )

    # Remove student
    activity["participants"].remove(email)
    record_action(user["username"], "participant_unregistered", f"{email} from {activity_name}")
    return {"message": f"Unregistered {email} from {activity_name}"}

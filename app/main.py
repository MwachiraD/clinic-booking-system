from fastapi import FastAPI

from app.routes import appointments, doctors

app = FastAPI()

app.include_router(appointments.router)
app.include_router(doctors.router)
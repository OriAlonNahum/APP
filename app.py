from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, status
from pydantic import BaseModel, Field, validator
from typing import List, Optional
from datetime import datetime, date, time
import re

# הגדרת האפליקציה עם מטא-דאטה של יוקרה :)
app = FastAPI(
    title="Lisa Alon - Premium Booking API",
    description="High-End Appointment System Backend",
    version="2.0.0"
)

# ----------------- Models & Validations ----------------- #

class AppointmentRequest(BaseModel):
    client_name: str = Field(..., min_length=2, max_length=50)
    client_phone: str
    appointment_date: date
    appointment_time: time

    @validator('client_phone')
    def validate_israel_phone(cls, v):
        # וולידציה פסיכית לטלפון ישראלי (עם או בלי קידומת +972)
        pattern = r"^(?:(?:(\+?972|\b0)5\d{1})-?\d{7})$"
        if not re.match(pattern, str(v).replace(" ", "")):
            raise ValueError('מספר טלפון אינו תקין')
        return v

class AppointmentResponse(AppointmentRequest):
    id: int
    status: str

# ----------------- Mock Database (For Demo) ----------------- #
# במציאות נשתמש ב-SQLAlchemy עם PostgreSQL או Supabase
fake_db_appointments = []

# ----------------- Background Tasks ----------------- #
# פונקציה אסינכרונית שנשלחת לרקע (לא תוקעת את חווית המשתמש!)
def send_whatsapp_confirmation(name: str, phone: str, date: str, time: str):
    """
    כאן מתחברים ל-Twilio או WhatsApp Business API
    זה פועל ברקע אחרי שהלקוח כבר קיבל מסך "הצלחה"
    """
    print(f"✅ [SYSTEM] Sending luxury WhatsApp template to {phone}...")
    print(f"✉️ Message: Hi {name}, your premium appointment with Lisa is set for {date} at {time}.")

# ----------------- Endpoints ----------------- #

@app.get("/api/slots", response_model=List[time])
async def get_available_slots(req_date: date):
    """
    מחזיר רק שעות פנויות, וחותך החוצה שעות שכבר נתפסו ב-DB.
    """
    # הגדרות מנהלת (אפשר להפוך לדינמי ב-DB)
    all_slots = [time(h, m) for h in range(10, 18) for m in (0, 30)]
    
    # סינון שעות תפוסות
    booked_times = [
        appt.appointment_time for appt in fake_db_appointments 
        if appt.appointment_date == req_date and appt.status != "cancelled"
    ]
    
    available_slots = [slot for slot in all_slots if slot not in booked_times]
    return available_slots

@app.post("/api/book", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
async def book_appointment(appointment: AppointmentRequest, background_tasks: BackgroundTasks):
    """
    קביעת תור עם מניעת כפילויות (Race Condition Prevention)
    """
    # בדיקת כפילות תור (Double Booking Prevention)
    is_booked = any(
        a.appointment_date == appointment.appointment_date and 
        a.appointment_time == appointment.appointment_time and 
        a.status == "active" 
        for a in fake_db_appointments
    )
    
    if is_booked:
        raise HTTPException(status_code=400, detail="השעה המבוקשת כבר נתפסה, אנא בחרי שעה אחרת.")
    
    # יצירת התור
    new_appointment = AppointmentResponse(
        id=len(fake_db_appointments) + 1,
        status="active",
        **appointment.dict()
    )
    fake_db_appointments.append(new_appointment)

    # טריגר לשליחת וואטסאפ אסינכרוני
    background_tasks.add_task(
        send_whatsapp_confirmation, 
        appointment.client_name, 
        appointment.client_phone, 
        str(appointment.appointment_date), 
        str(appointment.appointment_time)
    )

    return new_appointment

# ----------------- Admin Routes ----------------- #

def verify_admin_token(token: str):
    # הדמיה של בדיקת JWT (אבטחה!)
    if token != "super-secret-luxury-token-2026":
        raise HTTPException(status_code=403, detail="Not authorized")
    return True

@app.get("/api/admin/appointments")
async def get_all_appointments(token: str):
    verify_admin_token(token)
    return fake_db_appointments

@app.delete("/api/admin/appointments/{appointment_id}")
async def cancel_appointment(appointment_id: int, token: str):
    verify_admin_token(token)
    for appt in fake_db_appointments:
        if appt.id == appointment_id:
            appt.status = "cancelled"
            return {"message": "התור בוטל בהצלחה"}
    raise HTTPException(status_code=404, detail="תור לא נמצא")

# כדי להריץ: uvicorn main:app --reload
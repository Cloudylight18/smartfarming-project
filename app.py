from flask import Flask
from model import db, SystemState, Schedule
from routes_web import web_bp
from routes_api import api_bp, set_actuator
from datetime import datetime, timedelta
import threading
import time
import os
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)

# KONFIGURASI DATABASE DARI .ENV
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)


app.register_blueprint(web_bp)
app.register_blueprint(api_bp)

# BACKGROUND TASK (JADWAL)
def schedule_checker(app):
    """Fungsi ini berjalan di background thread terpisah"""
    while True:
        with app.app_context():
            now = datetime.now()
            current_minute = now.strftime("%H:%M")
            state = SystemState.query.first()  
            if state:
                if state.active_schedule_end and now >= state.active_schedule_end:
                    set_actuator(False, "Waktu Jadwal Selesai")
                    state.active_schedule_end = None
                    db.session.commit()
                if state.mode == "JADWAL":
                    schedules = Schedule.query.all()
                    for sched in schedules:
                        if sched.time_val == current_minute:
                            expected_source = f"Jadwal ({sched.time_val})"
                            if state.actuator_source != expected_source:
                                set_actuator(True, expected_source)
                                state.active_schedule_end = now + timedelta(minutes=sched.duration)
                                db.session.commit()
                            break
        time.sleep(5)

# INISIALISASI & JALANKAN
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        if not SystemState.query.first():
            init_state = SystemState(mode="MANUAL")
            db.session.add(init_state)
            db.session.commit()
    threading.Thread(target=schedule_checker, args=(app,), daemon=True).start()
    app.run(debug=True, host="0.0.0.0", port=5000)
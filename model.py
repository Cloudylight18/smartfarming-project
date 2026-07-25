from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

# Tabel Riwayat Sensor
class SensorData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.now)
    suhu = db.Column(db.Float, default=0.0)
    lembap = db.Column(db.Float, default=0.0)
    tanah = db.Column(db.Float, default=0.0)

# Tabel Jadwal Penyiraman
class Schedule(db.Model):
    id = db.Column(db.String(8), primary_key=True)
    time_val = db.Column(db.String(5)) # Format HH:MM
    duration = db.Column(db.Integer)

# Tabel Log Aktivitas
class SystemLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.now)
    message = db.Column(db.String(255))

# Tabel Status Sistem (Hanya akan berisi 1 baris untuk menyimpan state saat ini)
class SystemState(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mode = db.Column(db.String(20), default="MANUAL")
    actuator_on = db.Column(db.Boolean, default=False)
    actuator_source = db.Column(db.String(50), default="Sistem")
    last_esp32_update = db.Column(db.Float, default=0.0)
    active_schedule_end = db.Column(db.DateTime, nullable=True)
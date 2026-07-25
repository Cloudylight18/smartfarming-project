from flask import Blueprint, request, jsonify, redirect, url_for
from datetime import datetime, timedelta
import uuid
import time
from model import db, SensorData, Schedule, SystemLog, SystemState

api_bp = Blueprint('api_bp', __name__)

# --- BATASAN SOP INTERNASIONAL KADAR AIR TANAH ---
SOIL_DRY_LIMIT = 30.0 
SOIL_WET_LIMIT = 60.0   

def add_log(message):
    new_log = SystemLog(message=message)
    db.session.add(new_log)
    db.session.commit()

def set_actuator(on: bool, source: str):
    state = SystemState.query.first()
    
    if state.actuator_source != source:
        state.actuator_source = source
        db.session.commit()

    # Jika status pompa (ON/OFF) sudah sesuai dengan yang diminta, abaikan proses ke bawah
    if state.actuator_on == on: 
        return
    
    # Jika status pompa berbeda, lakukan perubahan
    state.actuator_on = on
    db.session.commit()
    
    status_teks = "MENYALA" if on else "MATI"
    add_log(f"Pompa {status_teks} - {source}")

# --- HELPER EVALUASI ---
def evaluasi_sensor(suhu, lembap, tanah):
    # Proteksi agar tidak error jika data dari sensor/database bernilai kosong (None)
    tanah = tanah if tanah is not None else 0.0
    suhu = suhu if suhu is not None else 0.0
    lembap = lembap if lembap is not None else 0.0

    # Evaluasi Tanah (SOP Internasional)
    st_tanah = "success" if tanah <= SOIL_WET_LIMIT else "danger"
    st_tanah = "danger" if tanah < SOIL_DRY_LIMIT else st_tanah
    lb_tanah = "TANAH KERING " if tanah < SOIL_DRY_LIMIT else ("LEMBAP IDEAL" if tanah <= SOIL_WET_LIMIT else "BASAH BERLEBIHAN")

    # Evaluasi Suhu
    st_suhu = "success" if suhu < 30 else ("warn" if suhu < 35 else "danger")
    lb_suhu = "NORMAL" if st_suhu == "success" else ("PANAS" if st_suhu == "warn" else "SANGAT PANAS")

    # Evaluasi Kelembapan Udara
    st_lembap = "success" if 40 <= lembap <= 70 else "warn"
    lb_lembap = "NORMAL" if st_lembap == "success" else "WASPADA"

    return (st_tanah, lb_tanah), (st_suhu, lb_suhu), (st_lembap, lb_lembap)

# ================= ROUTES API =================

@api_bp.route("/api/data", methods=["GET"])
def api_data():
    state = SystemState.query.first()
    
    # Ambil 20 data terakhir untuk Chart, reverse (kiri ke kanan)
    history = SensorData.query.order_by(SensorData.timestamp.desc()).limit(20).all()
    history = history[::-1]
    
    # Data terbaru
    latest = history[-1] if history else SensorData()

    # Pastikan data terbaru tidak None sebelum dievaluasi dan dibulatkan
    lat_suhu = latest.suhu if latest.suhu is not None else 0.0
    lat_lembap = latest.lembap if latest.lembap is not None else 0.0
    lat_tanah = latest.tanah if latest.tanah is not None else 0.0

    (tanah_cls, tanah_lbl), (suhu_cls, suhu_lbl), (lembap_cls, lembap_lbl) = evaluasi_sensor(lat_suhu, lat_lembap, lat_tanah)
    
    # Ambil log terbaru & Jadwal
    logs = SystemLog.query.order_by(SystemLog.timestamp.desc()).limit(15).all()
    schedules = Schedule.query.order_by(Schedule.time_val).all()

    # Cek koneksi ESP8266
    data_source = "esp32" if (time.time() - state.last_esp32_update) < 15 else "Terputus"
    if state.last_esp32_update == 0: data_source = "Menunggu"

    return jsonify({
        "now": datetime.now().strftime("%H:%M:%S"),
        "data_source": data_source,
        "mode": state.mode,
        "suhu": round(lat_suhu, 1), "suhu_label": suhu_lbl, "suhu_cls": suhu_cls,
        "lembap": round(lat_lembap, 1), "lembap_label": lembap_lbl, "lembap_cls": lembap_cls,
        "tanah": round(lat_tanah, 1), "tanah_label": tanah_lbl, "tanah_cls": tanah_cls,
        "actuator_on": state.actuator_on,
        "actuator_source": state.actuator_source,
        
        # Data Array untuk Chart (dilindungi dari None)
        "time_history": [d.timestamp.strftime("%H:%M:%S") for d in history],
        "suhu_history": [round(d.suhu if d.suhu is not None else 0.0, 1) for d in history],
        "lembap_history": [round(d.lembap if d.lembap is not None else 0.0, 1) for d in history],
        "tanah_history": [round(d.tanah if d.tanah is not None else 0.0, 1) for d in history],
        
        "schedules": [{"id": s.id, "time": s.time_val, "duration": s.duration} for s in schedules],
        "logs": [f"[{l.timestamp.strftime('%H:%M:%S')}] {l.message}" for l in logs]
    })

@api_bp.route("/api/mode", methods=["POST"])
def change_mode():
    data = request.json
    new_mode = data.get("mode", "MANUAL")
    state = SystemState.query.first()
    state.mode = new_mode
    add_log(f"Mode operasi diubah ke: {new_mode}")
    
    # PERBAIKAN 2: Pastikan jadwal sebelumnya dibatalkan jika pindah mode
    state.active_schedule_end = None 
    db.session.commit()
    
    # PERBAIKAN 3: Setiap ganti mode, POMPA DIMATIKAN DULU, dan teks pemicu dirubah sesuai modenya
    if new_mode == "MANUAL":
        set_actuator(False, "Mode Manual (Klik tombol Air)")
    elif new_mode == "JADWAL":
        set_actuator(False, "Menunggu Waktu Jadwal")
    elif new_mode == "OTOMATIS":
        set_actuator(False, "Menunggu Data dari soil moisture")
        
    return jsonify({"status": "ok"})

@api_bp.route("/aktuator/toggle", methods=["POST"])
def toggle_actuator():
    state = SystemState.query.first()
    if state.mode != "MANUAL":
        return jsonify({"status": "error", "message": "Ubah ke mode MANUAL dulu!"})
    
    set_actuator(not state.actuator_on, "Tombol Web (Manual)")
    return jsonify({"status": "ok"})

@api_bp.route("/schedule/add", methods=["POST"])
def add_schedule():
    time_val = request.form.get("time")
    duration_val = int(request.form.get("duration", 15))
    if time_val:
        new_sched = Schedule(id=str(uuid.uuid4())[:8], time_val=time_val, duration=duration_val)
        db.session.add(new_sched)
        db.session.commit()
        add_log(f"Jadwal ditambahkan: {time_val} ({duration_val} mnt)")
    return redirect("/")

@api_bp.route("/schedule/delete/<sched_id>", methods=["POST"])
def delete_schedule(sched_id):
    sched = Schedule.query.get(sched_id)
    if sched:
        db.session.delete(sched)
        db.session.commit()
        add_log("Jadwal dihapus")
    return jsonify({"status": "ok"})

# Endpoint untuk ESP8266
@api_bp.route("/api/sensors", methods=["POST"])
def api_receive_sensors():
    data = request.get_json(silent=True) or request.form
    try:
        suhu = float(data.get("suhu", 0))
        lembap = float(data.get("lembap", 0))
        tanah = float(data.get("tanah", 0))
        tanah = max(0.0, min(100.0, tanah))
    except (TypeError, ValueError):
        return jsonify({"status": "error"}), 400

    # 1. Simpan Data Sensor ke DB
    new_data = SensorData(suhu=suhu, lembap=lembap, tanah=tanah)
    db.session.add(new_data)
    
    # 2. Update Status Update Terakhir ESP8266
    state = SystemState.query.first()
    state.last_esp32_update = time.time()
    db.session.commit()
    
    # 3. Evaluasi Mode Otomatis (Berdasarkan Kelembapan Tanah)
    if state.mode == "OTOMATIS":
        if tanah < SOIL_DRY_LIMIT and not state.actuator_on:
            set_actuator(True, f"Auto: Tanah Kering Kritis (<{SOIL_DRY_LIMIT}%)")
        elif tanah >= 40.0 and state.actuator_on: 
            # Pompa mati jika air sudah mencapai 40% (masuk ambang ideal)
            set_actuator(False, f"Auto: Tanah Sudah Ideal (>=40%)")

    return jsonify({"status": "ok", "actuator_on": state.actuator_on})
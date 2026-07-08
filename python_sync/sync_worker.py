import pymysql
import requests
import time
import os

# ----------------------------------------------------
# 1. LOAD KONFIGURASI DARI .ENV LARAVEL
# ----------------------------------------------------
def load_env(filepath=".env"):
    # Coba baca dari folder yang sama, atau folder parent
    paths_to_try = [filepath, os.path.join(os.path.dirname(__file__), "..", filepath)]
    for path in paths_to_try:
        if os.path.exists(path):
            with open(path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, val = line.split("=", 1)
                        os.environ[key.strip()] = val.strip().strip("'").strip('"')
            break

load_env()

# ----------------------------------------------------
# 2. SETUP VARIABEL & DATABASE DINAMIS
# ----------------------------------------------------
LOCAL_ROLE = os.environ.get("SERVER_ROLE", "lokal")
TARGET_ROLE = "vps" if LOCAL_ROLE == "lokal" else "lokal"

BASE_URL = os.environ.get("SYNC_URL", "http://127.0.0.1:8000/api")
SYNC_TOKEN = os.environ.get("SYNC_SECRET_KEY", "SyncSecretToken2026Secure")

SLAVE_URL = os.environ.get("SLAVE_URL", "")
SLAVE_TOKEN = os.environ.get("SLAVE_SYNC_TOKEN", "")

db_config = {
    "user": os.environ.get("DB_USERNAME", "root"),
    "password": os.environ.get("DB_PASSWORD", ""),
    "database": os.environ.get("DB_DATABASE", "rawat_inap"),
}

# Cek apakah environment pakai socket (seperti VPS) atau host biasa
db_socket = os.environ.get("DB_SOCKET")
if db_socket:
    db_config["unix_socket"] = db_socket
else:
    db_config["host"] = os.environ.get("DB_HOST", "127.0.0.1")
    db_port = os.environ.get("DB_PORT")
    if db_port:
        db_config["port"] = int(db_port)

last_errors = {}

# ----------------------------------------------------
# 3. FUNGSI LOG SINKRONISASI
# ----------------------------------------------------
def save_sync_log(cursor, table_name, action_type, data_uuid, source_server, target_server, sync_status, duration_ms, message):
    query = """
    INSERT INTO sync_log (table_name, action_type, data_uuid, source_server, target_server, sync_status, sync_duration_ms, message, created_at, updated_at)
    VALUES (%s,%s,%s,%s,%s,%s,%s,%s, NOW(),NOW())
    """
    cursor.execute(query, (table_name, action_type, data_uuid, source_server, target_server, sync_status, duration_ms, message))

# ----------------------------------------------------
# 4. FUNGSI PUSH DATA (LOKAL -> TARGET)
# ----------------------------------------------------
def sync_data(table_name, endpoint):
    db = pymysql.connect(**db_config)
    cursor = db.cursor(pymysql.cursors.DictCursor)

    print(f"\n[PUSH {table_name.upper()}]")
    print(f"CEK DATA PENDING DI {LOCAL_ROLE.upper()}...")

    query = f"SELECT * FROM {table_name} WHERE status_sync='pending' AND source_server='{LOCAL_ROLE}'"
    cursor.execute(query)
    hasil = cursor.fetchall()

    if not hasil:
        print(f"TIDAK ADA DATA PENDING DI {LOCAL_ROLE.upper()}")
        db.close()
        return

    for item in hasil:
        for key, value in item.items():
            if value is not None:
                item[key] = str(value)
    try:
        ids = [str(item['id']) for item in hasil]
        cursor.execute(f"UPDATE {table_name} SET status_sync='syncing' WHERE id IN ({','.join(ids)})")
        db.commit()

        start_time = time.time()
        response = requests.post(
            f"{BASE_URL}/{endpoint}",
            json=hasil,
            headers={"Content-Type": "application/json", "Accept": "application/json", "X-Sync-Token": SYNC_TOKEN},
            timeout=10
        )
        duration_ms = int((time.time() - start_time) * 1000)

        print("STATUS :", response.status_code)
        print("RESPON :", response.text)
        print(f"DURATION : {duration_ms} ms")

        if response.status_code == 200 and response.json().get("success"):
            cursor.execute(f"UPDATE {table_name} SET status_sync='synced', synced_at=NOW() WHERE id IN ({','.join(ids)})")
            for item in hasil:
                save_sync_log(cursor, table_name, item["action_type"], item["uuid"], LOCAL_ROLE, TARGET_ROLE, "success", duration_ms, f"Push {table_name} berhasil")
            db.commit()
            print(f"PUSH {table_name.upper()} BERHASIL")
            last_errors[table_name] = None
        else:
            for item in hasil:
                save_sync_log(cursor, table_name, item["action_type"], item["uuid"], LOCAL_ROLE, TARGET_ROLE, "failed", duration_ms, response.text)
            cursor.execute(f"UPDATE {table_name} SET status_sync='pending' WHERE id IN ({','.join(ids)})")
            db.commit()
            print(f"PUSH {table_name.upper()} GAGAL")
    
    except Exception as e:
        error_message = str(e)
        clean_message = f"SERVER {TARGET_ROLE.upper()} OFFLINE / TIDAK TERHUBUNG" if "Failed to establish a new connection" in error_message else error_message
        print(f"PUSH {table_name.upper()} GAGAL - ERROR:", clean_message)

        if last_errors.get(table_name) != clean_message:
            for item in hasil:
                save_sync_log(cursor, table_name, item["action_type"], item["uuid"], LOCAL_ROLE, TARGET_ROLE, "failed", 0, clean_message)
            db.commit()
            last_errors[table_name] = clean_message

        cursor.execute(f"UPDATE {table_name} SET status_sync='pending' WHERE id IN ({','.join(ids)})")
        db.commit()
    finally:
        db.close()

# ----------------------------------------------------
# 5. FUNGSI PULL DATA (TARGET -> LOKAL)
# ----------------------------------------------------
def pull_and_sync_data(table_name, pull_endpoint, ack_endpoint):
    db = pymysql.connect(**db_config)
    cursor = db.cursor(pymysql.cursors.DictCursor)

    print(f"\n[PULL {table_name.upper()}]")
    print(f"MENGAMBIL DATA DARI {TARGET_ROLE.upper()}...")

    try:
        response = requests.get(
            f"{BASE_URL}/{pull_endpoint}",
            headers={"Accept": "application/json", "X-Sync-Token": SYNC_TOKEN},
            timeout=10
        )

        if response.status_code != 200:
            print(f"PULL {table_name.upper()} GAGAL - Status: {response.status_code}")
            return

        hasil = response.json()
        if not hasil:
            print(f"TIDAK ADA DATA PENDING DI {TARGET_ROLE.upper()}")
            return

        print(f"MENERIMA {len(hasil)} DATA PENDING DARI {TARGET_ROLE.upper()}")
        synced_uuids = []
        start_time = time.time()

        allowed_columns = {
            'pasien': ['uuid', 'no_rm', 'nama', 'jenis_kelamin', 'tanggal_lahir', 'dokter_id', 'dokter_uuid', 'status', 'tanggal_keluar', 'catatan_keluar', 'is_active', 'status_sync', 'source_server', 'action_type', 'is_deleted', 'created_at', 'updated_at'],
            'visit': ['uuid', 'pasien_id', 'dokter_id', 'pasien_uuid', 'dokter_uuid', 'keluhan', 'diagnosa', 'tindakan', 'status_sync', 'source_server', 'action_type', 'created_at', 'updated_at'],
            'users': ['uuid', 'name', 'email', 'password', 'role', 'status_sync', 'source_server', 'action_type', 'created_at', 'updated_at']
        }.get(table_name, [])

        for item in hasil:
            uuid_val = item.get('uuid')
            if not uuid_val: continue

            for k, v in item.items():
                if v in ['None', 'null', '', None]: item[k] = None
                elif k in ['is_active', 'is_deleted'] and v is not None: item[k] = 1 if str(v).lower() in ['true', '1'] else 0
                elif k in ['created_at', 'updated_at', 'synced_at'] and v is not None: item[k] = str(v).replace('T', ' ').split('.')[0].rstrip('Z')
                elif k in ['tanggal_lahir', 'tanggal_keluar'] and v is not None: item[k] = str(v).split('T')[0]

            if table_name in ['pasien', 'visit']:
                d_uuid = item.get('dokter_uuid')
                if d_uuid:
                    cursor.execute("SELECT id FROM users WHERE uuid = %s", (d_uuid,))
                    res = cursor.fetchone()
                    item['dokter_id'] = res['id'] if res else None
                else: item['dokter_id'] = None

            if table_name == 'visit':
                p_uuid = item.get('pasien_uuid')
                if p_uuid:
                    cursor.execute("SELECT id FROM pasien WHERE uuid = %s", (p_uuid,))
                    res = cursor.fetchone()
                    item['pasien_id'] = res['id'] if res else None
                else: item['pasien_id'] = None

            for col in allowed_columns:
                if col not in item: item[col] = None

            cursor.execute(f"SELECT * FROM {table_name} WHERE uuid = %s", (uuid_val,))
            existing = cursor.fetchone()

            if not existing:
                item['status_sync'] = 'synced'
                placeholders = [f"%({c})s" for c in allowed_columns] + ['NOW()']
                cursor.execute(f"INSERT INTO {table_name} ({', '.join(allowed_columns)}, synced_at) VALUES ({', '.join(placeholders)})", item)
                print(f"INSERT LOKAL BERHASIL: {uuid_val}")
            else:
                target_updated = item.get('updated_at')
                local_updated = existing.get('updated_at')
                is_newer = str(target_updated) > str(local_updated) if target_updated and local_updated else bool(target_updated)

                if is_newer:
                    item['status_sync'] = 'synced'
                    update_parts = [f"{c} = %({c})s" for c in allowed_columns if c not in ['uuid', 'created_at']] + ["synced_at = NOW()"]
                    cursor.execute(f"UPDATE {table_name} SET {', '.join(update_parts)} WHERE uuid = %(uuid)s", item)
                    print(f"UPDATE LOKAL BERHASIL: {uuid_val}")
                else:
                    print(f"SKIP UPDATE ({LOCAL_ROLE.upper()} LEBIH BARU/SAMA): {uuid_val}")

            synced_uuids.append(uuid_val)

        db.commit()

        if synced_uuids:
            duration_ms = int((time.time() - start_time) * 1000)
            ack_res = requests.post(
                f"{BASE_URL}/{ack_endpoint}",
                json={"uuids": synced_uuids},
                headers={"Content-Type": "application/json", "Accept": "application/json", "X-Sync-Token": SYNC_TOKEN},
                timeout=10
            )

            if ack_res.status_code == 200 and ack_res.json().get("success"):
                print(f"ACK PULL {table_name.upper()} SUKSES DI {TARGET_ROLE.upper()}")
                for uuid_val in synced_uuids:
                    save_sync_log(cursor, table_name, "pull_insert", uuid_val, TARGET_ROLE, LOCAL_ROLE, "success", duration_ms, f"Pull sync {table_name} berhasil")
                db.commit()
            else:
                print(f"ACK PULL {table_name.upper()} GAGAL DI {TARGET_ROLE.upper()}: {ack_res.text}")

    except Exception as e:
        print(f"PULL {table_name.upper()} ERROR:", str(e))
        db.rollback()
    finally:
        db.close()

# ----------------------------------------------------
# 6. FUNGSI DISASTER RECOVERY (TARGET -> LOKAL)
# ----------------------------------------------------
def recover_lost_data(table_name, endpoint):
    db = pymysql.connect(**db_config)
    cursor = db.cursor(pymysql.cursors.DictCursor)

    print(f"\n[RECOVERY {table_name.upper()}]")
    print(f"MENGAMBIL DATA RECOVERY DARI {TARGET_ROLE.upper()}...")

    try:
        response = requests.get(
            f"{BASE_URL}/{endpoint}",
            headers={"Accept": "application/json", "X-Sync-Token": SYNC_TOKEN},
            timeout=15
        )

        if response.status_code != 200:
            print(f"RECOVERY {table_name.upper()} GAGAL - Status: {response.status_code}")
            return

        hasil = response.json()
        if not hasil:
            print(f"TIDAK ADA DATA RECOVERY DI {TARGET_ROLE.upper()}")
            return

        print(f"MENERIMA {len(hasil)} DATA RECOVERY DARI {TARGET_ROLE.upper()}")

        recovered_count = 0
        updated_count = 0
        start_time = time.time()

        allowed_columns = {
            'pasien': ['uuid', 'no_rm', 'nama', 'jenis_kelamin', 'tanggal_lahir', 'dokter_id', 'dokter_uuid', 'status', 'tanggal_keluar', 'catatan_keluar', 'is_active', 'status_sync', 'source_server', 'action_type', 'is_deleted', 'created_at', 'updated_at'],
            'visit': ['uuid', 'pasien_id', 'dokter_id', 'pasien_uuid', 'dokter_uuid', 'keluhan', 'diagnosa', 'tindakan', 'status_sync', 'source_server', 'action_type', 'created_at', 'updated_at'],
            'users': ['uuid', 'name', 'email', 'password', 'role', 'status_sync', 'source_server', 'action_type', 'created_at', 'updated_at']
        }.get(table_name, [])

        for item in hasil:
            uuid_val = item.get('uuid')
            if not uuid_val: continue

            for k, v in item.items():
                if v in ['None', 'null', '', None]: item[k] = None
                elif k in ['is_active', 'is_deleted'] and v is not None: item[k] = 1 if str(v).lower() in ['true', '1'] else 0
                elif k in ['created_at', 'updated_at', 'synced_at'] and v is not None: item[k] = str(v).replace('T', ' ').split('.')[0].rstrip('Z')
                elif k in ['tanggal_lahir', 'tanggal_keluar'] and v is not None: item[k] = str(v).split('T')[0]

            if table_name in ['pasien', 'visit']:
                d_uuid = item.get('dokter_uuid')
                if d_uuid:
                    cursor.execute("SELECT id FROM users WHERE uuid = %s", (d_uuid,))
                    res = cursor.fetchone()
                    item['dokter_id'] = res['id'] if res else None
                else: item['dokter_id'] = None

            if table_name == 'visit':
                p_uuid = item.get('pasien_uuid')
                if p_uuid:
                    cursor.execute("SELECT id FROM pasien WHERE uuid = %s", (p_uuid,))
                    res = cursor.fetchone()
                    item['pasien_id'] = res['id'] if res else None
                else: item['pasien_id'] = None

            for col in allowed_columns:
                if col not in item: item[col] = None

            cursor.execute(f"SELECT * FROM {table_name} WHERE uuid = %s", (uuid_val,))
            existing = cursor.fetchone()

            if not existing:
                item['status_sync'] = 'synced'
                placeholders = [f"%({c})s" for c in allowed_columns] + ['NOW()']
                cursor.execute(f"INSERT INTO {table_name} ({', '.join(allowed_columns)}, synced_at) VALUES ({', '.join(placeholders)})", item)
                print(f"PEMULIHAN INSERT BERHASIL: {uuid_val}")
                recovered_count += 1
            else:
                target_updated = item.get('updated_at')
                local_updated = existing.get('updated_at')
                is_newer = str(target_updated) > str(local_updated) if target_updated and local_updated else bool(target_updated)

                if is_newer:
                    item['status_sync'] = 'synced'
                    update_parts = [f"{c} = %({c})s" for c in allowed_columns if c not in ['uuid', 'created_at']] + ["synced_at = NOW()"]
                    cursor.execute(f"UPDATE {table_name} SET {', '.join(update_parts)} WHERE uuid = %(uuid)s", item)
                    print(f"PEMULIHAN UPDATE BERHASIL: {uuid_val}")
                    updated_count += 1

        db.commit()
        duration_ms = int((time.time() - start_time) * 1000)

        if recovered_count > 0 or updated_count > 0:
            print(f"RECOVERY {table_name.upper()} SELESAI: {recovered_count} DATA DIPULIHKAN, {updated_count} DATA DIUPDATE")
            save_sync_log(cursor, table_name, "recovery", "-", TARGET_ROLE, LOCAL_ROLE, "success", duration_ms, f"Recovery selesai. {recovered_count} dipulihkan, {updated_count} diupdate.")
            db.commit()
        else:
            print(f"RECOVERY {table_name.upper()} SELESAI: TIDAK ADA DATA {LOCAL_ROLE.upper()} YANG HILANG/TERTANDINGI")

    except Exception as e:
        print(f"RECOVERY {table_name.upper()} ERROR:", str(e))
        db.rollback()
    finally:
        db.close()


# ----------------------------------------------------
# 6b. FUNGSI DISASTER RECOVERY DARI SERVER SLAVE
# ----------------------------------------------------
def recover_from_slave(table_name, endpoint):
    if not SLAVE_URL:
        print(f"\n[SLAVE RECOVERY {table_name.upper()}] SLAVE_URL tidak dikonfigurasi, skip.")
        return

    db = pymysql.connect(**db_config)
    cursor = db.cursor(pymysql.cursors.DictCursor)

    print(f"\n[SLAVE RECOVERY {table_name.upper()}]")
    print(f"MENGAMBIL DATA RECOVERY DARI SERVER SLAVE ({SLAVE_URL})...")

    try:
        response = requests.get(
            f"{SLAVE_URL}/{endpoint}",
            headers={"Accept": "application/json", "X-Sync-Token": SLAVE_TOKEN},
            timeout=15
        )

        if response.status_code != 200:
            print(f"SLAVE RECOVERY {table_name.upper()} GAGAL - Status: {response.status_code}")
            return

        hasil = response.json()
        if not hasil:
            print(f"TIDAK ADA DATA RECOVERY DI SERVER SLAVE")
            return

        print(f"MENERIMA {len(hasil)} DATA RECOVERY DARI SERVER SLAVE")

        recovered_count = 0
        updated_count = 0
        start_time = time.time()

        allowed_columns = {
            'pasien': ['uuid', 'no_rm', 'nama', 'jenis_kelamin', 'tanggal_lahir', 'dokter_id', 'dokter_uuid', 'status', 'tanggal_keluar', 'catatan_keluar', 'is_active', 'status_sync', 'source_server', 'action_type', 'is_deleted', 'created_at', 'updated_at'],
            'visit': ['uuid', 'pasien_id', 'dokter_id', 'pasien_uuid', 'dokter_uuid', 'keluhan', 'diagnosa', 'tindakan', 'status_sync', 'source_server', 'action_type', 'created_at', 'updated_at'],
            'users': ['uuid', 'name', 'email', 'password', 'role', 'status_sync', 'source_server', 'action_type', 'created_at', 'updated_at']
        }.get(table_name, [])

        for item in hasil:
            uuid_val = item.get('uuid')
            if not uuid_val: continue

            for k, v in item.items():
                if v in ['None', 'null', '', None]: item[k] = None
                elif k in ['is_active', 'is_deleted'] and v is not None: item[k] = 1 if str(v).lower() in ['true', '1'] else 0
                elif k in ['created_at', 'updated_at', 'synced_at'] and v is not None: item[k] = str(v).replace('T', ' ').split('.')[0].rstrip('Z')
                elif k in ['tanggal_lahir', 'tanggal_keluar'] and v is not None: item[k] = str(v).split('T')[0]

            if table_name in ['pasien', 'visit']:
                d_uuid = item.get('dokter_uuid')
                if d_uuid:
                    cursor.execute("SELECT id FROM users WHERE uuid = %s", (d_uuid,))
                    res = cursor.fetchone()
                    item['dokter_id'] = res['id'] if res else None
                else: item['dokter_id'] = None

            if table_name == 'visit':
                p_uuid = item.get('pasien_uuid')
                if p_uuid:
                    cursor.execute("SELECT id FROM pasien WHERE uuid = %s", (p_uuid,))
                    res = cursor.fetchone()
                    item['pasien_id'] = res['id'] if res else None
                else: item['pasien_id'] = None

            for col in allowed_columns:
                if col not in item: item[col] = None

            cursor.execute(f"SELECT * FROM {table_name} WHERE uuid = %s", (uuid_val,))
            existing = cursor.fetchone()

            if not existing:
                item['status_sync'] = 'synced'
                placeholders = [f"%({c})s" for c in allowed_columns] + ['NOW()']
                cursor.execute(f"INSERT INTO {table_name} ({', '.join(allowed_columns)}, synced_at) VALUES ({', '.join(placeholders)})", item)
                print(f"PEMULIHAN SLAVE INSERT BERHASIL: {uuid_val}")
                recovered_count += 1
            else:
                target_updated = item.get('updated_at')
                local_updated = existing.get('updated_at')
                is_newer = str(target_updated) > str(local_updated) if target_updated and local_updated else bool(target_updated)

                if is_newer:
                    item['status_sync'] = 'synced'
                    update_parts = [f"{c} = %({c})s" for c in allowed_columns if c not in ['uuid', 'created_at']] + ["synced_at = NOW()"]
                    cursor.execute(f"UPDATE {table_name} SET {', '.join(update_parts)} WHERE uuid = %(uuid)s", item)
                    print(f"PEMULIHAN SLAVE UPDATE BERHASIL: {uuid_val}")
                    updated_count += 1

        db.commit()
        duration_ms = int((time.time() - start_time) * 1000)

        if recovered_count > 0 or updated_count > 0:
            print(f"SLAVE RECOVERY {table_name.upper()} SELESAI: {recovered_count} DATA DIPULIHKAN, {updated_count} DATA DIUPDATE")
            save_sync_log(cursor, table_name, "recovery_slave", "-", "slave", LOCAL_ROLE, "success", duration_ms, f"Slave recovery selesai. {recovered_count} dipulihkan, {updated_count} diupdate.")
            db.commit()
        else:
            print(f"SLAVE RECOVERY {table_name.upper()} SELESAI: TIDAK ADA DATA SLAVE YANG BARU ATAU HILANG")

    except Exception as e:
        print(f"SLAVE RECOVERY {table_name.upper()} ERROR:", str(e))
        db.rollback()
    finally:
        db.close()


# ----------------------------------------------------
# 7. MAIN WORKER LOOP
# ----------------------------------------------------
if __name__ == "__main__":
    print(f"\n=== WORKER BERJALAN SEBAGAI: {LOCAL_ROLE.upper()} ===")
    print(f"=== MENGHUBUNGI TARGET: {TARGET_ROLE.upper()} ({BASE_URL}) ===\n")

    # -------------------------------------------------------
    # DISASTER RECOVERY saat pertama kali worker dijalankan
    # -------------------------------------------------------
    print("=== MENJALANKAN DISASTER RECOVERY TAHAP 1 (DARI LOKAL/MASTER) ===")
    recover_lost_data("users", "sync/all-users")
    recover_lost_data("pasien", "sync/all-pasien")
    recover_lost_data("visit", "sync/all-visit")
    
    print("\n=== MENJALANKAN DISASTER RECOVERY TAHAP 2 (DARI SERVER SLAVE) ===")
    recover_from_slave("users", "sync/all-users")
    recover_from_slave("pasien", "sync/all-pasien")
    recover_from_slave("visit", "sync/all-visit")
    print("=== DISASTER RECOVERY SELESAI. MASUK KE LOOP SINKRONISASI ===\n")

    # Interval recovery berkala: setiap 60 siklus x 5 detik = ±5 menit
    RECOVERY_INTERVAL = 60
    loop_counter = 0

    while True:
        # PUSH: kirim data pending dari lokal ke target
        sync_data("pasien", "sync/pasien")
        sync_data("visit", "sync/visit")
        sync_data("users", "sync/users")

        # PULL: ambil data pending dari target ke lokal
        pull_and_sync_data("pasien", "sync/pull-pasien", "sync/acknowledge-pasien")
        pull_and_sync_data("visit", "sync/pull-visit", "sync/acknowledge-visit")
        pull_and_sync_data("users", "sync/pull-users", "sync/acknowledge-users")

        # -------------------------------------------------------
        # PERIODIC SELF-RECOVERY: setiap ±5 menit
        # -------------------------------------------------------
        loop_counter += 1
        if loop_counter >= RECOVERY_INTERVAL:
            print("\n=== [PERIODIC SELF-RECOVERY] CEK DATA YANG HILANG DARI TARGET ===")
            recover_lost_data("users",  "sync/all-users")
            recover_lost_data("pasien", "sync/all-pasien")
            recover_lost_data("visit",  "sync/all-visit")
            
            print("\n=== [PERIODIC SELF-RECOVERY] CEK DATA YANG HILANG DARI SLAVE ===")
            recover_from_slave("users",  "sync/all-users")
            recover_from_slave("pasien", "sync/all-pasien")
            recover_from_slave("visit",  "recovery/all-visit") # Jika di slave routing-nya diatur recovery/all-visit
            print("=== [PERIODIC SELF-RECOVERY] SELESAI ===\n")
            loop_counter = 0  # reset counter

        # Jeda 5 detik setiap siklus
        time.sleep(5)
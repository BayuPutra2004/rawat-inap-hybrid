# Sistem Rawat Inap Hibrida: Two-Way Synchronization & Self-Healing Disaster Recovery

> **Tugas Akhir / Proyek Penelitian Skripsi**  
> Program Studi Teknologi Rekayasa Komputer Jaringan (TRKJ) – Politeknik Negeri Lhokseumawe  
> Pengembang: **Bayu Angkasa Putra**

---

## Latar Belakang Masalah
Fasilitas layanan kesehatan di berbagai daerah sering kali mengalami kendala konektivitas internet yang tidak stabil. Putusnya jaringan dapat mengganggu proses pencatatan rekam medis rawat inap dan kunjungan dokter. Proyek penelitian ini merancang sistem **arsitektur hibrida (offline-to-cloud)** yang memungkinkan operasional rumah sakit tetap berjalan lancar saat offline, dan secara otomatis melakukan sinkronisasi data dua arah ketika jaringan kembali terhubung tanpa risiko duplikasi data.

---

## Fitur Utama & Kemampuan Sistem

### 1. Manajemen Rawat Inap & Rekam Medis (RESTful API)
- **Autentikasi Aman:** Menggunakan **Laravel Sanctum** untuk pengelolaan sesi dokter dan staf medis berbasis token.
- **Manajemen Pasien & Dokter:** CRUD data pasien, status aktif, riwayat kunjungan (*visit*), dan prosedur kepulangan pasien.
- **Pencatatan Kunjungan (*Doctor Visits*):** Tracking riwayat pemeriksaan dokter terhadap pasien secara terstruktur.

### 2. Arsitektur Sinkronisasi Dua Arah (*Two-Way Data Sync*)
- **Mekanisme Pull & Acknowledge:** Mencegah terjadinya konflik dan duplikasi data (*race condition*) antar-node database.
- **Pendeteksian Perubahan Data:** Implementasi *soft delete* dan *sync flag* untuk melacak data yang perlu dikirim ke cloud atau ditarik ke lokal.
- **Keamanan Endpoint Sinkronisasi:** Proteksi jalur sinkronisasi data menggunakan custom middleware `VerifySyncToken`.

### 3. Disaster Recovery & Self-Healing
- **Pemulihan Otomatis (*Self-Healing*):** Fitur pemulihan berkala (*periodic recovery / recover from slave*) setiap 5 menit untuk memastikan konsistensi antara database lokal dan slave/cloud.
- **Ketahanan Jaringan:** Sistem dirancang tetap tangguh meskipun terjadi *packet loss* atau gangguan jaringan lokal.

### 4. Background Python Worker Engine
- Dilengkapi dengan *worker* latar belakang mandiri (`python_sync/sync_worker.py`) menggunakan **Python 3**, **PyMySQL**, dan **Requests** untuk mengeksekusi proses sinkronisasi secara non-blocking terhadap aplikasi web utama.

---

## Tech Stack

- **Backend Framework:** Laravel (PHP 8.x)
- **API Authentication:** Laravel Sanctum
- **Background Sync Engine:** Python 3 (PyMySQL, Requests)
- **Database:** MySQL
- **Networking & Tunneling:** Ngrok Tunneling & Reverse Proxy

---

## Alur Kerja Sinkronisasi (Architecture Flow)

```mermaid
graph TD
    subgraph Local Node (Rumah Sakit)
        LocalApp[Web / Mobile Client] --> LocalDB[(Local MySQL)]
        Worker[Python Sync Worker] -->|Membaca Perubahan Data| LocalDB
    end

    subgraph Cloud Node (Server Pusat)
        CloudAPI[Laravel API Server] --> CloudDB[(Cloud MySQL)]
    end

    Worker -->|Push Data & VerifySyncToken| CloudAPI
    CloudAPI -->|Acknowledge Response| Worker
    CloudAPI -->|Pull Pending Data / Self-Healing| Worker
```

<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Support\Str;

class Pasien extends Model
{
    protected $table = 'pasien';

    protected $fillable = [
        'no_rm',
        'nama',
        'jenis_kelamin',
        'tanggal_lahir',
        'dokter_id',
        'dokter_uuid',
        'is_active',
        'status',
        'tanggal_keluar',
        'catatan_keluar',

        // FIELD SINKRONISASI
        'uuid',
        'status_sync',
        'synced_at',
        'source_server',
        'action_type',
        'is_deleted'
    ];

    /**
     * Boot method untuk auto isi data saat create & update
     */
    protected static function boot()
    {
        parent::boot();

        // Saat INSERT data baru
        static::creating(function ($model) {

            if (!$model->uuid) {
                $model->uuid = Str::uuid();
            }

            // jangan override saat hasil sync
            if (!$model->status_sync) {
                $model->status_sync = 'pending';
            }

            // otomatis ambil role server
            if (!$model->source_server) {
                $model->source_server = env('SERVER_ROLE', 'lokal');
            }
        });

        // Saat UPDATE data
        static::updating(function ($model) {
        // jangan reset saat proses sync sukses
            if ($model->status_sync !== 'synced') {
                $model->status_sync = 'pending';
            }

        });
    }

    /**
     * Relasi ke dokter (user)
     */
    public function dokter()
    {
        return $this->belongsTo(\App\Models\User::class, 'dokter_id');
    }
}
<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Support\Str;

class Visit extends Model
{
    protected $table = 'visit';

    protected $fillable = [
        'pasien_id',
        'dokter_id',
        'pasien_uuid',
        'dokter_uuid',
        'keluhan',
        'diagnosa',
        'tindakan',

        // FIELD SYNC
        'uuid',
        'status_sync',
        'synced_at',
        'source_server',
        'action_type',
    ];

    /**
     * AUTO HANDLE SYNC
     */
    protected static function boot()
    {
        parent::boot();

        // Saat create
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

        // Saat update
        static::updating(function ($model) {

            // jangan ubah saat proses sync berhasil
            if ($model->status_sync !== 'synced') {
                $model->status_sync = 'pending';
            }

        });
    }

    // RELASI KE PASIEN
    public function pasien()
    {
        return $this->belongsTo(\App\Models\Pasien::class, 'pasien_id');
    }

    // RELASI KE DOKTER
    public function dokter()
    {
        return $this->belongsTo(\App\Models\User::class, 'dokter_id');
    }
}
<?php

namespace Database\Seeders;

use Illuminate\Database\Seeder;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Hash;
use Illuminate\Support\Str;
use Carbon\Carbon;

class SemproSeeder extends Seeder
{
    /**
     * Run the database seeds.
     *
     * @return void
     */
    public function run()
    {
        $serverRole = env('SERVER_ROLE', 'lokal');
        
        // 1. Buat 5 Dokter
        $dokterIds = [];
        for ($i = 1; $i <= 5; $i++) {
            $uuid = (string) Str::uuid();
            $id = DB::table('users')->insertGetId([
                'uuid' => $uuid,
                'name' => "Dokter $i " . strtoupper($serverRole),
                'email' => "dokter$i" . time() . "@$serverRole.com",
                'password' => Hash::make('123456'),
                'role' => 'dokter',
                'status_sync' => 'pending',
                'source_server' => $serverRole,
                'action_type' => 'insert',
                'created_at' => Carbon::now(),
                'updated_at' => Carbon::now(),
            ]);
            $dokterIds[] = ['id' => $id, 'uuid' => $uuid];
        }

        // 2. Buat 25 Pasien
        $pasienIds = [];
        for ($i = 1; $i <= 25; $i++) {
            $dokter = $dokterIds[array_rand($dokterIds)];
            $uuid = (string) Str::uuid();
            $id = DB::table('pasien')->insertGetId([
                'uuid' => $uuid,
                'no_rm' => "RM-" . strtoupper($serverRole) . "-" . rand(1000, 9999),
                'nama' => "Pasien Dummy $i " . strtoupper($serverRole),
                'jenis_kelamin' => rand(0, 1) ? 'L' : 'P',
                'tanggal_lahir' => Carbon::now()->subYears(rand(10, 60))->format('Y-m-d'),
                'dokter_id' => $dokter['id'],
                'dokter_uuid' => $dokter['uuid'],
                'status' => 'dirawat',
                'is_active' => true,
                'status_sync' => 'pending',
                'source_server' => $serverRole,
                'action_type' => 'insert',
                'created_at' => Carbon::now(),
                'updated_at' => Carbon::now(),
            ]);
            $pasienIds[] = ['id' => $id, 'uuid' => $uuid, 'dokter' => $dokter];
        }

        // 3. Buat 25 Visit
        for ($i = 1; $i <= 25; $i++) {
            $pasien = $pasienIds[array_rand($pasienIds)];
            DB::table('visit')->insert([
                'uuid' => (string) Str::uuid(),
                'pasien_id' => $pasien['id'],
                'dokter_id' => $pasien['dokter']['id'],
                'pasien_uuid' => $pasien['uuid'],
                'dokter_uuid' => $pasien['dokter']['uuid'],
                'keluhan' => "Keluhan Sempro $i dari $serverRole",
                'diagnosa' => "Diagnosa Sempro $i dari $serverRole",
                'tindakan' => "Tindakan Sempro $i dari $serverRole",
                'status_sync' => 'pending',
                'source_server' => $serverRole,
                'action_type' => 'insert',
                'created_at' => Carbon::now(),
                'updated_at' => Carbon::now(),
            ]);
        }
        
        echo "✅ Berhasil membuat 5 Dokter, 25 Pasien, dan 25 Visit untuk server $serverRole!\n";
    }
}

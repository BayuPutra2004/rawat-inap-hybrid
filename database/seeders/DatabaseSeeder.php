<?php

namespace Database\Seeders;

use App\Models\User;
use Illuminate\Database\Seeder;
use Illuminate\Support\Facades\Hash;

class DatabaseSeeder extends Seeder
{
    public function run(): void
    {
        // ADMIN / PERAWAT
        User::create([
            'name' => 'Admin Rawat Inap',
            'email' => 'admin@rs.test',
            'password' => Hash::make('admin123'),
            'role' => 'admin',
        ]);

        // DOKTER
        User::create([
            'name' => 'Dokter Umum',
            'email' => 'dokter@rs.test',
            'password' => Hash::make('dokter123'),
            'role' => 'dokter',
        ]);
    }
}

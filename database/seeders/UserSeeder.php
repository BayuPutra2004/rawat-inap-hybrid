<?php

namespace Database\Seeders;

use Illuminate\Database\Seeder;
use App\Models\User;
use Illuminate\Support\Facades\Hash;

class UserSeeder extends Seeder
{
    /**
     * Run the database seeds.
     */
    public function run(): void
    {
        // ADMIN
        User::create([
            'name' => 'Admin Sistem',
            'email' => 'admin@rawatinap.test',
            'password' => Hash::make('admin123'),
            'role' => 'admin',
        ]);

        // DOKTER
        User::create([
            'name' => 'Dokter Umum',
            'email' => 'dokter@rawatinap.test',
            'password' => Hash::make('dokter123'),
            'role' => 'dokter',
        ]);
    }
}

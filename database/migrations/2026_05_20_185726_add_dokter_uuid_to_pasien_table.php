<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::table('pasien', function (Blueprint $table) {

            $table->uuid('dokter_uuid')
                  ->nullable()
                  ->after('dokter_id');

        });
    }

    public function down(): void
    {
        Schema::table('pasien', function (Blueprint $table) {

            $table->dropColumn('dokter_uuid');

        });
    }
};
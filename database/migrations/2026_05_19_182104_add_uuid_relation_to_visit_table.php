<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    /**
     * Run the migrations.
     */
    public function up(): void
    {
        Schema::table('visit', function (Blueprint $table) {

            $table->uuid('pasien_uuid')->nullable();

            $table->uuid('dokter_uuid')->nullable();

        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::table('visit', function (Blueprint $table) {

            $table->dropColumn([
                'pasien_uuid',
                'dokter_uuid'
            ]);

        });
    }
};
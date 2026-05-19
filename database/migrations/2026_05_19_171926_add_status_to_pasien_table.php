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
        Schema::table('pasien', function (Blueprint $table) {

            $table->string('status')->nullable();

            $table->date('tanggal_keluar')->nullable();

            $table->text('catatan_keluar')->nullable();

        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::table('pasien', function (Blueprint $table) {

            $table->dropColumn([
                'status',
                'tanggal_keluar',
                'catatan_keluar'
            ]);

        });
    }
};

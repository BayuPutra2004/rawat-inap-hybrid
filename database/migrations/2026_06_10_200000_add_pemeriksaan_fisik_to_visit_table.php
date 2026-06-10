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
            $table->text('pemeriksaan_fisik')->nullable()->after('keluhan');
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::table('visit', function (Blueprint $table) {
            $table->dropColumn('pemeriksaan_fisik');
        });
    }
};

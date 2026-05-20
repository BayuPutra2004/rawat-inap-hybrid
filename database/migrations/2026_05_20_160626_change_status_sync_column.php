<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::table('pasien', function (Blueprint $table) {

            $table->string('status_sync')
                  ->default('pending')
                  ->change();

        });

        Schema::table('visit', function (Blueprint $table) {

            $table->string('status_sync')
                  ->default('pending')
                  ->change();

        });
    }

    public function down(): void
    {
        //
    }
};
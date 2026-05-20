<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::table('sync_log', function (Blueprint $table) {

            $table->bigInteger('sync_duration_ms')
                  ->nullable();

            $table->string('target_server')
                  ->nullable();

        });
    }

    public function down(): void
    {
        Schema::table('sync_log', function (Blueprint $table) {

            $table->dropColumn([
                'sync_duration_ms',
                'target_server'
            ]);

        });
    }
};
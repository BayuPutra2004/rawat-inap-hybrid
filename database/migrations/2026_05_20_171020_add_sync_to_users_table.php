<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::table('users', function (Blueprint $table) {
            $table->string('status_sync')
                  ->default('pending');
            $table->timestamp('synced_at')
                  ->nullable();
            $table->string('source_server')
                  ->default('lokal');
            $table->string('action_type')
                  ->default('create');
        });
    }

    public function down(): void
    {
        //
    }
};
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
            $table->uuid('uuid')->nullable()->unique();
            $table->string('status_sync')->default('pending');
            $table->timestamp('synced_at')->nullable();
            $table->string('source_server')->default('lokal');
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::table('visit', function (Blueprint $table) {
            //
        });
    }
};

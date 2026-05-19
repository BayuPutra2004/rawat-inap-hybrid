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
	    Schema::create('rawat_inap', function (Blueprint $table) {
	        $table->id();
	        $table->foreignId('pasien_id')->constrained('pasien')->cascadeOnDelete();
	        $table->string('kamar');
	        $table->date('tanggal_masuk');
	        $table->string('status')->default('dirawat');
	        $table->timestamps();
	    });
	}

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('rawat_inap');
    }
};

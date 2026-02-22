package com.flashintel.agent.domain;

import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * SMART health metrics snapshot for the monitored disk.
 * All fields default to -1 when the value cannot be read from smartctl.
 */
public class SmartMetrics {

    @JsonProperty("wear_leveling_count")
    private long wearLevelingCount = -1;

    @JsonProperty("reallocated_sector_count")
    private long reallocatedSectorCount = -1;

    @JsonProperty("power_on_hours")
    private long powerOnHours = -1;

    @JsonProperty("temperature")
    private double temperature = -1;

    @JsonProperty("media_errors")
    private long mediaErrors = -1;

    public SmartMetrics() {}

    public long getWearLevelingCount() { return wearLevelingCount; }
    public void setWearLevelingCount(long v) { this.wearLevelingCount = v; }

    public long getReallocatedSectorCount() { return reallocatedSectorCount; }
    public void setReallocatedSectorCount(long v) { this.reallocatedSectorCount = v; }

    public long getPowerOnHours() { return powerOnHours; }
    public void setPowerOnHours(long v) { this.powerOnHours = v; }

    public double getTemperature() { return temperature; }
    public void setTemperature(double v) { this.temperature = v; }

    public long getMediaErrors() { return mediaErrors; }
    public void setMediaErrors(long v) { this.mediaErrors = v; }
}

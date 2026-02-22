package com.flashintel.agent.domain;

import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * I/O throughput metrics snapshot.
 * On macOS M1 these values are simulated; see IoMetricsCollector.
 */
public class IoMetrics {

    @JsonProperty("read_iops")
    private double readIOPS;

    @JsonProperty("write_iops")
    private double writeIOPS;

    @JsonProperty("burst_write_rate")
    private double burstWriteRate;

    @JsonProperty("simulated")
    private boolean simulated;

    public IoMetrics() {}

    public IoMetrics(double readIOPS, double writeIOPS, double burstWriteRate, boolean simulated) {
        this.readIOPS = readIOPS;
        this.writeIOPS = writeIOPS;
        this.burstWriteRate = burstWriteRate;
        this.simulated = simulated;
    }

    public double getReadIOPS() { return readIOPS; }
    public void setReadIOPS(double readIOPS) { this.readIOPS = readIOPS; }

    public double getWriteIOPS() { return writeIOPS; }
    public void setWriteIOPS(double writeIOPS) { this.writeIOPS = writeIOPS; }

    public double getBurstWriteRate() { return burstWriteRate; }
    public void setBurstWriteRate(double burstWriteRate) { this.burstWriteRate = burstWriteRate; }

    public boolean isSimulated() { return simulated; }
    public void setSimulated(boolean simulated) { this.simulated = simulated; }
}

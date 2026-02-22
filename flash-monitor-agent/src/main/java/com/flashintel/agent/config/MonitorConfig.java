package com.flashintel.agent.config;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

import java.util.List;

/**
 * Strongly-typed configuration for the Flash Monitor Agent.
 * All values are bound from application.yml; no hardcoded magic numbers.
 */
@Component
@ConfigurationProperties(prefix = "monitor")
public class MonitorConfig {

    private Scan scan = new Scan();
    private Disk disk = new Disk();
    private Io io = new Io();
    private Smart smart = new Smart();
    private Send send = new Send();

    // ── Getters / Setters ────────────────────────────────────────────

    public Scan getScan() { return scan; }
    public void setScan(Scan scan) { this.scan = scan; }

    public Disk getDisk() { return disk; }
    public void setDisk(Disk disk) { this.disk = disk; }

    public Io getIo() { return io; }
    public void setIo(Io io) { this.io = io; }

    public Smart getSmart() { return smart; }
    public void setSmart(Smart smart) { this.smart = smart; }

    public Send getSend() { return send; }
    public void setSend(Send send) { this.send = send; }

    // ── Nested config classes ─────────────────────────────────────────

    public static class Scan {
        private String root = System.getProperty("user.home");
        private int maxDepth = 10;
        private List<String> trackedExtensions = List.of();

        public String getRoot() { return root; }
        public void setRoot(String root) { this.root = root; }
        public int getMaxDepth() { return maxDepth; }
        public void setMaxDepth(int maxDepth) { this.maxDepth = maxDepth; }
        public List<String> getTrackedExtensions() { return trackedExtensions; }
        public void setTrackedExtensions(List<String> trackedExtensions) { this.trackedExtensions = trackedExtensions; }
    }

    public static class Disk {
        private long intervalMs = 10_000L;

        public long getIntervalMs() { return intervalMs; }
        public void setIntervalMs(long intervalMs) { this.intervalMs = intervalMs; }
    }

    public static class Io {
        private boolean simulate = true;
        private double simReadIopsBase = 1200.0;
        private double simWriteIopsBase = 800.0;
        private double simBurstWriteRateBase = 2000.0;
        private int simJitterPercent = 15;

        public boolean isSimulate() { return simulate; }
        public void setSimulate(boolean simulate) { this.simulate = simulate; }
        public double getSimReadIopsBase() { return simReadIopsBase; }
        public void setSimReadIopsBase(double v) { this.simReadIopsBase = v; }
        public double getSimWriteIopsBase() { return simWriteIopsBase; }
        public void setSimWriteIopsBase(double v) { this.simWriteIopsBase = v; }
        public double getSimBurstWriteRateBase() { return simBurstWriteRateBase; }
        public void setSimBurstWriteRateBase(double v) { this.simBurstWriteRateBase = v; }
        public int getSimJitterPercent() { return simJitterPercent; }
        public void setSimJitterPercent(int v) { this.simJitterPercent = v; }
    }

    public static class Smart {
        private String device = "/dev/disk0";
        private String smartctlPath = "/usr/local/bin/smartctl";

        public String getDevice() { return device; }
        public void setDevice(String device) { this.device = device; }
        public String getSmartctlPath() { return smartctlPath; }
        public void setSmartctlPath(String smartctlPath) { this.smartctlPath = smartctlPath; }
    }

    public static class Send {
        private long intervalMs = 15_000L;
        private String endpoint = "http://localhost:8000/ingest";
        private int connectTimeoutMs = 5_000;
        private int readTimeoutMs = 10_000;

        public long getIntervalMs() { return intervalMs; }
        public void setIntervalMs(long intervalMs) { this.intervalMs = intervalMs; }
        public String getEndpoint() { return endpoint; }
        public void setEndpoint(String endpoint) { this.endpoint = endpoint; }
        public int getConnectTimeoutMs() { return connectTimeoutMs; }
        public void setConnectTimeoutMs(int v) { this.connectTimeoutMs = v; }
        public int getReadTimeoutMs() { return readTimeoutMs; }
        public void setReadTimeoutMs(int v) { this.readTimeoutMs = v; }
    }
}

package com.flashintel.agent.domain;

import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * Disk capacity metrics snapshot.
 * Sizes are in bytes.
 */
public class DiskMetrics {

    @JsonProperty("total_bytes")
    private long totalBytes;

    @JsonProperty("used_bytes")
    private long usedBytes;

    @JsonProperty("free_bytes")
    private long freeBytes;

    public DiskMetrics() {}

    public DiskMetrics(long totalBytes, long usedBytes, long freeBytes) {
        this.totalBytes = totalBytes;
        this.usedBytes = usedBytes;
        this.freeBytes = freeBytes;
    }

    public long getTotalBytes() { return totalBytes; }
    public void setTotalBytes(long totalBytes) { this.totalBytes = totalBytes; }

    public long getUsedBytes() { return usedBytes; }
    public void setUsedBytes(long usedBytes) { this.usedBytes = usedBytes; }

    public long getFreeBytes() { return freeBytes; }
    public void setFreeBytes(long freeBytes) { this.freeBytes = freeBytes; }
}

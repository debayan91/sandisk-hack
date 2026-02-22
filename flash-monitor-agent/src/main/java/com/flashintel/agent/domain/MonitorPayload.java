package com.flashintel.agent.domain;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.time.Instant;
import java.util.List;

/**
 * Root payload sent to the Python Intelligence Core every 15 seconds.
 * All sub-fields are populated by their respective collectors.
 */
public class MonitorPayload {

    @JsonProperty("timestamp")
    private String timestamp;

    @JsonProperty("disk_metrics")
    private DiskMetrics diskMetrics;

    @JsonProperty("smart_metrics")
    private SmartMetrics smartMetrics;

    @JsonProperty("io_metrics")
    private IoMetrics ioMetrics;

    @JsonProperty("files")
    private List<FileMetadata> files;

    public MonitorPayload() {
        this.timestamp = Instant.now().toString();
    }

    public String getTimestamp() { return timestamp; }
    public void setTimestamp(String timestamp) { this.timestamp = timestamp; }

    public DiskMetrics getDiskMetrics() { return diskMetrics; }
    public void setDiskMetrics(DiskMetrics diskMetrics) { this.diskMetrics = diskMetrics; }

    public SmartMetrics getSmartMetrics() { return smartMetrics; }
    public void setSmartMetrics(SmartMetrics smartMetrics) { this.smartMetrics = smartMetrics; }

    public IoMetrics getIoMetrics() { return ioMetrics; }
    public void setIoMetrics(IoMetrics ioMetrics) { this.ioMetrics = ioMetrics; }

    public List<FileMetadata> getFiles() { return files; }
    public void setFiles(List<FileMetadata> files) { this.files = files; }
}

package com.flashintel.agent.domain;

import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * Metadata snapshot for a single file observed during a scan cycle.
 */
public class FileMetadata {

    @JsonProperty("path")
    private String path;

    @JsonProperty("size")
    private long size;

    @JsonProperty("last_access")
    private long lastAccessTime;   // epoch millis

    @JsonProperty("last_modified")
    private long lastModifiedTime; // epoch millis

    @JsonProperty("extension")
    private String extension;

    @JsonProperty("access_count")
    private long accessCount;

    @JsonProperty("write_count")
    private long writeCount;

    @JsonProperty("rename_count")
    private long renameCount;

    public FileMetadata() {}

    public FileMetadata(String path, long size, long lastAccessTime,
                        long lastModifiedTime, String extension) {
        this.path = path;
        this.size = size;
        this.lastAccessTime = lastAccessTime;
        this.lastModifiedTime = lastModifiedTime;
        this.extension = extension;
    }

    // ── Getters / Setters ────────────────────────────────────────────

    public String getPath() { return path; }
    public void setPath(String path) { this.path = path; }

    public long getSize() { return size; }
    public void setSize(long size) { this.size = size; }

    public long getLastAccessTime() { return lastAccessTime; }
    public void setLastAccessTime(long lastAccessTime) { this.lastAccessTime = lastAccessTime; }

    public long getLastModifiedTime() { return lastModifiedTime; }
    public void setLastModifiedTime(long lastModifiedTime) { this.lastModifiedTime = lastModifiedTime; }

    public String getExtension() { return extension; }
    public void setExtension(String extension) { this.extension = extension; }

    public long getAccessCount() { return accessCount; }
    public void setAccessCount(long accessCount) { this.accessCount = accessCount; }

    public long getWriteCount() { return writeCount; }
    public void setWriteCount(long writeCount) { this.writeCount = writeCount; }

    public long getRenameCount() { return renameCount; }
    public void setRenameCount(long renameCount) { this.renameCount = renameCount; }
}

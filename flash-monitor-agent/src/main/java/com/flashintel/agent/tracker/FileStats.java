package com.flashintel.agent.tracker;

import java.util.concurrent.atomic.AtomicLong;

/**
 * Thread-safe container for access/write/rename event counters for a single file.
 * Uses AtomicLong so WatchService events from multiple threads don't need explicit locking.
 */
public class FileStats {

    private final AtomicLong accessCount = new AtomicLong(0);
    private final AtomicLong writeCount = new AtomicLong(0);
    private final AtomicLong renameCount = new AtomicLong(0);

    public void incrementAccess() { accessCount.incrementAndGet(); }
    public void incrementWrite()  { writeCount.incrementAndGet(); }
    public void incrementRename() { renameCount.incrementAndGet(); }

    public long getAccessCount() { return accessCount.get(); }
    public long getWriteCount()  { return writeCount.get(); }
    public long getRenameCount() { return renameCount.get(); }
}

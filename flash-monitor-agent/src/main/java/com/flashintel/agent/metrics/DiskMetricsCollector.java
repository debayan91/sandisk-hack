package com.flashintel.agent.metrics;

import com.flashintel.agent.domain.DiskMetrics;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.nio.file.FileStore;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.concurrent.atomic.AtomicReference;

/**
 * Collects disk capacity metrics on a configurable interval.
 *
 * Uses Java NIO {@link FileStore} for cross-platform compatibility.
 * The latest snapshot is stored in an AtomicReference so callers
 * always get a consistent, lock-free read.
 */
@Component
public class DiskMetricsCollector {

    private static final Logger log = LoggerFactory.getLogger(DiskMetricsCollector.class);

    @Value("${monitor.scan.root:${user.home}}")
    private String scanRoot;

    private final AtomicReference<DiskMetrics> latest =
            new AtomicReference<>(new DiskMetrics(0, 0, 0));

    /**
     * Called by the scheduler every {@code monitor.disk.interval-ms} milliseconds.
     * The interval is driven from {@link com.flashintel.agent.sender.JsonPayloadSender}
     * via a separate @Scheduled annotation to avoid annotation duplication.
     */
    public void collect() {
        try {
            FileStore store = Files.getFileStore(Path.of(scanRoot));
            long total = store.getTotalSpace();
            long free  = store.getUsableSpace();
            long used  = total - free;
            latest.set(new DiskMetrics(total, used, free));
            log.debug("Disk: total={} used={} free={}", total, used, free);
        } catch (IOException e) {
            log.warn("Could not collect disk metrics: {}", e.getMessage());
        }
    }

    /** Returns the most recently collected {@link DiskMetrics} snapshot. */
    public DiskMetrics getLatest() {
        return latest.get();
    }
}

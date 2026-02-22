package com.flashintel.agent.tracker;

import com.flashintel.agent.config.MonitorConfig;
import jakarta.annotation.PostConstruct;
import jakarta.annotation.PreDestroy;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.nio.file.*;
import java.nio.file.attribute.BasicFileAttributes;
import java.util.HashMap;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;

import static java.nio.file.StandardWatchEventKinds.*;

/**
 * Watches the scan root (and all subdirectories) using Java NIO WatchService.
 *
 * Event mapping:
 *   ENTRY_MODIFY → accessCount++, writeCount++
 *   ENTRY_CREATE (within short window of a DELETE) → renameCount++
 *   ENTRY_CREATE otherwise → no-op (new file)
 *
 * Runs on a dedicated daemon thread so it never blocks the main scheduler.
 */
@Component
public class AccessFrequencyTracker {

    private static final Logger log = LoggerFactory.getLogger(AccessFrequencyTracker.class);

    /** Threshold (ms) within which a CREATE after a DELETE is treated as a rename. */
    private static final long RENAME_WINDOW_MS = 500;

    private final MonitorConfig config;

    // path → FileStats
    private final ConcurrentHashMap<String, FileStats> statsMap = new ConcurrentHashMap<>();

    private WatchService watchService;
    private Thread watchThread;

    // Track recent DELETEs for rename heuristic: path → timestamp of DELETE event
    private final Map<Path, Long> recentDeletes = new ConcurrentHashMap<>();

    // WatchKey → directory path mapping
    private final Map<WatchKey, Path> keyMap = new HashMap<>();

    public AccessFrequencyTracker(MonitorConfig config) {
        this.config = config;
    }

    @PostConstruct
    public void start() {
        try {
            watchService = FileSystems.getDefault().newWatchService();
            Path root = Path.of(config.getScan().getRoot());
            registerAll(root);
            watchThread = new Thread(this::watchLoop, "fip-watch-thread");
            watchThread.setDaemon(true);
            watchThread.start();
            log.info("AccessFrequencyTracker started on root: {}", root);
        } catch (IOException e) {
            log.warn("Could not start AccessFrequencyTracker: {}", e.getMessage());
        }
    }

    @PreDestroy
    public void stop() {
        if (watchThread != null) watchThread.interrupt();
        if (watchService != null) {
            try { watchService.close(); } catch (IOException ignored) {}
        }
    }

    /** Returns the FileStats for a given absolute path, creating one if absent. */
    public FileStats statsFor(String absolutePath) {
        return statsMap.computeIfAbsent(absolutePath, k -> new FileStats());
    }

    /** Returns a read-only view of all tracked stats. */
    public Map<String, FileStats> getStatsMap() {
        return statsMap;
    }

    // ── Private helpers ───────────────────────────────────────────────

    private void registerAll(Path start) throws IOException {
        Files.walkFileTree(start, Set.of(FileVisitOption.FOLLOW_LINKS),
                config.getScan().getMaxDepth(),
                new SimpleFileVisitor<>() {
                    @Override
                    public FileVisitResult preVisitDirectory(Path dir,
                            BasicFileAttributes attrs) throws IOException {
                        if (isSymlinkLoop(dir)) return FileVisitResult.SKIP_SUBTREE;
                        WatchKey key = dir.register(watchService, ENTRY_CREATE, ENTRY_DELETE, ENTRY_MODIFY);
                        keyMap.put(key, dir);
                        return FileVisitResult.CONTINUE;
                    }
                    @Override
                    public FileVisitResult visitFileFailed(Path file, IOException exc) {
                        return FileVisitResult.SKIP_SUBTREE;
                    }
                });
    }

    private boolean isSymlinkLoop(Path dir) {
        try { return !dir.toRealPath().equals(dir.toAbsolutePath()); }
        catch (IOException e) { return false; }
    }

    private void watchLoop() {
        log.debug("Watch loop started");
        while (!Thread.currentThread().isInterrupted()) {
            WatchKey key;
            try {
                key = watchService.take();
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                break;
            }
            Path dir = keyMap.get(key);
            if (dir == null) { key.reset(); continue; }

            for (WatchEvent<?> event : key.pollEvents()) {
                WatchEvent.Kind<?> kind = event.kind();
                if (kind == OVERFLOW) continue;

                @SuppressWarnings("unchecked")
                WatchEvent<Path> pathEvent = (WatchEvent<Path>) event;
                Path child = dir.resolve(pathEvent.context());
                String absPath = child.toAbsolutePath().toString();

                if (kind == ENTRY_MODIFY) {
                    FileStats stats = statsMap.computeIfAbsent(absPath, k -> new FileStats());
                    stats.incrementWrite();
                    stats.incrementAccess();
                }

                if (kind == ENTRY_DELETE) {
                    recentDeletes.put(child, System.currentTimeMillis());
                }

                if (kind == ENTRY_CREATE) {
                    // Register new directories
                    if (Files.isDirectory(child)) {
                        try {
                            WatchKey newKey = child.register(watchService,
                                    ENTRY_CREATE, ENTRY_DELETE, ENTRY_MODIFY);
                            keyMap.put(newKey, child);
                        } catch (IOException e) {
                            log.debug("Could not register new dir: {}", child);
                        }
                    }
                    // Heuristic rename detection
                    long now = System.currentTimeMillis();
                    recentDeletes.entrySet().removeIf(entry ->
                            now - entry.getValue() > RENAME_WINDOW_MS * 10);

                    recentDeletes.entrySet().stream()
                            .filter(e -> now - e.getValue() < RENAME_WINDOW_MS)
                            .findFirst()
                            .ifPresent(e -> {
                                FileStats stats = statsMap.computeIfAbsent(absPath, k -> new FileStats());
                                stats.incrementRename();
                                recentDeletes.remove(e.getKey());
                            });
                }
            }
            key.reset();
        }
        log.debug("Watch loop terminated");
    }
}

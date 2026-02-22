package com.flashintel.agent.scanner;

import com.flashintel.agent.config.MonitorConfig;
import com.flashintel.agent.domain.FileMetadata;
import com.flashintel.agent.tracker.AccessFrequencyTracker;
import com.flashintel.agent.tracker.FileStats;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.nio.file.*;
import java.nio.file.attribute.BasicFileAttributes;
import java.util.ArrayList;
import java.util.List;
import java.util.Set;

/**
 * Recursively scans the configured root directory and builds a list of
 * {@link FileMetadata} objects enriched with tracker event counts.
 *
 * The scan is synchronous but fast (read-only stat calls); it is invoked
 * by the payload sender just before assembly.
 */
@Component
public class FileScanner {

    private static final Logger log = LoggerFactory.getLogger(FileScanner.class);

    private final MonitorConfig config;
    private final AccessFrequencyTracker tracker;

    public FileScanner(MonitorConfig config, AccessFrequencyTracker tracker) {
        this.config = config;
        this.tracker = tracker;
    }

    /**
     * Performs a fresh recursive scan and returns all file metadata.
     * Directories, symlinks pointing outside the root, and unreadable paths are skipped.
     */
    public List<FileMetadata> scan() {
        List<FileMetadata> results = new ArrayList<>();
        Path root = Path.of(config.getScan().getRoot());
        List<String> filterExtensions = config.getScan().getTrackedExtensions();

        try {
            Files.walkFileTree(root,
                    Set.of(FileVisitOption.FOLLOW_LINKS),
                    config.getScan().getMaxDepth(),
                    new SimpleFileVisitor<>() {
                        @Override
                        public FileVisitResult visitFile(Path file, BasicFileAttributes attrs) {
                            try {
                                String fileStr = file.toAbsolutePath().toString();
                                String ext = extractExtension(file.getFileName().toString());

                                // Filter by extension if configured
                                if (!filterExtensions.isEmpty()
                                        && !filterExtensions.contains(ext)) {
                                    return FileVisitResult.CONTINUE;
                                }

                                FileMetadata meta = new FileMetadata(
                                        fileStr,
                                        attrs.size(),
                                        attrs.lastAccessTime().toMillis(),
                                        attrs.lastModifiedTime().toMillis(),
                                        ext
                                );

                                // Enrich with tracker data
                                FileStats stats = tracker.statsFor(fileStr);
                                meta.setAccessCount(stats.getAccessCount());
                                meta.setWriteCount(stats.getWriteCount());
                                meta.setRenameCount(stats.getRenameCount());

                                results.add(meta);
                            } catch (Exception e) {
                                log.debug("Skipping file {}: {}", file, e.getMessage());
                            }
                            return FileVisitResult.CONTINUE;
                        }

                        @Override
                        public FileVisitResult visitFileFailed(Path file, IOException exc) {
                            log.debug("Cannot visit {}: {}", file, exc.getMessage());
                            return FileVisitResult.SKIP_SUBTREE;
                        }
                    });
        } catch (IOException e) {
            log.warn("Error during file scan: {}", e.getMessage());
        }

        log.debug("Scan complete: {} files found under {}", results.size(), root);
        return results;
    }

    /** Extracts lowercase extension from a filename, or empty string if none. */
    private static String extractExtension(String filename) {
        int dot = filename.lastIndexOf('.');
        if (dot < 0 || dot == filename.length() - 1) return "";
        return filename.substring(dot + 1).toLowerCase();
    }
}

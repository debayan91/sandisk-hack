package com.flashintel.agent.metrics;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.flashintel.agent.config.MonitorConfig;
import com.flashintel.agent.domain.SmartMetrics;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.util.concurrent.atomic.AtomicReference;
import java.util.stream.Collectors;

/**
 * Collects S.M.A.R.T. disk health metrics by invoking {@code smartctl -j -a <device>}
 * via ProcessBuilder.
 *
 * All fields are parsed safely — a missing or malformed field defaults to -1.
 * On macOS M1 (Apple Silicon), smartctl may not have full NVMe support without
 * Homebrew; the collector logs a warning and returns safe defaults.
 *
 * Supported field paths in the smartctl JSON output:
 * <pre>
 *   wear_leveling_count  → ata_smart_attributes.table[id==177].raw.value
 *   reallocated_sector   → ata_smart_attributes.table[id==5].raw.value
 *   power_on_hours       → power_on_time.hours
 *   temperature          → temperature.current
 *   media_errors         → nvme_smart_health_information_log.media_errors
 * </pre>
 */
@Component
public class SmartMetricsCollector {

    private static final Logger log = LoggerFactory.getLogger(SmartMetricsCollector.class);

    private final MonitorConfig config;
    private final ObjectMapper mapper = new ObjectMapper();

    private final AtomicReference<SmartMetrics> latest =
            new AtomicReference<>(new SmartMetrics());

    public SmartMetricsCollector(MonitorConfig config) {
        this.config = config;
    }

    /**
     * Runs smartctl and parses output.  Called by the scheduler.
     * Always completes without throwing — failures produce a safe-defaults object.
     */
    public void collect() {
        SmartMetrics metrics = new SmartMetrics();
        try {
            String smartctlPath = config.getSmart().getSmartctlPath();
            String device = config.getSmart().getDevice();

            ProcessBuilder pb = new ProcessBuilder(smartctlPath, "-j", "-a", device);
            pb.redirectErrorStream(true);
            Process proc = pb.start();

            String output;
            try (BufferedReader reader = new BufferedReader(
                    new InputStreamReader(proc.getInputStream()))) {
                output = reader.lines().collect(Collectors.joining("\n"));
            }
            proc.waitFor();

            JsonNode root = mapper.readTree(output);
            metrics.setWearLevelingCount(findSmartAttribute(root, 177));
            metrics.setReallocatedSectorCount(findSmartAttribute(root, 5));
            metrics.setPowerOnHours(longAt(root, "power_on_time", "hours"));
            metrics.setTemperature(doubleAt(root, "temperature", "current"));
            metrics.setMediaErrors(longAt(root,
                    "nvme_smart_health_information_log", "media_errors"));

            log.debug("SMART metrics collected: wlc={} temp={}",
                    metrics.getWearLevelingCount(), metrics.getTemperature());
        } catch (Exception e) {
            log.warn("smartctl unavailable or failed ({}), using defaults", e.getMessage());
        }
        latest.set(metrics);
    }

    /** Returns the most recently collected {@link SmartMetrics}. */
    public SmartMetrics getLatest() {
        return latest.get();
    }

    // ── JSON helpers ──────────────────────────────────────────────────

    /** Searches ata_smart_attributes.table for an entry matching the given ID. */
    private long findSmartAttribute(JsonNode root, int attrId) {
        try {
            JsonNode table = root.path("ata_smart_attributes").path("table");
            if (table.isArray()) {
                for (JsonNode entry : table) {
                    if (entry.path("id").asInt(-1) == attrId) {
                        return entry.path("raw").path("value").asLong(-1);
                    }
                }
            }
        } catch (Exception ignored) {}
        return -1;
    }

    private long longAt(JsonNode root, String... path) {
        try {
            JsonNode node = root;
            for (String key : path) node = node.path(key);
            return node.isMissingNode() ? -1 : node.asLong(-1);
        } catch (Exception e) { return -1; }
    }

    private double doubleAt(JsonNode root, String... path) {
        try {
            JsonNode node = root;
            for (String key : path) node = node.path(key);
            return node.isMissingNode() ? -1 : node.asDouble(-1);
        } catch (Exception e) { return -1; }
    }
}

package com.flashintel.agent.metrics;

import com.flashintel.agent.config.MonitorConfig;
import com.flashintel.agent.domain.IoMetrics;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import java.util.Random;
import java.util.concurrent.atomic.AtomicReference;

/**
 * Collects or simulates I/O throughput metrics (IOPS, burst write rate).
 *
 * macOS Apple Silicon (M1) does not expose raw IOPS via standard userspace tools
 * without root/kernel extensions, so this collector operates in two modes:
 *
 * <ul>
 *   <li><b>Simulate = true</b>: generates realistic jittered values from configurable
 *       baselines. Suitable for demo and development.</li>
 *   <li><b>Simulate = false</b>: attempts to parse {@code iostat -d 1 1} output;
 *       falls back to simulation on failure.</li>
 * </ul>
 */
@Component
public class IoMetricsCollector {

    private static final Logger log = LoggerFactory.getLogger(IoMetricsCollector.class);

    private final MonitorConfig config;
    private final Random rng = new Random();

    private final AtomicReference<IoMetrics> latest = new AtomicReference<>(
            new IoMetrics(0, 0, 0, true));

    public IoMetricsCollector(MonitorConfig config) {
        this.config = config;
    }

    /** Collects (or simulates) I/O metrics. Called by the payload sender scheduler. */
    public void collect() {
        MonitorConfig.Io io = config.getIo();

        if (io.isSimulate()) {
            latest.set(simulate(io));
            return;
        }

        // Attempt real iostat parse (macOS disk0 column)
        try {
            IoMetrics real = parseIostat();
            latest.set(real);
        } catch (Exception e) {
            log.warn("iostat parse failed ({}), falling back to simulation", e.getMessage());
            latest.set(simulate(io));
        }
    }

    /** Returns the most recently collected/simulated {@link IoMetrics}. */
    public IoMetrics getLatest() {
        return latest.get();
    }

    // ── Private helpers ───────────────────────────────────────────────

    private IoMetrics simulate(MonitorConfig.Io io) {
        double jitterFactor = io.getSimJitterPercent() / 100.0;
        double readIOPS  = jitter(io.getSimReadIopsBase(), jitterFactor);
        double writeIOPS = jitter(io.getSimWriteIopsBase(), jitterFactor);
        double burst     = jitter(io.getSimBurstWriteRateBase(), jitterFactor);
        log.debug("Simulated IO: read={} write={} burst={}", readIOPS, writeIOPS, burst);
        return new IoMetrics(readIOPS, writeIOPS, burst, true);
    }

    private IoMetrics parseIostat() throws Exception {
        ProcessBuilder pb = new ProcessBuilder("iostat", "-d", "1", "1");
        pb.redirectErrorStream(true);
        Process proc = pb.start();
        String out = new String(proc.getInputStream().readAllBytes());
        proc.waitFor();

        // iostat output format (macOS disk column):
        //   KB/t  tps  MB/s  ...
        //   value value value ...
        String[] lines = out.trim().split("\n");
        if (lines.length < 3) throw new Exception("unexpected iostat output");

        // Third line has actual values
        String[] parts = lines[2].trim().split("\\s+");
        // tps = parts[1], use as approximate writeIOPS
        double tps = Double.parseDouble(parts[1]);
        return new IoMetrics(tps * 0.6, tps * 0.4,
                tps * 1.5, false);
    }

    private double jitter(double base, double factor) {
        double delta = base * factor;
        return Math.max(0, base + (rng.nextDouble() * 2 - 1) * delta);
    }
}

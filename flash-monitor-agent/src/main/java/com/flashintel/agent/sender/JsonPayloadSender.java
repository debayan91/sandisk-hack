package com.flashintel.agent.sender;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import com.flashintel.agent.config.MonitorConfig;
import com.flashintel.agent.domain.MonitorPayload;
import com.flashintel.agent.metrics.DiskMetricsCollector;
import com.flashintel.agent.metrics.IoMetricsCollector;
import com.flashintel.agent.metrics.SmartMetricsCollector;
import com.flashintel.agent.scanner.FileScanner;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.scheduling.annotation.Async;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.time.Instant;

/**
 * Orchestrates the complete data-collection-and-send cycle on a configurable interval.
 *
 * <ol>
 *   <li>Triggers all metric collectors.</li>
 *   <li>Runs a file scan.</li>
 *   <li>Assembles the {@link MonitorPayload}.</li>
 *   <li>POSTs the JSON payload asynchronously (non-blocking) to the Python Intelligence Core.</li>
 * </ol>
 *
 * The send is annotated {@code @Async} to prevent the scheduler thread from blocking
 * if the remote endpoint is slow or unreachable.
 */
@Component
public class JsonPayloadSender {

    private static final Logger log = LoggerFactory.getLogger(JsonPayloadSender.class);

    private final MonitorConfig config;
    private final DiskMetricsCollector diskCollector;
    private final SmartMetricsCollector smartCollector;
    private final IoMetricsCollector ioCollector;
    private final FileScanner fileScanner;
    private final ObjectMapper mapper;
    private final HttpClient httpClient;

    public JsonPayloadSender(MonitorConfig config,
                             DiskMetricsCollector diskCollector,
                             SmartMetricsCollector smartCollector,
                             IoMetricsCollector ioCollector,
                             FileScanner fileScanner) {
        this.config = config;
        this.diskCollector = diskCollector;
        this.smartCollector = smartCollector;
        this.ioCollector = ioCollector;
        this.fileScanner = fileScanner;

        this.mapper = new ObjectMapper();
        this.mapper.disable(SerializationFeature.FAIL_ON_EMPTY_BEANS);

        MonitorConfig.Send sendCfg = config.getSend();
        this.httpClient = HttpClient.newBuilder()
                .connectTimeout(Duration.ofMillis(sendCfg.getConnectTimeoutMs()))
                .build();
    }

    /**
     * Scheduled entry point — fires every {@code monitor.send.interval-ms} ms.
     * Delegates to {@link #collectAndSend()} via @Async to keep the scheduler free.
     */
    @Scheduled(fixedDelayString = "${monitor.send.interval-ms:15000}")
    public void scheduledSend() {
        collectAndSend(); // Spring proxies this through the async executor
    }

    /**
     * Collects all metrics, scans files, and asynchronously POSTs the payload.
     * Must be public for Spring's @Async proxy to intercept it.
     */
    @Async
    public void collectAndSend() {
        try {
            // 1. Collect fresh metrics
            diskCollector.collect();
            smartCollector.collect();
            ioCollector.collect();

            // 2. Assemble payload
            MonitorPayload payload = new MonitorPayload();
            payload.setTimestamp(Instant.now().toString());
            payload.setDiskMetrics(diskCollector.getLatest());
            payload.setSmartMetrics(smartCollector.getLatest());
            payload.setIoMetrics(ioCollector.getLatest());
            payload.setFiles(fileScanner.scan());

            // 3. Serialize
            String json = mapper.writeValueAsString(payload);

            // 4. Send
            String endpoint = config.getSend().getEndpoint();
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(endpoint))
                    .timeout(Duration.ofMillis(config.getSend().getReadTimeoutMs()))
                    .header("Content-Type", "application/json")
                    .POST(HttpRequest.BodyPublishers.ofString(json))
                    .build();

            HttpResponse<String> response = httpClient.send(request,
                    HttpResponse.BodyHandlers.ofString());

            log.info("Payload sent → {} | files={} | status={}",
                    endpoint, payload.getFiles().size(), response.statusCode());

        } catch (Exception e) {
            log.warn("Failed to send payload: {}", e.getMessage());
        }
    }
}

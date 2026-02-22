package com.flashintel.agent;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableAsync;
import org.springframework.scheduling.annotation.EnableScheduling;

/**
 * Flash Monitor Agent — entry point.
 *
 * Starts the Spring Boot application which activates:
 *   - Scheduled tasks (disk metrics, payload sender)
 *   - Async execution (non-blocking HTTP sends)
 *   - File system watching (WatchService tracker)
 */
@SpringBootApplication
@EnableScheduling
@EnableAsync
public class FlashMonitorAgentApplication {

    public static void main(String[] args) {
        SpringApplication.run(FlashMonitorAgentApplication.class, args);
    }
}

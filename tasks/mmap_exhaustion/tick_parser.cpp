#include <iostream>
#include <sys/mman.h>
#include <unistd.h>
#include <cstring>
#include <cerrno>
#include <vector>

// Order Book tick struct
struct TickData {
    long timestamp;
    double price;
    int volume;
    char symbol[8];
};

int main() {
    std::cout << "[INFO] Initializing low-latency tick data parser..." << std::endl;
    std::vector<void*> maps;
    
    // Simulate mapping small 256KB files
    size_t chunk_size = 256 * 1024; 
    size_t ticks_per_chunk = chunk_size / sizeof(TickData);

    for (int i = 0; i < 10000; ++i) {
        // Create an anonymous mapping
        void* ptr = mmap(NULL, chunk_size, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
        
        if (ptr == MAP_FAILED) {
            std::cerr << "\n[FATAL ERROR] Failed to map order book batch " << i << "!" << std::endl;
            std::cerr << "mmap(...) = -1 : " << strerror(errno) << " (ENOMEM)" << std::endl;
            std::cerr << "Parser crashed. Please check system resources." << std::endl;
            return 1;
        }

        // Write dummy data to the memory to force the kernel to allocate physical RAM pages
        TickData* ticks = static_cast<TickData*>(ptr);
        for (size_t j = 0; j < ticks_per_chunk; j += 100) { 
            ticks[j].timestamp = 1710000000 + i;
            ticks[j].price = 150.25;
            ticks[j].volume = 100;
            strcpy(ticks[j].symbol, "AAPL");
        }

        maps.push_back(ptr);
        
        // Progress update every 500 seconds
        if (i % 500 == 0) {
            std::cout << "[PROCESSING] Mapped and parsed " << i << " tick batches..." << std::endl;
            usleep(100000); // Slight delay to understand the command 'top'
        }
    }

    std::cout << "[SUCCESS] 10,000 tick batches parsed successfully!" << std::endl;
    return 0;
}

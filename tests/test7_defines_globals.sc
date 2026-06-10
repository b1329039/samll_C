#define PI 3
#define MAX 100

int global_count = 0;

void inc_global() {
    global_count = global_count + 1;
}

int main() {
    printf("PI is %d, MAX is %d\n", PI, MAX);
    inc_global();
    inc_global();
    printf("Global count: %d\n", global_count);
    return 0;
}

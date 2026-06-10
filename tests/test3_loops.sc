int main() {
    int i;
    printf("While loop:\n");
    i = 0;
    while (i < 5) {
        printf("%d ", i);
        i = i + 1;
    }
    printf("\nFor loop:\n");
    for (i = 0; i < 5; i = i + 1) {
        printf("%d ", i);
    }
    printf("\nDo-while loop:\n");
    i = 0;
    do {
        printf("%d ", i);
        i = i + 1;
    } while (i < 5);
    printf("\n");
    return 0;
}

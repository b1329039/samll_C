int main() {
    int x;
    printf("Please enter an integer: ");
    scanf("%d", &x);
    if (x > 0) {
        printf("Positive\n");
    } else if (x < 0) {
        printf("Negative\n");
    } else {
        printf("Zero\n");
    }
    return 0;
}

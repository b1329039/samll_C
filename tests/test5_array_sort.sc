int main() {
    int arr[5];
    int i;
    int j;
    int tmp;

    arr[0] = 5; arr[1] = 2; arr[2] = 8; arr[3] = 1; arr[4] = 9;

    printf("Original: ");
    for (i = 0; i < 5; i = i + 1) printf("%d ", arr[i]);
    printf("\n");

    for (i = 0; i < 4; i = i + 1) {
        for (j = 0; j < 4 - i; j = j + 1) {
            if (arr[j] > arr[j+1]) {
                tmp = arr[j];
                arr[j] = arr[j+1];
                arr[j+1] = tmp;
            }
        }
    }

    printf("Sorted:   ");
    for (i = 0; i < 5; i = i + 1) printf("%d ", arr[i]);
    printf("\n");
    return 0;
}

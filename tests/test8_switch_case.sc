int main() {
    int i;
    int j = 2;
    for (i = 1; i <= 3; i = i + 1) {
        printf("i = %d: ", i);
        switch (i) {
            case 1:
                printf("One\n");
                break;
            case 2:
                printf("Two\n");
                break;
            case 3:
                printf("Three\n");
                break;
            default:
                printf("Unknown\n");
        }
    }

    printf("Fall-through test:\n");
    switch (j) {
        case 1: printf("1\n");
        case 2: printf("2\n");
        case 3: printf("3\n");
        default: printf("D\n");
    }
    return 0;
}

int x = 100;

int main() {
    int x = 10;
    printf("Outer x: %d\n", x);
    {
        int x = 1;
        printf("Inner x: %d\n", x);
        int y = 20;
        printf("Inner y: %d\n", y);
    }
    // int z = 5; // This would cause error now because it's not at the start
    printf("Back to outer x: %d\n", x);
    
    // Testing strict rule
    // int error_var = 0; // Should fail if I uncomment this and put it after a statement
    return 0;
}

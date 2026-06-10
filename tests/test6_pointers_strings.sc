int main() {
    char s1[20];
    char *s2 = "Hello";
    strcpy(s1, s2);
    strcat(s1, " World");
    printf("s1: %s, length: %d\n", s1, strlen(s1));
    if (strcmp(s2, "Hello") == 0) {
        printf("s2 matches 'Hello'\n");
    }
    return 0;
}

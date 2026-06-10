int main() {
    int i = 5;
    int arr[3];
    int *p;
    
    printf("i = %d\n", i);
    printf("i++ is %d, then i is %d\n", i++, i);
    printf("++i is %d, then i is %d\n", ++i, i);
    printf("i-- is %d, then i is %d\n", i--, i);
    printf("--i is %d, then i is %d\n", --i, i);
    
    arr[0] = 10; arr[1] = 20; arr[2] = 30;
    p = arr;
    printf("*p++ is %d\n", *p++);
    printf("*p is %d\n", *p);
    return 0;
}

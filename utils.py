# Version 1: The test calculates factorials. Future versions will include optimized and diverse test cases.
def intensive_task(n):
    result = 1
    for i in range(1, n + 1):
        result *= i
    return result


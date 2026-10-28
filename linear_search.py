# Basic implementation of linear search in Python

def linear_search(arr, target):
    for index, value in enumerate(arr):
        if value == target:
            return index
    return -1

# Example usage
if __name__ == "__main__":
    arr = [2, 3, 4, 10, 40]
    target = 10
    result = linear_search(arr, target)

    if result != -1:
        print(f"Element is present at index {result}")
    else:
        print("Element is not present in array")

/* Harmless, independently authored target for MCP analysis/persistence tests. */
#include <stdio.h>

__declspec(noinline) int research_add(int left, int right) {
    return left + right;
}

int main(void) {
    const int result = research_add(19, 23);
    printf("Expedition 33 research fixture: %d\n", result);
    return result == 42 ? 0 : 1;
}

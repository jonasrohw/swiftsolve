from sandbox.run_in_sandbox import *

code = r"""
#include <iostream>

int main() {
    int n; std::cin >> n;
    long long sum = 0;
    for (int i = 0; i < n; ++i) {
        for (int j = i; j < n; ++j) {
            sum += (i + j) % 2 == 0 ? i : -j;
        }
        std::cout << sum << '\n';
    }
    return 0;
}
"""

compile_and_run(code, "20000", 2)

print(compile_and_profile(code, "20000"))

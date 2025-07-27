A list of possible optimizations to feed the LLM:

Attempt to run these before the profiler feedback.

---

Make sure to optimize input and output. Always include these two lines.

```cpp
std::cin.tie(nullptr);
std::ios_base::sync_with_stdio(false);
```

---

Optimize modulo / division operations by making them constants when possible.

For example:
```cpp
constexpr int MOD = 998244353;
int x;
std::cin >> x;
std::cout << x % MOD << '\n';
```

is always better than

```cpp
int MOD = 998244353;
int x;
std::cin >> x;
std::cout << x % MOD << '\n';
```
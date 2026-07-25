# Lambdas and Closures

## λ-calculus foundation

C++ lambdas descend from Alonzo Church's λ-calculus — a formal system in which all computation is anonymous functions, variable binding, and substitution. The three structural terms:

- **Variables** — identifiers mapping to values (`x`).
- **Abstractions** — function definitions written `λx.M`: formal parameter `x` bound in body `M`.
- **Applications** — function calls `M N`.

Execution is **β-reduction**: replace each occurrence of the bound variable with the argument expression.

> `(λx. x × 2) 4  →  4 × 2  →  8`

Pure λ-calculus can encode booleans (Church encodings), integers, conditionals, and recursion (the Y combinator) using only anonymous abstractions. It is Turing-complete (Church–Turing thesis).

Because pure λ-calculus admits only unary functions, multi-argument functions are **curried**:

> `f(x, y) = x + y  ⇒  λx. (λy. x + y)`

Applying the outer function returns an intermediate unary closure over the first argument.

## What the compiler actually emits

A C++ lambda is syntactic sugar for an anonymous, unnameable function object — a **closure type**. The compiler synthesizes a unique class type for every lambda expression in the translation unit. Structurally identical lambdas have distinct, incompatible types.

Source:

```cpp
int multiplier = 3;
auto multiply = [multiplier](int value) noexcept -> int {
    return value * multiplier;
};
```

Compiler-synthesized equivalent (conceptually):

```cpp
class __lambda_unique_id {
    int multiplier;                                  // capture → private member

public:
    __lambda_unique_id(int m) noexcept : multiplier(m) {}

    int operator()(int value) const noexcept {       // body → operator()
        return value * multiplier;
    }

    __lambda_unique_id& operator=(const __lambda_unique_id&) = delete;
};

__lambda_unique_id multiply(multiplier);
int result = multiply(5);
```

`operator()` is `const` by default.

## Capture semantics

The capture clause governs the closure type's layout, member lifetimes, and access to enclosing-scope variables.

| Capture | Meaning |
|---|---|
| `[]` | No captures. Stateless closure; the type has an implicit conversion to a raw function pointer (e.g., `int(*)(int)`). |
| `[=]` | Default capture-by-value. Each referenced variable is copied into a private member at construction. |
| `[&]` | Default capture-by-reference. Variables stored as references; risk of dangling if the closure outlives the stack frame. |
| `[x, &y]` | Mixed: `x` by value, `y` by reference. |
| `[x = std::move(p)]` | C++14 generalized capture. Init-from-expression; required for move-only captures like `std::unique_ptr`. |

To mutate a by-value capture, mark the lambda `mutable` — this strips `const` from the synthesized `operator()`:

```cpp
int counter = 0;
auto incrementer = [counter]() mutable {
    return ++counter;   // mutates the closure's copy, not the outer variable
};
```

## Performance

C++ closures are zero-overhead at runtime:

- the closure type is fully resolved at compile time;
- `operator()` is a normal member function and inlines aggressively;
- no dynamic dispatch, symbol lookup, or call-stack ceremony beyond a direct call.

Footprint = sum of captured-member sizes + alignment padding. A stateless `[]` lambda has size 1 (the standard requires distinct objects to have distinct addresses).

## Pitfalls

- `[&]` capturing locals that go out of scope → dangling reference UB.
- Capturing `this` in member-function lambdas captures a raw `this` pointer — dangerous if the closure outlives the object. Prefer `[*this]` (C++17) to capture a copy.
- Two structurally identical lambdas have *different* types — they cannot be assigned to the same variable. Use `std::function` (with type-erasure overhead) or a function pointer (only for stateless lambdas).
- Generic lambdas (`auto` parameters, C++14) are templates under the hood — each call site with a new argument type instantiates a new `operator()`. Same code-bloat dynamics as ordinary templates apply.

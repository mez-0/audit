# Audit Check Catalogue

Every check dimension the `/audit` skill evaluates. Each section is self-contained so
a dimension agent can read just its section and have everything it needs.

---

## 1. Magic Values

**What to look for:**
- Numeric literals in logic (not `0`, `1`, `-1` in obvious contexts like loop init or bool conversion)
- String literals used as keys, status codes, or identifiers in more than one place
- Repeated numeric thresholds (timeouts, retry counts, buffer sizes, port numbers)
- Bitwise masks without named constants
- HTTP status codes as bare integers (`if resp.status == 200`)
- Array indices beyond `[0]` and `[-1]` used for structural access

**What's NOT a magic value:**
- `0`, `1`, `-1` in arithmetic or loop contexts
- Strings in log messages, docstrings, or test assertions
- Numbers in test data/fixtures
- Single-use regex patterns (these are patterns, not magic values)
- Constants already defined at module level that just happen to be inlined at one call site

**Severity:** minor (single occurrence), major (same literal in 2+ places), critical (if the value has security/correctness implications — e.g. a hardcoded port that should be configurable)

**How to report:**
```
Line 45: magic number `30` used as timeout — define `REQUEST_TIMEOUT_SECONDS = 30`
Lines 45, 89, 120: magic string `"pending"` used as status — define status enum/constant
```

---

## 2. Nesting and Control Flow

**What to look for:**

### Deep nesting (>3 levels of indentation in logic)
Count logical nesting depth, not syntactic (a class body + method is +2 before any logic starts — that's fine). The smell is when the *logic itself* nests 4+ levels deep:

```python
# BAD — 4 levels of logic nesting
def process(items):
    for item in items:
        if item.valid:
            if item.type == "A":
                if item.value > threshold:
                    do_thing(item)

# GOOD — early returns flatten the logic
def process(items):
    for item in items:
        if not item.valid:
            continue
        if item.type != "A":
            continue
        if item.value <= threshold:
            continue
        do_thing(item)
```

### Missing early returns / guard clauses
Functions that wrap their entire body in an `if` condition instead of returning early:

```python
# BAD
def handle(request):
    if request.user.is_authenticated:
        # 40 lines of logic
        ...
    else:
        return HttpResponse(401)

# GOOD
def handle(request):
    if not request.user.is_authenticated:
        return HttpResponse(401)
    # 40 lines of logic, one indent level less
```

### Complex boolean expressions
- Conditions with 3+ clauses that could be named
- Negated compound conditions (`not (a and b)` → De Morgan's into `not a or not b`, or name it)
- Repeated conditions across branches

### Ternary/conditional expression abuse
- Nested ternaries
- Ternaries longer than ~80 chars

**Severity:** minor (one instance, 4 levels), major (pattern across the codebase, or >5 levels), critical (deeply nested error handling paths that might swallow exceptions)

---

## 3. Abstraction Opportunities

**What to look for:**

### Repeated code blocks
- 3+ lines of identical or near-identical code in 2+ places
- Same try/except pattern wrapped around different calls
- Same validation logic before different operations
- Copy-paste with only variable names changed

### God functions
- Functions longer than 50 lines that do more than one conceptual thing
- Functions with more than 5 parameters (should be a config/options dataclass)
- Functions that mix I/O and logic (read from DB, transform, write back — should be split)

> **The 50 is conjunctive and this matters.** Length alone is not a finding in a
> managed language — the trigger is *length **and** more than one conceptual
> thing*. `MAX_FUNCTION_LINES = 50` in `src/audit/lint.py` gives you candidates
> to read, not a list to report. Two corollaries, both paid for:
> - **Do not cite NASA Power of 10 Rule 4 here.** Its 60-line limit is a C rule
>   and lives in §14. Citing a C standard against Python manufactures an
>   authority the project never accepted.
> - **Exclude nested definitions from the enclosing function's count.** A tool
>   factory whose body is inner tool functions with long docstrings is not a god
>   function; measured on one real codebase, fifteen such factories fell from
>   >60 lines to single digits once inner defs were excluded, and the docstrings
>   were mandated by that project's own conventions.

### Missing class opportunities
- Groups of functions that all take the same first 2-3 parameters
- Dictionaries used as structs (accessing string keys for structured data)
- State passed through multiple function calls via parameters that could be instance state

### Over-abstraction (yes, this is also a smell)
- Single-use abstractions (a class with one subclass, a protocol with one implementor)
- Pass-through functions that just forward to another function
- Wrapper classes that add no behaviour
- "Strategy pattern" with one strategy

### Registry vs if/elif
- 3+ branches of `if/elif` that all do the same shape of work with different data
- `match`/`switch` statements where every case constructs a similar object

### isinstance chains
- `isinstance(x, (A, B, C, D))` with 4+ types — suggests a protocol/ABC or registry
- if/elif chains where each branch tests `isinstance` — polymorphism or visitor pattern
- The `lint_assist.py` script detects both patterns mechanically

### String literals as enum values
- The same string (`"pending"`, `"active"`, `"failed"`) passed as an argument to 3+ call sites — should be a constant or enum member
- A function receiving 2+ different short string variants in the same argument position — those variants are an enum waiting to be written
- `kwargs.get("key")` / `options.get("key")` — stringly-typed parameter access that hides the real interface behind dict lookups. Use explicit params or a `@dataclass`
- `getattr(obj, "attr_name")` for non-dunder attributes — stringly-typed, consider protocol/ABC

### **kwargs signatures
- Functions accepting `**kwargs` that aren't decorators, wrappers, or dunder methods — the signature is a lie. Callers can't see what parameters actually exist. Use explicit params or bundle into a dataclass

**Severity:** minor (small duplication, <5 lines), major (significant duplication or god functions), critical (architectural — data flows through a dict-of-dicts that should be a proper model)

---

## 4. Documentation

**What to look for:**

### Missing docstrings
- Public functions/methods without docstrings
- Classes without docstrings
- Modules without module-level docstrings (if the project convention requires them)
- **Check the project's convention first** — some projects (e.g. orbit) want full Sphinx docstrings on private helpers too; others follow "no comments" philosophy

### Misleading docstrings
- Docstring that describes what the function *used to* do (copy-paste from refactored code)
- Docstring that contradicts the actual parameters
- Generic docstring that adds no information ("Process the data" on a function called `process_data`)

### Misleading names
- Boolean variables/functions not named as predicates (`data` instead of `is_valid`)
- Functions with side effects named as pure queries (`get_user` that also logs the access)
- Variables named after their type rather than their meaning (`string`, `data`, `result`, `temp`)
- Abbreviations that aren't universally obvious (`proc` for process? procedure? processor?)

### Missing parameter documentation
- Functions with non-obvious parameters that have no `:param:` / `@param` / `Args:` docs
- Return types that aren't self-documenting and lack `:returns:` / `Returns:` docs

**Severity:** minor (missing docstring on a small helper), major (misleading name/docstring, missing docs on complex public API), critical (misleading docs on security-sensitive function)

---

## 5. Type Safety (Python)

**What to look for:**

### Missing type hints
- Functions without return type annotations
- Function parameters without type annotations
- Variables where the type isn't obvious from context and there's no annotation

### Unsafe typing
- `Any` used where a more specific type exists
- `# type: ignore` without an error code or explanation
- `cast()` without a comment explaining why it's safe
- Union types that could be narrowed with discriminated unions

### Dict-as-struct
- Functions returning `dict` where callers access specific keys by convention
- `dict[str, Any]` used to pass structured data between functions
- Tuple returns where callers unpack positionally (`name, age, email = get_user()` — should be a dataclass)

### Optional unsafety
- Functions that accept `Optional[X]` but never check for `None`
- Chains of `.get()` calls that assume the key exists
- `assert x is not None` used for runtime narrowing (should be an explicit check + raise)

**Severity:** minor (missing hint on obvious helper), major (dict-as-struct in API boundaries), critical (`Any` in security-sensitive code, unchecked `Optional` that will `AttributeError` at runtime)

---

## 6. Dead Code

**What to look for:**

### Unreachable code
- Code after `return`, `break`, `continue`, `raise`, `sys.exit()`
- Conditions that are always true/false based on prior checks
- Branches that handle impossible states (e.g. checking for a type that's excluded by a prior guard)

### Unused definitions
- Imported but unused names (though linters catch most of these)
- Functions/methods defined but never called from anywhere in the project
- Class attributes set but never read
- Variables assigned but never used

### Commented-out code
- Blocks of commented-out code (not explanatory comments — actual code that's been disabled)
- `if False:` or `if 0:` blocks
- `# TODO: re-enable this` with code below

### Dead feature flags
- Constants that are always `True`/`False` and used in conditions
- Environment variable checks where the variable is never set

**Severity:** minor (small unused helper), major (large blocks of dead code, commented-out features), critical (unreachable error handling — errors won't be caught)

---

## 7. TypeScript Patterns

**What to look for:**

### Type safety
- `any` anywhere — should be `unknown` + type guard
- `as` casts that aren't at system boundaries
- `@ts-ignore` instead of `@ts-expect-error` with a reason
- Missing discriminated unions for variant types (using `string` where a union literal fits)
- `enum` where a union type would do (enums generate runtime code)

### Boolean flag states
- Multiple `useState<boolean>` that represent mutually exclusive states
- `isLoading && isError` being possible simultaneously
- Should be a status union type: `'idle' | 'pending' | 'resolved' | 'rejected'`

### Raw JSON
- API responses used without type parsing at the boundary
- `fetch().then(r => r.json())` without typing the result
- Components receiving `any` from API calls

### Missing error handling
- `fetch()` calls without error handling
- Promises without `.catch()` or try/catch in async functions
- Optional chaining (`?.`) used defensively where the value should always exist

**Severity:** minor (single `any` in a test), major (pattern of untyped API data), critical (`any` in auth/security code)

---

## 8. React Patterns

**What to look for:**

### Derived state in useState
- `useState` for values that can be computed from other state/props
- Two `useState` calls that must be kept in sync manually
- `useEffect` that exists only to sync derived state

### Wrong useEffect usage
- `useEffect` for data transformation (should be inline computation)
- `useEffect` for event handling (should be in the event handler)
- `useEffect` for derived state (should be a `const`)
- `useEffect` with missing dependencies
- `useEffect` with `// eslint-disable-next-line react-hooks/exhaustive-deps`

### Component structure
- Components split "for readability" without a concrete symptom (perf, reuse, testing)
- Components over 300 lines without any of the 7 split triggers
- Prop drilling through 3+ levels (should be context or composition)
- `React.memo` / `useMemo` / `useCallback` without profiling evidence

### Error boundaries
- Only a global error boundary (or none)
- No Suspense boundaries for async data

### State management
- Complex state managed with multiple `useState` instead of `useReducer`
- Global state for local concerns (Zustand/Redux for single-component state)
- Stale closure bugs (using state in callbacks without deps)

**Severity:** minor (unnecessary memo), major (derived state in useState, wrong useEffect), critical (missing error boundaries on critical paths)

---

## 9. TypeScript Structure

**What to look for:**
- Barrel files (`index.ts` re-exports) that break tree-shaking
- Missing path aliases (deep relative imports like `../../../`)
- `forwardRef` usage where `ref` as prop works (React 19)
- Inline style objects in JSX not hoisted to module scope
- Direct modification of UI library files (shadcn `components/ui/`) instead of wrappers

**Severity:** minor (style), major (barrel files in hot paths, missing type boundaries)

---

## 10. Naming

**What to look for:**

### Inconsistent conventions
- Mixed `snake_case` and `camelCase` in the same language context
- Mixed naming for the same concept (sometimes `user_id`, sometimes `userId`, sometimes `uid`)
- Inconsistent verb forms (`get_user` vs `fetch_users` vs `load_user`)

### Misleading names
- `handle_error` that doesn't handle it, just logs
- `is_valid` that has side effects
- `utils.py` / `helpers.py` / `misc.py` that are grab-bags (the name tells you nothing)
- Variables named after implementation (`dict_of_users`) instead of meaning (`users_by_id`)
- Single-letter variables outside of comprehensions, loops, or well-known conventions (`i`, `j`, `k`, `x`, `y`, `n`, `e` for exception)

### Abbreviation issues
- Abbreviations that aren't domain-standard (`proc`, `mgr`, `impl`, `ctx` are borderline — domain-specific ones like `fqdn`, `ip`, `ttl` are fine)
- Same concept abbreviated differently in different files

**Severity:** minor (one-off inconsistency), major (systematic inconsistency, misleading names)

---

## 11. Error Handling

**What to look for:**

### Swallowed errors
- Bare `except:` / `except Exception:` with just `pass` or `continue`
- `try/catch` that catches everything and logs without re-raising
- Error callbacks that ignore the error parameter

### Missing error context
- `raise ValueError("invalid")` — invalid what? Add context
- `except Exception as e: raise RuntimeError("failed")` — wraps but loses the cause (should be `from e`)
- Log messages on error paths that don't include the actual error

### Wrong error granularity
- Catching broad exceptions when a specific one is expected
- Raising generic `Exception` instead of a specific error type
- Using `assert` for runtime validation (stripped in `-O` mode)

### Missing error paths
- I/O operations without error handling (file open, network calls)
- Dictionary access with `[]` that should be `.get()` (or vice versa — `.get()` that silently returns `None` when a missing key is a real error)
- Missing `finally` blocks for resource cleanup

**Severity:** minor (overly broad catch on non-critical path), major (swallowed errors, lost context), critical (swallowed errors on security/data paths, missing error handling on I/O)

---

## 12. Security

**What to look for:**

### Injection
- SQL queries built with f-strings, `.format()`, or `%` operator
- Shell commands built with string concatenation (should use `subprocess` with a list, not `shell=True`)
- HTML/template injection via unescaped user input
- LDAP injection, XPath injection, NoSQL injection (same pattern — user input in query construction)

### Secrets
- Hardcoded API keys, tokens, passwords, connection strings
- Secrets in source code comments
- Default credentials that aren't obviously test/dev fixtures
- `.env` files committed to version control (check `.gitignore`)
- Secrets logged at any level (including `DEBUG`)

### Path traversal
- File paths constructed from user input without sanitisation
- `os.path.join()` with user-controlled components (doesn't prevent `..`)
- `open()` calls with user-controlled paths

### SSRF
- URL construction from user input without allowlist validation
- Redirect following on URLs from user input
- DNS rebinding vectors (time-of-check to time-of-use on hostname resolution)

### Auth/authz
- Missing authentication checks on endpoints
- Authorisation checks that can be bypassed (IDOR — using user-supplied ID without ownership check)
- Session tokens in URLs (logged by proxies)
- Missing CSRF protection on state-changing endpoints

### Crypto
- Weak hashing (`MD5`, `SHA1` for security purposes — fine for checksums)
- Hardcoded IVs/nonces
- ECB mode
- `random` module used for security (should be `secrets`)
- Homegrown crypto (rolling your own instead of using established libraries)

**Severity:** almost always critical. Security findings that are merely informational (e.g. "you could add rate limiting") are major.

---

## Bash/Shell dimensions

If `.sh` / `.bash` files are present:

- Unquoted variables (`$var` instead of `"$var"`)
- Missing `set -euo pipefail` at the top
- Commands not checked for failure (no `|| die`, no `set -e`)
- `eval` usage
- Temp files without `mktemp`
- Race conditions in file operations
- `[` instead of `[[` (bash-specific)
- Parsing `ls` output instead of using globs/`find`
- Missing `shellcheck` directives for intentional deviations

**Severity:** minor (quoting in non-user-input contexts), major (missing error handling), critical (injection via unquoted variables in security-sensitive scripts)

---

## 13. C/C++ Safety

**Standards:** NASA/JPL Power of 10, MISRA C:2012, CERT C/C++ Coding Standard

**What to look for:**

### Memory safety
- Buffer overflows — writing past allocated bounds (arrays, strings, buffers)
  - *CERT C: ARR30-C, ARR38-C*
- Use-after-free — accessing memory after `free()` / `delete`
  - *CERT C: MEM30-C*
- Double-free — calling `free()` / `delete` on already-freed memory
  - *CERT C: MEM31-C*
- Null pointer dereference — using a pointer without checking for NULL
  - *CERT C: EXP34-C*
- Uninitialised memory — reading from uninitialised variables or allocated-but-unwritten memory
  - *CERT C: EXP33-C*
- Memory leaks — allocating without a corresponding free on all code paths
  - *CERT C: MEM31-C*
- Dangling pointers — pointers to stack-local variables returned from functions
  - *CERT C: DCL30-C*

### Integer safety
- Integer overflow / underflow — arithmetic on `int`/`unsigned` without bounds checking
  - *CERT C: INT30-C, INT32-C*
- Signed/unsigned comparison — implicit conversion bugs
  - *CERT C: INT31-C, MISRA Rule 10.4*
- Truncation — assigning a wider type to a narrower one
  - *CERT C: INT31-C*

### Undefined behaviour
- Sequence point violations — `i++ + i++`
  - *CERT C: EXP30-C*
- Strict aliasing violations — type-punning via pointer casts
  - *CERT C: EXP39-C*
- Signed integer overflow (UB in C, defined in some implementations but don't rely on it)

### String handling
- `strcpy`, `strcat`, `sprintf`, `gets` — use bounded variants (`strncpy`, `strncat`, `snprintf`, never `gets`)
  - *CERT C: STR31-C*
- Missing null terminator checks
  - *CERT C: STR32-C*
- Format string vulnerabilities — user-controlled format strings
  - *CERT C: FIO30-C, CWE-134*

### Preprocessor (NASA Rule 8)
- Token pasting (`##`) and stringification (`#`) — fragile and hard to debug
- Variadic macros — hard to get right
- Recursive macros — undefined behaviour
- Complex conditional compilation — `#ifdef` nesting deeper than 2 levels

**Severity:** critical (memory safety, UB, format strings), major (integer safety, string handling, preprocessor abuse), minor (style-level MISRA deviations)

---

## 14. C/C++ Quality

**Standards:** NASA/JPL Power of 10, Cognitive Complexity, CERT C

**What to look for:**

### Function discipline (NASA Rules 4-5)
- Functions longer than 60 lines (printed, single-page) — *NASA Rule 4*
- Functions with fewer than 2 assertions on average — *NASA Rule 5*
  - Assert preconditions, postconditions, invariants
  - `assert()` or project-specific assertion macros
- Functions with more than 6 parameters — bundle into a struct

### Scope and declarations (NASA Rule 6)
- Variables declared far from first use — declare at smallest possible scope
- Global variables — minimise, prefer function-local or file-static
- Large scope for loop variables (`int i` declared at function top, used in one loop)

### Return value discipline (NASA Rule 7)
- Return values of non-void functions unchecked — especially `malloc`, `fopen`, `read`, `write`
- `printf`/`fprintf` return values unchecked (acceptable in most contexts, but flag in error-handling paths)
- Explicit `(void)` cast when deliberately ignoring return value

### Pointer discipline (NASA Rule 9)
- More than one level of pointer dereferencing (`**p`, `***p`)
- Function pointers outside of a single dispatch/jump table
- Pointer arithmetic beyond simple array indexing

### Nesting and control flow
- Same rules as Section 2 (nesting-and-flow) but additionally:
- `goto` usage — *NASA Rule 1, MISRA Rule 15.x*
- `setjmp`/`longjmp` — *NASA Rule 1*
- Recursion — *NASA Rule 1* (all loops must have fixed upper bounds)

### Build discipline (NASA Rule 10)
- Compiler warnings not treated as errors
- Missing `-Wall -Wextra -Werror` or equivalent
- Static analyser findings not addressed

**Severity:** major (function length, missing return checks, scope violations), minor (pointer style, assertion density), critical (unchecked malloc, goto in safety-critical code)

---

## 15. Go Patterns

**Standards:** Effective Go, Go Code Review Comments, Uber Go Style Guide

**What to look for:**

### Error handling
- Unchecked errors — `val, _ := doThing()` or ignoring the error return entirely
  - *Effective Go: Errors, Uber: Handle Errors*
- Bare `if err != nil { return err }` without wrapping context — use `fmt.Errorf("context: %w", err)`
  - *Uber: Error Wrapping*
- Error strings that start with capital letters or end with punctuation (they get composed)
  - *Go Code Review Comments: Error Strings*
- Sentinel errors that should be custom types (for `errors.Is`/`errors.As`)
  - *Uber: Error Types*

### Goroutine discipline
- Goroutines launched without a way to stop them (context cancellation, done channel)
  - *Uber: No Goroutine Leaks*
- Missing `sync.WaitGroup` or equivalent for goroutine lifecycle
- Channel send/receive without timeout or context — potential deadlock
- `defer` inside a loop — deferred calls won't execute until function returns

### Naming
- Exported names without doc comments — `go vet` catches this, but flag it
  - *Effective Go: Commentary*
- Getter methods prefixed with `Get` — Go convention is `Name()` not `GetName()`
  - *Effective Go: Getters*
- Package names that stutter — `user.UserService` instead of `user.Service`
  - *Effective Go: Package Names*
- Acronyms not consistently cased — `ID` not `Id`, `URL` not `Url`
  - *Go Code Review Comments: Initialisms*

### Interface design
- Interfaces defined by the implementer instead of the consumer — Go interfaces are implicit, define them where they're used
  - *Effective Go: Interfaces*
- Large interfaces (>5 methods) — prefer small, composable interfaces
- Interface compliance not verified — use `var _ Interface = (*Struct)(nil)`
  - *Uber: Verify Interface Compliance*

### Common patterns
- `init()` functions — avoid, make dependencies explicit
  - *Uber: Avoid init()*
- Naked returns in long functions — confusing, name return values only if it improves docs
  - *Go Code Review Comments: Named Result Parameters*
- `panic` in library code — libraries should return errors, not panic
  - *Uber: Don't Panic*
- `sync.Mutex` as a struct field without embedding — embed for cleaner API, or document why not
- Missing `//go:build` constraints on platform-specific files

**Severity:** major (unchecked errors, goroutine leaks, panic in libraries), minor (naming, interface style), critical (deadlock potential, missing context cancellation)

---

## 16. Rust Patterns

**Standards:** Rust API Guidelines, Clippy Lints, ANSSI Rust Secure Coding

**What to look for:**

### Error handling
- `unwrap()` / `expect()` outside of tests or infallible contexts — use `?` or match
  - *Clippy: clippy::unwrap_used*
- `panic!` in library code — return `Result` instead
  - *ANSSI: Error handling*
- Missing `From` implementations for error type conversion
  - *Rust API Guidelines: C-GOOD-ERR*
- Opaque error types that don't implement `std::error::Error`

### Unsafe discipline
- `unsafe` blocks without a `// SAFETY:` comment explaining the invariants
  - *Clippy: clippy::undocumented_unsafe_blocks*
- `unsafe` blocks larger than necessary — minimise the unsafe surface
  - *ANSSI: Unsafe Rust*
- Raw pointer operations that could use safe abstractions
- FFI boundaries without proper validation of external data
  - *ANSSI: FFI*

### Type safety and API design
- Missing `#[must_use]` on types/functions where ignoring the result is always a bug
  - *Rust API Guidelines: C-MUST-USE*
- Stringly-typed APIs where enums or newtypes would prevent misuse
  - *Rust API Guidelines: C-NEWTYPE*
- Missing `Default`, `Debug`, `Display` implementations on public types
  - *Rust API Guidelines: C-COMMON-TRAITS*
- Leaking implementation details in public API types
  - *Rust API Guidelines: C-SEALED*

### Common patterns
- `clone()` to satisfy the borrow checker when restructuring ownership would work
  - *Clippy: clippy::redundant_clone*
- Collecting an iterator just to iterate again — `iter.collect::<Vec<_>>().iter()` instead of just using the iterator
  - *Clippy: clippy::needless_collect*
- `&String` / `&Vec<T>` in function parameters instead of `&str` / `&[T]`
  - *Clippy: clippy::ptr_arg*
- Missing `#[derive]` for standard traits
- Ignoring clippy lints with `#[allow]` without explanation

**Severity:** major (unwrap in prod, unsafe without SAFETY comment, clone abuse), minor (missing derives, API design), critical (unsafe without invariant documentation, FFI boundary bugs)

---

## 17. Offensive Tooling & OPSEC

**Standards:** See STANDARDS.md — Offensive Tooling & OPSEC section, MITRE ATT&CK

**When to apply:** Only when the codebase is offensive tooling (C2, implant, loader,
post-exploitation, security assessment). Detected by: project indicators in CLAUDE.md,
Win32 API patterns, syscall stubs, shellcode, or user confirmation.

**What to look for:**

### String artefacts
- Tool name, author name, or project-specific strings in binaries
- Debug logging strings that identify the tool or its internal structure
- Hardcoded file paths (especially build paths, PDB paths, `__FILE__`)
- Verbose error messages that fingerprint the implant vs legitimate software
- Unobfuscated configuration data (C2 addresses, keys, campaign IDs)

### API usage patterns
- Direct imports of suspicious Win32 APIs (VirtualAlloc, WriteProcessMemory, CreateRemoteThread, NtQueueApcThread, etc.) — prefer dynamic resolution
- Large import tables with unused sensitive APIs
- P/Invoke signatures matching known tool signatures
- API calls without proper error handling (detection of "are we being debugged" failing silently)
- Missing API hashing or encrypted string tables for sensitive function names

### Memory hygiene
- Secrets (keys, tokens, plaintext credentials) allocated on heap without secure zeroing
- Plaintext strings stored in global/static variables (live in memory for process lifetime)
- RWX memory regions — allocate RW, write, then change to RX
- Stack-based buffers for secrets without explicit zeroing before return
- Missing use of `SecureZeroMemory` / `RtlSecureZeroMemory` / `explicit_bzero` / `OPENSSL_cleanse`

### Network OPSEC
- Hardcoded C2 addresses or domains (should be configurable, preferably encrypted at rest)
- Fixed callback intervals without jitter — trivially detectable by network monitoring
- Distinctive protocol signatures (magic bytes, fixed headers, predictable packet sizes)
- User-Agent strings that don't match the host's installed browsers/versions
- DNS patterns that stand out (high entropy subdomains, excessive query rate, unusual TLDs)
- TLS fingerprints (JA3/JA4) that don't match legitimate software on the host
- Missing certificate pinning or validation on C2 channels (MITM risk to operator)

### Build and release hygiene
- Debug symbols (`-g`, PDB files) included in release builds
- Compiler/linker paths embedded in binary metadata
- Timestamps in PE headers that correlate to developer timezone
- Missing or expired code signing
- Deterministic build not configured (same source → different hashes reveals build environment)
- Rich headers in PE files leaking toolchain info

### Detection surface
- Patterns known to trigger EDR/AV heuristics — cross-reference with:
  - Elastic Detection Rules: https://github.com/elastic/detection-rules
  - Sigma Rules: https://github.com/SigmaHQ/sigma
  - YARA Rules: https://github.com/Yara-Rules/rules
- MITRE ATT&CK technique mapping — cite the technique ID for what the code implements (e.g. T1055.003 for thread execution hijacking)
- ETW provider interactions that generate telemetry
- AMSI/ETW unhooking patterns that are themselves detected

**Severity:** critical (plaintext C2 addresses, debug symbols in release, secrets in memory without zeroing), major (fixed callback intervals, direct API imports for sensitive calls, missing jitter), minor (user-agent mismatch, timestamp correlation)

---

## 18. Enforcement (universal)

**Standards:** none external. The authority is the project's own configuration
and style guide — this dimension audits the project against its own claims.

Every other dimension looks for code that breaks a rule. This one looks for
**rules that break nothing**: conventions the project declares and never
enforces. Those are more dangerous than an unwritten rule, because a declared
rule reads as coverage — someone checks the config, sees the rule listed, and
concludes the class of defect is handled.

**Run the checks. Do not read the config and assume it passes.** This is the
whole discipline of the dimension, and the failure it guards against is
specific: a lint rule that is configured *and failing* looks identical to a
lint rule that is working, if you only ever read the config file.

### What to look for

**Declared-but-failing.** Every rule in a `select` / `extends` / `rules` block —
run the tool and count violations. A configured rule with a non-zero count is
enforcing nothing.

```bash
ruff check . --statistics                  # every selected rule, with counts
uv run pre-commit run --all-files          # do the gating hooks actually pass?
npx eslint . --format=json | jq '[.[].messages[]] | length'
mypy . 2>&1 | tail -1 ; tsc --noEmit
```

**Declared-but-not-gating.** A hook or step that cannot fail:
- pre-commit hooks pinned to `stages: [manual]` — never run on commit
- a tool that always exits 0 (`radon`, most formatters in check-less mode) used
  where a failing gate was intended (the enforcing equivalents: `xenon` for
  complexity, `--check` / `--diff` for formatters)
- a lint config present with no CI step and no pre-commit hook invoking it
- `continue-on-error: true` on the CI step that runs it
- a test file whose tests are all skipped, xfailed, or renamed out of collection

**Written-but-unmechanised.** Imperative rules in `CLAUDE.md` / `CODE_STYLE.md`
("always", "never", "must") with no corresponding check anywhere. For each,
state whether a linter rule exists that would enforce it, and name it:
- "imports at the top of the file, always" → ruff `PLC0415`
- "no `any`, no `@ts-ignore`" → `@typescript-eslint/no-explicit-any`, `ban-ts-comment`
- "no backwards-compatibility shims" → no rule exists; needs a test
- closed vocabularies / "no magic strings" → **no lint rule exists for this in
  any language.** The enforceable form is a completeness test per enum:
  assert no production module compares against a raw member value.

Where no rule exists, say so plainly rather than proposing an approximate one —
a proxy metric enabled in place of the real rule (cyclomatic complexity standing
in for function length, say) disagrees with the stated rule in both directions
and produces argument instead of enforcement.

**Enforced-but-undeclared.** The inverse, and worth one line: a check gating CI
that appears in no style guide. Contributors cannot follow a rule they cannot
read.

### Reporting

Report one finding per declared-and-unenforced rule, not one per violation —
the violations belong to the dimension that owns the rule. State: the rule, where
it is declared, how it is (not) enforced, and the current violation count.

A tidy summary table earns its place here:

| Declared | Where | Enforced? | Violations |
|---|---|---|---|
| `select = ["F401"]` | `pyproject.toml` | configured, never gated | 29 |
| complexity gate | `.pre-commit-config.yaml` | `stages: [manual]`, exits 0 | unknown |
| "imports at the top, always" | `CLAUDE.md` | nothing | 133 (`PLC0415`) |

**Severity:** `major` for a rule that is configured and failing (it reads as
coverage and delivers none). `major` for a check that cannot fail by
construction. `minor` for a written convention with no mechanism, unless the
violation count is large enough that the convention is already dead — then
`major`.

**One caution.** Enabling a rule against a large pre-existing violation count
does not fix anything; it produces a red build, and a rule that lands red is a
rule someone disables. Where the count is large, recommend a **ratchet** (fail
on any increase against a recorded baseline) rather than a threshold. That is
enforceable on day one, and it stops the bleed, which is what the project
actually wanted from the rule it never turned on.

# Audit Standards Catalogue

Authoritative standards that audit findings bind to. During Phase 0, the skill
detects which languages are present and selects the applicable standards. Phase 1
agents cite specific rules from these standards alongside each finding.

A finding that cites a standard carries weight. A finding that just says "this is
bad practice" is an opinion. Bind every finding to at least one of these where
possible.

---

## C / C++

### NASA/JPL Power of 10 Rules
**URL:** https://spinroot.com/gerard/pdf/P10.pdf
**Scope:** nesting-and-flow, abstraction, error-handling, type-safety
**When:** C/C++ files present

Gerard Holzmann's ten rules for safety-critical code. Designed for flight
software but applicable anywhere correctness matters. The rules:

1. **No goto, setjmp, longjmp, or recursion.** All loops must have a fixed upper bound.
2. **All loops must have a fixed upper bound.** Prevent runaway iteration.
3. **No dynamic memory allocation after initialisation.**
4. **No function longer than 60 lines** (printed, single-page).
5. **Minimum two assertions per function** on average. Assert preconditions.
6. **Declare data at the smallest possible scope.**
7. **Check return values of all non-void functions,** or explicitly cast to void.
8. **Limit preprocessor use** to file includes and simple conditional compilation. No token pasting, no variadic macros, no recursive macros.
9. **Limit pointer use.** No more than one level of dereferencing. No function pointers (unless through a single jump table).
10. **Compile with all warnings enabled,** treat warnings as errors. Use static analysers daily.

### MISRA C:2012 / MISRA C++:2023
**URL:** https://www.misra.org.uk/misra-c/
**Scope:** type-safety, error-handling, security, dead-code
**When:** C/C++ files present, especially embedded/safety-critical

The motor industry standard, now used across aerospace, medical, rail. Rules are
mandatory/required/advisory. Key categories mapped to our checks:

- **Rule 1.3** — no undefined behaviour (maps to: security, error-handling)
- **Rule 2.x** — no unused code (maps to: dead-code)
- **Rule 8.x** — declarations and definitions (maps to: naming, type-safety)
- **Rule 10.x** — essential type model, no implicit conversions (maps to: type-safety)
- **Rule 11.x** — pointer conversions restricted (maps to: type-safety, security)
- **Rule 14.x** — control flow restrictions (maps to: nesting-and-flow)
- **Rule 15.x** — no goto (maps to: nesting-and-flow)
- **Rule 17.x** — function rules — return type required, check returns (maps to: error-handling)
- **Rule 21.x** — standard library restrictions — no banned functions (maps to: security)

### CERT C Coding Standard (SEI)
**URL:** https://wiki.sei.cmu.edu/confluence/display/c/SEI+CERT+C+Coding+Standard
**Scope:** security, error-handling, type-safety, memory safety
**When:** C files present

Carnegie Mellon's secure coding rules. Each rule has a risk assessment
(likelihood × remediation cost × severity). Key sections:

- **PRE** — preprocessor (macro hygiene)
- **DCL** — declarations (scope, linkage, type qualifiers)
- **EXP** — expressions (operator precedence, side effects, evaluation order)
- **INT** — integers (overflow, signedness, truncation)
- **FLP** — floating point (comparison, precision)
- **ARR** — arrays (bounds checking)
- **STR** — strings (buffer overflow, null termination)
- **MEM** — memory (allocation, deallocation, use-after-free, double-free)
- **FIO** — file I/O (TOCTOU, temp files, path traversal)
- **ENV** — environment (command injection via system(), PATH manipulation)
- **SIG** — signals
- **ERR** — error handling (errno, return codes, setjmp constraints)
- **CON** — concurrency (race conditions, deadlocks, atomics)
- **MSC** — miscellaneous (dead code, sizeof misuse)

### CERT C++ Coding Standard (SEI)
**URL:** https://wiki.sei.cmu.edu/confluence/display/cplusplus/SEI+CERT+C%2B%2B+Coding+Standard
**Scope:** security, error-handling, type-safety, abstraction
**When:** C++ files present

Extends CERT C with C++-specific rules:

- **DCL** — declarations (auto, constexpr, inline variables)
- **EXP** — expressions (narrowing conversions, std::move semantics)
- **INT** — integer handling
- **CTR** — containers (iterator invalidation, bounds)
- **STR** — strings (std::string vs C strings)
- **MEM** — memory (smart pointers, RAII, placement new)
- **OOP** — OO patterns (virtual destructors, slicing, Liskov)
- **ERR** — exceptions (exception safety guarantees, noexcept)
- **CON** — concurrency (mutex, condition variables, atomics)

---

## Python

### PEP 8 — Style Guide
**URL:** https://peps.python.org/pep-0008/
**Scope:** naming, magic-values, nesting-and-flow
**When:** Python files present

The baseline style guide. Most projects layer conventions on top.

### PEP 257 — Docstring Conventions
**URL:** https://peps.python.org/pep-0257/
**Scope:** documentation
**When:** Python files present

### PEP 484 / 526 / 585 / 604 — Type Hints
**URLs:**
- https://peps.python.org/pep-0484/ (function annotations)
- https://peps.python.org/pep-0526/ (variable annotations)
- https://peps.python.org/pep-0585/ (generics in stdlib — `list[int]` not `List[int]`)
- https://peps.python.org/pep-0604/ (union syntax — `X | Y` not `Union[X, Y]`)

**Scope:** type-safety
**When:** Python files present

### Google Python Style Guide
**URL:** https://google.github.io/styleguide/pyguide.html
**Scope:** naming, documentation, abstraction, error-handling
**When:** Python files present

Stricter than PEP 8 on several points. Key sections:
- **2.x** — imports, exceptions, mutables as defaults, comprehensions, generators
- **3.x** — docstrings (mandatory on public), comments, type annotations
- **4.x** — naming (module_name, ClassName, function_name, CONSTANT_NAME)

### Ruff Rule Reference
**URL:** https://docs.astral.sh/ruff/rules/
**Scope:** all Python dimensions
**When:** Python files present

Check what the project already enables before flagging something ruff would catch.

### Cognitive Complexity (SonarSource)
**URL:** https://www.sonarsource.com/docs/CognitiveComplexity.pdf
**Scope:** nesting-and-flow, abstraction
**When:** any language

Better nesting metric than cyclomatic complexity. Penalises nesting and
flow-breaking more heavily.

---

## Go

### Effective Go
**URL:** https://go.dev/doc/effective_go
**Scope:** naming, error-handling, abstraction, nesting-and-flow
**When:** Go files present

The canonical Go style reference. Key patterns:
- Error handling — `if err != nil` immediately, no nesting
- Naming — MixedCaps, short names for local scope, getters without `Get` prefix
- Interfaces — small, accept interfaces return structs
- Goroutines — ensure cleanup, avoid leaks

### Go Code Review Comments
**URL:** https://go.dev/wiki/CodeReviewComments
**Scope:** naming, documentation, error-handling, type-safety
**When:** Go files present

Community-maintained list of common review comments. Supplements Effective Go.

### Uber Go Style Guide
**URL:** https://github.com/uber-go/guide/blob/master/style.md
**Scope:** error-handling, abstraction, naming, security
**When:** Go files present

Production-hardened patterns:
- Interface compliance (`var _ Interface = (*Struct)(nil)`)
- Error wrapping with `%w`
- Avoid naked returns
- Avoid `init()`
- Functional options pattern
- Table-driven tests

### Google Go Style Guide
**URL:** https://google.github.io/styleguide/go/
**Scope:** naming, documentation, abstraction
**When:** Go files present

---

## Rust

### Rust API Guidelines
**URL:** https://rust-lang.github.io/api-guidelines/
**Scope:** naming, documentation, type-safety, abstraction
**When:** Rust files present

How to design Rust library APIs:
- Naming conventions (C-CASE, C-CONV)
- Type safety (C-NEWTYPE, C-CUSTOM-TYPE)
- Documentation (C-EXAMPLE, C-QUESTION-MARK)
- Interoperability (C-COMMON-TRAITS)

### Clippy Lint Categories
**URL:** https://rust-lang.github.io/rust-clippy/master/
**Scope:** all Rust dimensions
**When:** Rust files present

Organised by category:
- `clippy::correctness` — definite bugs
- `clippy::suspicious` — very likely bugs
- `clippy::complexity` — unnecessarily complex code
- `clippy::perf` — performance improvements
- `clippy::style` — deviations from idiomatic Rust
- `clippy::pedantic` — stricter lints

### Rust Secure Coding Guidelines (ANSSI)
**URL:** https://anssi-fr.github.io/rust-guide/
**Scope:** security, error-handling, type-safety
**When:** Rust files present

French national cybersecurity agency guidelines for Rust:
- Memory safety (even in safe Rust — logic errors)
- Integer overflow handling
- Unsafe block discipline
- FFI boundary safety
- Cryptographic library selection

---

## TypeScript / JavaScript

### Google TypeScript Style Guide
**URL:** https://google.github.io/styleguide/tsguide.html
**Scope:** naming, type-safety, ts-patterns
**When:** TypeScript files present

### React — You Might Not Need an Effect
**URL:** https://react.dev/learn/you-might-not-need-an-effect
**Scope:** react-patterns
**When:** React files present

The canonical anti-pattern table for `useEffect`.

### React — Choosing the State Structure
**URL:** https://react.dev/learn/choosing-the-state-structure
**Scope:** react-patterns
**When:** React files present

Five principles: group related state, avoid contradictions, avoid redundancy,
avoid duplication, avoid deeply nested state.

### React — Thinking in React
**URL:** https://react.dev/learn/thinking-in-react
**Scope:** react-patterns, ts-structure
**When:** React files present

### React TypeScript Cheatsheets
**URL:** https://react-typescript-cheatsheet.netlify.app/
**Scope:** ts-patterns, react-patterns
**When:** React + TypeScript files present

### Bulletproof React
**URL:** https://github.com/alan2207/bulletproof-react
**Scope:** ts-structure, react-patterns
**When:** React files present

### Total TypeScript — Matt Pocock
**URL:** https://www.totaltypescript.com/tips
**Scope:** ts-patterns
**When:** TypeScript files present

### Node.js Best Practices
**URL:** https://github.com/goldbergyoni/nodebestpractices
**Scope:** error-handling, security, abstraction, ts-structure
**When:** Node.js project detected

80+ best practices, key sections:
- Error handling — async/await error handling, operational vs programmer errors
- Security — input validation, dependency security, HTTP headers
- Project structure — component-based, layer isolation
- Testing — test pyramid, property-based testing

---

## Shell / Bash

### ShellCheck Wiki
**URL:** https://www.shellcheck.net/wiki/
**Scope:** all shell dimensions
**When:** Shell files present

Every ShellCheck rule with examples. The authoritative reference.

### Google Shell Style Guide
**URL:** https://google.github.io/styleguide/shellguide.html
**Scope:** naming, error-handling, abstraction
**When:** Shell files present

### Bash Pitfalls
**URL:** https://mywiki.wooledge.org/BashPitfalls
**Scope:** all shell dimensions
**When:** Shell files present

The classic list of common bash mistakes.

---

## Architecture & Design (language-agnostic)

These apply to every audit regardless of language. They inform the abstraction,
naming, and structural dimensions.

### SOLID Principles
**URL:** https://en.wikipedia.org/wiki/SOLID
**Scope:** abstraction, ts-structure

- **S** — Single Responsibility. One reason to change.
- **O** — Open/Closed. Open for extension, closed for modification.
- **L** — Liskov Substitution. Subtypes must be substitutable.
- **I** — Interface Segregation. No forced unused dependencies.
- **D** — Dependency Inversion. Depend on abstractions.

### 12-Factor App
**URL:** https://12factor.net/
**Scope:** abstraction, error-handling, security

Key factors for audit relevance:
- **III** — Config in environment, not code (maps to: magic-values, security — hardcoded secrets)
- **VI** — Stateless processes (maps to: abstraction — hidden state)
- **XI** — Logs as event streams (maps to: error-handling — structured logging)
- **XII** — Admin processes as one-off (maps to: abstraction — scripts vs embedded commands)

### A Philosophy of Software Design (John Ousterhout)
**URL:** N/A (book)
**Scope:** abstraction

Core vocabulary:
- **Deep modules** — simple interface, complex implementation (good)
- **Shallow modules** — complex interface, trivial implementation (smell)
- **Pass-through methods** — add nothing, just forward (dead weight)
- **Information leakage** — same knowledge in multiple places

### Domain-Driven Design — Tactical Patterns
**URL:** https://www.domainlanguage.com/ddd/reference/
**Scope:** abstraction, naming

- Entities, Value Objects, Aggregates, Domain Events
- Ubiquitous Language — names in code should match the domain

---

## Security Standards

Always applied. These are the backbone of the security dimension.

### OWASP Top 10 (2021)
**URL:** https://owasp.org/Top10/
**Scope:** security

Every security finding should map to one of these:
1. A01 — Broken Access Control
2. A02 — Cryptographic Failures
3. A03 — Injection
4. A04 — Insecure Design
5. A05 — Security Misconfiguration
6. A06 — Vulnerable and Outdated Components
7. A07 — Identification and Authentication Failures
8. A08 — Software and Data Integrity Failures
9. A09 — Security Logging and Monitoring Failures
10. A10 — Server-Side Request Forgery (SSRF)

### OWASP Application Security Verification Standard (ASVS) v4.0
**URL:** https://owasp.org/www-project-application-security-verification-standard/
**Scope:** security

Three verification levels (L1/L2/L3). More granular than Top 10. Key chapters:
- V2 — Authentication
- V3 — Session Management
- V4 — Access Control
- V5 — Validation, Sanitization, Encoding
- V6 — Stored Cryptography
- V7 — Error Handling and Logging
- V8 — Data Protection
- V9 — Communication
- V10 — Malicious Code (backdoors, logic bombs)
- V12 — Files and Resources
- V13 — API and Web Service
- V14 — Configuration

### OWASP Cheat Sheet Series
**URL:** https://cheatsheetseries.owasp.org/
**Scope:** security

Concrete remediation per vulnerability class:
- SQL Injection Prevention — https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html
- XSS Prevention — https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html
- SSRF Prevention — https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html
- Input Validation — https://cheatsheetseries.owasp.org/cheatsheets/Input_Validation_Cheat_Sheet.html
- Authentication — https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html
- Command Injection — https://cheatsheetseries.owasp.org/cheatsheets/OS_Command_Injection_Defense_Cheat_Sheet.html
- Cryptographic Storage — https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html
- Secrets Management — https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html

### CWE Top 25 Most Dangerous Software Weaknesses
**URL:** https://cwe.mitre.org/top25/archive/2023/2023_top25_list.html
**Scope:** security

More granular than OWASP. Key CWEs for code audit:
- CWE-787 — Out-of-bounds Write
- CWE-79 — Cross-site Scripting (XSS)
- CWE-89 — SQL Injection
- CWE-416 — Use After Free
- CWE-78 — OS Command Injection
- CWE-20 — Improper Input Validation
- CWE-125 — Out-of-bounds Read
- CWE-22 — Path Traversal
- CWE-352 — Cross-Site Request Forgery
- CWE-434 — Unrestricted Upload
- CWE-862 — Missing Authorization
- CWE-476 — NULL Pointer Dereference
- CWE-287 — Improper Authentication
- CWE-190 — Integer Overflow
- CWE-502 — Deserialization of Untrusted Data
- CWE-77 — Command Injection
- CWE-119 — Buffer Overflow

### NIST Secure Software Development Framework (SSDF)
**URL:** https://csrc.nist.gov/projects/ssdf
**Scope:** security, error-handling

Practices grouped as:
- **PO** — Prepare the Organisation (tooling, policy)
- **PS** — Protect the Software (source integrity, build security)
- **PW** — Produce Well-Secured Software (design, code review, testing)
- **RV** — Respond to Vulnerabilities

### Bandit (Python Security Linter)
**URL:** https://bandit.readthedocs.io/en/latest/plugins/index.html
**Scope:** security (Python)
**When:** Python files present

Plugin reference. Useful for understanding automated vs manual review boundary.

### Semgrep Community Rules
**URL:** https://semgrep.dev/r
**Scope:** security (all languages)

Community-maintained pattern database. Cross-reference whether a finding is
well-known or novel.

---

## Offensive Tooling & OPSEC

Applied when the codebase is offensive tooling — C2 frameworks, implants, loaders,
post-exploitation tools, security assessment utilities. Detected by: presence of
Win32 API imports, syscall stubs, shellcode patterns, C2 protocol code, or
explicit project indicators (CLAUDE.md mentioning offensive/C2/implant).

These aren't "coding standards" in the traditional sense — they're operational
discipline rules. A violation doesn't break compilation; it breaks the operation.

### OPSEC Hygiene

**String Artefacts:**
- Hardcoded strings that identify the tool (tool name, author, debug paths, PDB paths)
- Format strings that leak internal structure (`[DEBUG] Sending beacon to %s`)
- Verbose error messages that fingerprint the implant
- Unencrypted/unobfuscated configuration data at rest

**API Usage Patterns:**
- Direct Win32 API imports for sensitive functions (VirtualAlloc, CreateRemoteThread, etc.) — prefer dynamic resolution or syscalls
- Import table bloat — importing APIs you don't use or that are IOC-heavy
- Unsafe P/Invoke signatures that could be flagged by static analysis
- Missing API hashing or dynamic resolution for sensitive calls

**Memory Hygiene:**
- Secrets (keys, tokens, credentials) not zeroed after use
- Plaintext strings lingering in memory (process dumps reveal them)
- RWX memory regions (highly suspicious — use RW then RX)
- Heap allocations for sensitive data without secure deallocation
- Missing `SecureZeroMemory` / `RtlSecureZeroMemory` for secrets

**Network OPSEC:**
- Hardcoded C2 addresses/domains
- Unencrypted C2 channels
- Distinctive protocol patterns (fixed magic bytes, predictable packet sizes)
- Missing jitter in callback intervals
- DNS queries that stand out (unusual TLD, high entropy subdomains, excessive query rate)
- User-Agent strings that don't match the host environment
- TLS configurations that don't match legitimate traffic (JA3/JA4 fingerprints)

**Build & Release:**
- Debug symbols left in release builds
- Build paths embedded in binaries (PDB paths, `__FILE__` macros)
- Compiler-specific artefacts that reveal toolchain
- Missing code signing (or using a burned cert)
- Timestamps that correlate to developer timezone

### MITRE ATT&CK Framework
**URL:** https://attack.mitre.org/
**Scope:** security (offensive tooling context)

Not a coding standard, but findings in offensive tooling should reference the
ATT&CK technique they implement or could enable. This helps correlate audit
findings with detection coverage.

Key technique categories for code audit:
- **T1055** — Process Injection (code quality of injection primitives)
- **T1027** — Obfuscated Files or Information (quality of obfuscation)
- **T1059** — Command and Scripting Interpreter (injection risks in command execution)
- **T1071** — Application Layer Protocol (C2 protocol implementation quality)
- **T1547** — Boot or Logon Autostart Execution (persistence mechanism hygiene)
- **T1003** — OS Credential Dumping (memory handling around credentials)

### Detection Surface References
**URLs:**
- Elastic Detection Rules — https://github.com/elastic/detection-rules
- Sigma Rules — https://github.com/SigmaHQ/sigma
- YARA Rules — https://github.com/Yara-Rules/rules

These tell you what defenders look for. An audit finding in offensive tooling
should note when a pattern is likely to trigger a known detection rule.

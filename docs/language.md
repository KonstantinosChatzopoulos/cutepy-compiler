# The CutePy language

CutePy is a small language for teaching compiler construction. The course instructor designed it for the Compilers course at the University of Ioannina. Its syntax borrows from Python, and every CutePy program is also a valid Python program: the CutePy-specific parts (`#{`, `#}`, `#declare`, `#$ ... #$`) are Python comments.

This page summarizes the language in our own words. The official specification is course material and isn't included here.

## Data and lexical rules

- **Types:** integers only. Constants have an optional sign and must be within ±(2³² − 1).
- **Identifiers:** start with a letter, then letters, digits and `_`. At most 30 characters.
- **Keywords:** `def`, `if`, `else`, `while`, `return`, `print`, `int`, `input`, `and`, `or`, `not`, `declare`
- **Comments:** between `#$` and `#$`.
- **Whitespace:** spaces, tabs and newlines are ignored (indentation has no meaning).

## Program structure

A program has two parts:

1. **Main functions:** one or more functions whose names start with `main_`. They take no parameters and return nothing.
2. **The call section:** `if __name__ == "__main__":` followed by calls to the main functions.

```python
def main_hello():
#{
    #declare x
    x = 42;
    print(x);
#}
if __name__ == "__main__":
    main_hello();
```

Each function body is a block between `#{` and `#}`, in this order:
1. declarations
2. local functions
3. statements

## Declarations

```python
#declare a, b
#declare total
```

Variables declared in a `main_` function are global to its local functions. Variables declared in a local function are local to it.

## Local functions

```python
def power(b, e):
#{
    if (e == 0):
        return (1);
    return (b * power(b, e - 1));
#}
```

- Parameters are passed by value.
- Functions can be nested and can be recursive.
- A function sees its own variables and parameters, those of every enclosing function, and the globals (static scoping, as in Pascal). Inner names hide outer ones.
- A function is called inside an expression: `x = power(2, 10);`

## Statements

| Statement | Syntax |
|---|---|
| Assignment | `x = expression;` |
| Input | `x = int(input());` |
| Output | `print(expression);` |
| Return | `return (expression);` |
| If | `if (condition):` statement or `#{ statements #}`, optionally followed by `else:` statement or `#{ statements #}` |
| While | `while (condition):` statement or `#{ statements #}` |

Simple statements end with `;`. `if` and `while` don't.

## Expressions and conditions

- **Arithmetic operators:** `*` and `//` (integer division) bind tighter than `+` and `-`. Parentheses `( )` group sub-expressions.
- **Relational operators:** `==`, `!=`, `<`, `<=`, `>`, `>=`
- **Logical operators:** `not`, then `and`, then `or` (from highest to lowest precedence). Square brackets `[ ]` group conditions, the way parentheses group arithmetic:

```python
if ([k <= limit] and not [k == 0]):
    return (k);
```

## Examples

See [../examples/](../examples/) for complete programs and the code the compiler generates for them.

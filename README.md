# StructDiff

**See what a change did to your code — not which characters moved.**

`structdiff` compares two versions of a Python file at the level of *structure*
instead of text, and renders the result as one interactive picture: every
function and class becomes a block, blocks are coloured by what happened to
them, and curves tie each block to its counterpart in the other version.

```console
$ structdiff before.py after.py --open
structdiff: 3 added, 1 removed, 2 modified, 1 unchanged, LOC 55 -> 47 (-8)
wrote after.structdiff.html (26 KB)
```

One HTML file, no server, no CDN, no JavaScript dependencies. It works on a
laptop with the Wi-Fi turned off.

---

## Why

A line diff answers *"which lines changed?"*. When you review a refactor, that
is usually the wrong question. Moving twenty lines from one function into two
new ones produces a wall of red and green, and yet nothing about the program
changed except its shape. Conversely, a one-character edit inside a condition
can quietly raise a function's complexity without looking dramatic.

StructDiff asks the structural questions instead:

- Which functions and classes appeared, disappeared, or changed?
- Did a function get *bigger*, or did it just move?
- Did its branching complexity go up while its line count went down?
- Is the function you are looking at the same function as before, only renamed?

The picture is built for two audiences:

- **Learners.** Compare your solution with the reference implementation: the
  blocks show where your decomposition differs, not just where your text
  differs.
- **Teachers.** Show a class what a refactor actually did. "I split one
  60-line function into four" is a sentence; the before/after map is an
  argument.

## What you see

```
before.py                       after.py
┌───────────────────────┐       ┌───────────────────────┐
│ load_rows          4  │───────│ load_rows          4  │  unchanged
│ parse_scores       6  │───────│ parse_scores       7  │  modified
│ process           18  │   ╳   │ letter_grade       3  │  added
│ main               2  │───╮   │ build_report       9  │  added
└───────────────────────┘   ╰───│ format_csv         4  │  added
                                │ main               2  │  modified
                                └───────────────────────┘
```

| Visual | Meaning |
| --- | --- |
| One block | One function, method, or class |
| Indentation | Lexical nesting (methods sit under their class) |
| Thin bar in the block | Lines of code, relative to the largest symbol in the diff |
| Number on the right | Cyclomatic complexity (`7→10` when it changed) |
| Green / red / amber / violet | added / removed / modified / renamed |
| Curve between columns | The same symbol in both versions |
| Click a block | Side-by-side source of just that symbol, with changed lines marked |

A summary strip on top totals the changes: symbol counts, lines of code, and
complexity for both versions.

## Install

```console
pip install structdiff
```

Python 3.9+. No dependencies.

From a checkout, without installing:

```console
set PYTHONPATH=src          # Windows
export PYTHONPATH=src       # macOS / Linux
python -m structdiff examples/before.py examples/after.py -o demo.html
```

## Use

### Command line

```console
structdiff OLD.py NEW.py
structdiff OLD.py NEW.py -o report.html --open
structdiff my_solution.py reference.py \
    --old-label "my code" --new-label "reference" \
    --title "Exercise 3"
structdiff OLD.py NEW.py --json        # summary only, for scripts
```

| Option | Meaning |
| --- | --- |
| `-o, --output` | Where to write the report (default: `<new>.structdiff.html`) |
| `--old-label`, `--new-label` | Column headings |
| `--title` | Report title |
| `--json` | Print the summary as JSON and exit |
| `--open` | Open the report in the default browser |
| `-q, --quiet` | Print nothing on success |

Exit codes: `0` success, `2` unreadable file or syntax error.

### Python

```python
from structdiff import diff_files, diff_sources, render_html, write_report

result = diff_files("before.py", "after.py")
print(result.summary())
# {'added': 3, 'removed': 1, 'modified': 2, 'unchanged': 1, ...}

write_report(result, "report.html", title="Refactor review")

# or work on strings, e.g. from a web form or a notebook
result = diff_sources(old_source, new_source, "v1", "v2")
html = render_html(result)
```

Useful pieces of the result:

```python
for pair in result.pairs:
    print(pair.status.value, pair.name, pair.old and pair.old.loc, pair.new and pair.new.loc)
```

### In CI

```yaml
- run: structdiff main.py pr.py --json
```

## How it works

```
source ──► parser.py ──► FileModel (tree of Symbols)
                            │
                            ▼
                         matcher.py ──► pairs + status
                            │
                            ▼
                         layout.py ──► x / y for every block
                            │
                            ▼
                         render.py ──► SVG + JSON  ──► one .html
```

1. **Parse** with `ast`. Each `def` / `async def` / `class` becomes a `Symbol`
   carrying its line span, non-blank line count, cyclomatic complexity,
   parameter count, and a hash of its syntax tree.
2. **Match** old symbols to new ones in three passes: same qualified name;
   same syntax-tree hash (this is how a rename is recognised as a rename);
   then fuzzy name similarity within the same kind. Everything unmatched is
   added or removed.
3. **Lay out** each side as an indented outline in document order.
4. **Render** static SVG in Python and ship the source slices as JSON for the
   click-through panel. The browser only handles hover, filter and the panel.

Design choices worth knowing:

- **Your code is never executed or imported.** It is parsed, nothing more, so
  a diff of untrusted code is safe.
- **The report is one file.** Styles, script and data are inlined; the data
  script tag escapes `</` so source containing markup cannot break out.
- **The output is a document, not a screenshot.** PNG export is on the
  roadmap; the interactive HTML is the product.

## Limits and roadmap

Known limits of the current skeleton:

- Module-level code inside `if` / `try` blocks is not collected as symbols.
- Matching a heavily rewritten function falls back to *removed + added*
  rather than *modified*.
- Very large files (thousands of symbols) are drawn as one long column; a
  collapse/expand control is needed.
- No PNG / SVG export yet, and no directory-to-directory mode.

Roadmap, roughly in order:

- [ ] Collapse nested symbols; keep classes folded by default
- [ ] Export the current view to PNG and SVG
- [ ] A "structure only" diff of two directories (module-level view)
- [ ] `--fail-on` thresholds for CI (e.g. complexity regression)
- [ ] Optional side-by-side unified diff mode for a single symbol

## Development

```console
git clone https://github.com/wyzzz12548/structdiff
cd structdiff
set PYTHONPATH=src
python -m unittest discover -s tests -t .
```

The package is a `src/` layout with no runtime dependencies, so tests run
against the checkout directly.

```
src/structdiff/
├── model.py      dataclasses: Symbol, FileModel, Pair, Status
├── parser.py     ast -> Symbol tree, LOC, complexity
├── matcher.py    three-pass symbol matching
├── diff.py       DiffResult + summary
├── layout.py     geometry for the two columns
├── render.py     SVG, payload, HTML assembly
├── cli.py        argparse front end
└── templates/    viewer.html / viewer.css / viewer.js
```

## License

MIT. See [LICENSE](LICENSE).

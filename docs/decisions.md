# Decisions

## 2026-07-28 - Rows and descriptors compare by value

**What:** `DataFileDescriptor` got `__eq__`/`__hash__` over the data file layout it describes,
so rows from two readers over the same archive now compare equal.
**Why:** Row equality embeds the descriptor; with identity-based comparison, rows identical in
data, raw_fields, id, position and rowtype still compared unequal across readers.
**Rejected:** Documenting the single-reader scope on `CoreRow.__eq__` instead - a descriptor
describes a file layout, not the reader that built it, so identity comparison was a bug rather
than a boundary worth keeping.

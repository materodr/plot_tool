# Requirements Format

Every requirement in this folder follows the format below.

## Requirement IDs

An ID is a prefix, a hyphen and a 5-digit integer padded with zeros: `<PREFIX>-<NNNNN>`.

| Prefix | Meaning | File |
|---|---|---|
| `COR` | Code and organization requirement | [code_and_organization.md](code_and_organization.md) |
| `PCR` | Process of collaboration requirement | [process_of_collaboration.md](process_of_collaboration.md) |
| `HLFR` | High-level functional requirement | to be added |
| `LLFR` | Low-level functional requirement | to be added |

- Numbers are plain integers counted from 1 (`00001`, `00002`, ...). Each prefix has its own count.
- Five digits give room for 10000 requirements per prefix and beyond (up to `99999`).
- No sub-numbering (no `1.2`). An LLFR is linked to its HLFR with a `Parent:` line, not through its number.
- An ID is never reused or renumbered. New requirements continue from the next number, even after a deletion.
- A deleted requirement keeps its ID in the file, and its title and text are replaced by `DELETED` (PCR-00027).
- Regular expression for a valid ID: `^(COR|PCR|HLFR|LLFR)-\d{5}$`

## Requirement entry

Each requirement is a level-3 heading with the ID and a short title, followed by the requirement statement:

```markdown
### COR-00001 Programming language
The code must be written in Python.
```

A requirement may end with an optional `Note:` line that adds guidance without adding a new requirement:

```markdown
### PCR-00004 Issue for every change
A GitHub issue must be created to track the development of every fix and new feature.

Note: Every issue must be created from one of the two templates: Fix or Feature.
```

A deleted requirement:

```markdown
### PCR-00099 DELETED
DELETED
```

An LLFR also names its parent HLFR:

```markdown
### LLFR-00001 <short title>
Parent: HLFR-00001
<statement>
```

# repobrain review

Analyze the blast radius and risk score of a pull request.

## Usage

```bash
repobrain review <PR_NUMBER_OR_BRANCH> [OPTIONS]
```

## Options

| Option | Default | Description |
|--------|---------|-------------|
| `--format` | `table` | Output format: `table`, `json`, `markdown` |
| `--max-depth N` | `3` | Transitive dependency traversal depth |
| `--no-transitive` | — | Only show direct changed files |

## Output

```
PR #42 — Add user authentication

DIRECT FILES (3)
  src/auth/login.py          risk: 8.2  centrality: 0.71  owner: alice@co.com
  src/auth/tokens.py         risk: 7.4  centrality: 0.65  owner: alice@co.com
  src/models/user.py         risk: 6.1  centrality: 0.58  owner: bob@co.com

TRANSITIVE DEPENDENTS (12)
  src/api/endpoints.py       risk: 5.3  (imports src/auth/login.py)
  src/tests/test_login.py    risk: 2.1  (imports src/auth/login.py)
  ...

CO-CHANGE WARNINGS
  src/auth/middleware.py is historically changed with src/auth/login.py (72% co-change)
  — but is NOT in this PR. Review recommended.

RECOMMENDED REVIEWERS
  alice@co.com  (owns 2/3 direct files)
  bob@co.com    (owns 1/3 direct files, 8/12 transitive files)

OVERALL RISK SCORE: 7.8 / 10.0  [HIGH]
```

## Risk Score Formula

```
risk = centrality × temporal_hotspot × (1 + test_gap_score)
```

Normalized to 0–10 across the repository.

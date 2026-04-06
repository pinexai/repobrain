# repobrain costs

Show LLM spend breakdown for all repobrain operations.

## Usage

```bash
repobrain costs [OPTIONS]
```

## Options

| Option | Default | Description |
|--------|---------|-------------|
| `--since DATE` | all time | Filter to costs since DATE (YYYY-MM-DD) |
| `--by` | `operation` | Group by: `operation`, `file`, `model`, `day` |
| `--top N` | 20 | Show top N entries |

## Example Output

```
repobrain costs --by operation

OPERATION          CALLS   INPUT TOKENS   OUTPUT TOKENS   COST
doc_generation       523      2,341,000         891,000   $4.23
explain_file          47        188,000          76,000   $0.38
search_codebase       31         62,000          18,000   $0.09
get_pr_impact         12         48,000          22,000   $0.07

TOTAL                613      2,639,000       1,007,000   $4.77
```

## Powered by tokenspy

repobrain uses [tokenspy](https://github.com/pinexai/tokenspy) to track costs. Every Anthropic call is wrapped by `TokenspyCostAdapter` which records tokens and estimated cost to the SQLite database.

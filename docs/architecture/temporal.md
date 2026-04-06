# Temporal Scoring

repomind weights recent commits exponentially more than old commits. This means a file changed 10 times last week ranks higher than a file changed 100 times 3 years ago.

## The Formula

```python
for commit in commits:
    age_days = (now - commit.authored_date).days
    decay = exp(-ln(2) * age_days / halflife_days)
    complexity = min(commit.lines_changed / 100.0, 3.0)
    score += decay * complexity
```

**Parameters:**
- `halflife_days` (default: 180) — time after which a commit contributes half its original weight
- `complexity` — capped at 3× to prevent single massive commits from dominating

## Intuition

With `halflife_days = 180`:

| Commit age | Weight |
|------------|--------|
| Today | 1.00 |
| 6 months ago | 0.50 |
| 1 year ago | 0.25 |
| 2 years ago | 0.06 |
| 3 years ago | 0.015 |

## Percentile Ranks

After every `upsert()`, repomind runs:

```sql
UPDATE git_metrics
SET percentile_rank = (
    SELECT PERCENT_RANK() OVER (ORDER BY temporal_hotspot_score)
    FROM git_metrics gm2
    WHERE gm2.file_id = git_metrics.file_id
)
```

This means hotspot rankings are always globally consistent — even after incremental updates that only touch a few files.

## Configuring Halflife

```bash
# More aggressive decay (recent activity matters more)
REPOMIND_DECAY_HALFLIFE_DAYS=90

# Balanced (default)
REPOMIND_DECAY_HALFLIFE_DAYS=180

# Historical view (all history equally weighted)
REPOMIND_DECAY_HALFLIFE_DAYS=3650
```

# Tool Contracts

## Conventions

- All timestamps are ISO-8601 strings.
- Empty/no-history results return an empty array plus an explanatory "note" field, never an error.
- The similarity threshold for `flag_recurring_mistake` is 0.3 on cosine distance, defined as a single named constant (not duplicated across files).

## 1. get_problem_context

### Input
```json
{
  "user_id": "uuid",
  "problem_statement": "string"
}
```

### Output
```json
{
  "matches": [
    {
      "attempt_id": "uuid",
      "outcome": "pass | fail | partial",
      "complexity_achieved": "string",
      "mistake_summary": "string or null",
      "distance": 0.18
    }
  ],
  "note": "string, present only when matches is empty"
}
```

## 2. log_attempt

### Input
```json
{
  "user_id": "uuid",
  "problem_id": "uuid",
  "code": "string",
  "outcome": "pass | fail | partial",
  "complexity_achieved": "string or null",
  "time_taken_seconds": "int or null"
}
```

### Output
```json
{
  "attempt_id": "uuid",
  "status": "logged",
  "mastery_score_after": 0.42
}
```

## 3. get_mastery_report

### Input
```json
{
  "user_id": "uuid",
  "topic": "string or null"
}
```

### Output
```json
{
  "topics": [
    {
      "slug": "sliding-window",
      "mastery_score": 0.42,
      "last_practiced_at": "ISO-8601 timestamp or null"
    }
  ]
}
```

## 4. suggest_next_problem

### Input
```json
{
  "user_id": "uuid"
}
```

### Output
```json
{
  "recommendation": {
    "id": "uuid",
    "title": "string",
    "difficulty": "easy | medium | hard"
  },
  "targeted_topic": "string",
  "mastery_score": 0.42,
  "reason": "string or null"
}
```
*(recommendation is null with a reason string when nothing qualifies)*

## 5. flag_recurring_mistake

### Input
```json
{
  "user_id": "uuid",
  "code_in_progress": "string"
}
```

### Output
```json
{
  "flagged": [
    {
      "summary": "string",
      "category": "string",
      "distance": 0.19,
      "occurrences": 4
    }
  ],
  "checked": true
}
```

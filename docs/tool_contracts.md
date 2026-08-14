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

## 6. get_or_create_user

### Input
```json
{
  "email": "string",
  "display_name": "string or null"
}
```

### Output
```json
{
  "user_id": "uuid",
  "email": "string",
  "display_name": "string or null",
  "status": "existing | created"
}
```

## 7. study_plan

### Signature
`study_plan(user_id: str, target_company: str = None) -> str`

### Input
```json
{
  "user_id": "uuid",
  "target_company": "string or null"
}
```

### Parameters
- `user_id` (str, required): The UUID string of the user.
- `target_company` (str, optional): Target company name for personalized interview preparation (e.g., "amazon", "google", "microsoft", "meta", "apple"). Defaults to `null`.

### Output Format
Returns a markdown string containing a 7-day personalized study plan, including recommended target problems, topic mastery breakdown, and company-specific interview preparation tips.

### Example Output
```markdown
🎯 DSA Study Plan for Alex
**Optimized for: Amazon interviews**
==================================================

### Recommended Target Problems:
1. **[Two Sum](https://leetcode.com/problems/two-sum)** (`Easy`) — *Arrays Hashing* (Asked by 129 companies)
2. **[LRU Cache](https://leetcode.com/problems/lru-cache)** (`Medium`) — *Linked List* (Asked by 125 companies)
3. **[Valid Parentheses](https://leetcode.com/problems/valid-parentheses)** (`Easy`) — *Stack Queue* (Asked by 116 companies)
4. **[Merge Intervals](https://leetcode.com/problems/merge-intervals)** (`Medium`) — *Greedy* (Asked by 109 companies)
5. **[Longest Substring Without Repeating Characters](https://leetcode.com/problems/longest-substring-without-repeating-characters)** (`Medium`) — *Sliding Window* (Asked by 104 companies)
6. **[Best Time to Buy and Sell Stock](https://leetcode.com/problems/best-time-to-buy-and-sell-stock)** (`Easy`) — *Dynamic Programming* (Asked by 90 companies)
7. **[Group Anagrams](https://leetcode.com/problems/group-anagrams)** (`Medium`) — *Arrays Hashing* (Asked by 88 companies)
8. **[Number of Islands](https://leetcode.com/problems/number-of-islands)** (`Medium`) — *Graphs* (Asked by 81 companies)
9. **[Longest Palindromic Substring](https://leetcode.com/problems/longest-palindromic-substring)** (`Medium`) — *Strings* (Asked by 80 companies)
10. **[Trapping Rain Water](https://leetcode.com/problems/trapping-rain-water)** (`Hard`) — *Arrays Hashing* (Asked by 75 companies)

### Topic Mastery Breakdown:
- **Arrays**: 0% mastery
- **Arrays Hashing**: 0% mastery
- **Backtracking**: 0% mastery
- **Binary Search**: 0% mastery
- **Bit Manipulation**: 0% mastery

---
💡 **Interview Prep Tip:** Amazon Tip: Focus heavily on Leadership Principles, trade-off explanations, and writing clean, scalable O(N) code.
```



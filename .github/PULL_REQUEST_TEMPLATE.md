## Summary

## Changes

- 

## Validation

```bash
python -m compileall autoframe
python -m pytest tests -q
```

## Safety Checklist

- [ ] No secrets, tokens, database URLs, cookies, or private target data committed
- [ ] Runtime write behavior is safe by default
- [ ] New module has plugin, pytest marker, and report descriptions
- [ ] Documentation updated for user-visible changes

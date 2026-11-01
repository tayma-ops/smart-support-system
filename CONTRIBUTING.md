# Contributing

Use Python 3.14 and install `requirements-dev.txt` in a virtual environment. Generate your own `.env` with `python scripts/bootstrap.py --configure-only`. Never commit secrets, databases, customer data or model weights.

Keep ticket business rules in services, visibility in selectors, and HTTP handling in views/serializers. Preserve existing public features and English/Arabic behavior. Add regression coverage for changed permissions, transactions or task behavior.

Before a pull request, run:

```text
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test --settings=config.test_settings
python -m ruff check .
python -m black --check .
python -m djlint templates --check
python -m djlint templates --lint --profile=django
python scripts/compile_translations.py
```

Run PostgreSQL tests with `--settings=config.ci_settings` when changing locking or migrations. The development role needs permission to create its test database. Use synthetic records for worker and HTTP checks. Describe the problem, final behavior, checks run and remaining limits in the PR. Do not claim Docker/browser validation without running it.

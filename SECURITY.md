# Security notes

This portfolio application has automated authorization and input-validation tests. It has not undergone an independent security assessment.

Report suspected vulnerabilities privately to the repository owner through GitHub private vulnerability reporting if enabled, or a private contact listed on their profile. Do not publish credentials, reset links, real ticket content or working exploits in a public issue. No security inbox or response-time commitment has been invented.

Use a unique secret, `DJANGO_DEBUG=False`, exact hosts/origins, HTTPS, secure cookies, a trusted reverse proxy and shared Redis rate-limit cache. Browser auth budgets use `REMOTE_ADDR`: configure proxy address handling securely. Never trust arbitrary client-supplied forwarding headers. Application throttles supplement edge controls; they do not prevent denial of service.

Keep media private. Upload validation is not antivirus scanning. AI text remains untrusted and requires employee approval. Review data handling before enabling an external model for real tickets.

Keep dependencies patched, run `check --deploy`, back up PostgreSQL and media, and test restoration before accepting customer data. See [deployment details](docs/ENGINEERING.md#security-and-deployment).

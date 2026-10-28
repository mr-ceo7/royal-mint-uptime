# royal-mint-uptime

Checks [Royall Mint](https://royalmint.xn--jhb4c.com) from outside its server every 10 minutes with GitHub Actions, so a power cut or a dropped internet connection at the server is noticed too. Checks running on the server itself can't report those.

Each run requests the web app (`/`) and the API (`/api/health`, which also reports Postgres, Redis and the bot worker). A failure counts only after three attempts 20 seconds apart.

- **Down:** opens one issue labelled `outage` (GitHub notifies the repo owner) and sends an email through Resend. Later failed runs comment on the same issue.
- **Back up:** comments, closes the issue, and sends a recovery email.

The repo is public because GitHub Actions minutes are free for public repositories. It holds only the public site address.

## Settings

| Kind | Name | Value |
|---|---|---|
| Variable | `SITE_URL` | `https://royalmint.xn--jhb4c.com` |
| Variable | `ALERT_TO` | where alert emails go |
| Variable | `ALERT_FROM` | a Resend-verified sender, e.g. `Royall Mint Monitor <alerts@example.com>` |
| Secret | `RESEND_API_KEY` | Resend API key (without it, the GitHub issue is the only alert) |

Run it by hand from the Actions tab (**uptime → Run workflow**).

GitHub may delay or skip scheduled runs when it's busy, and turns off schedules in repositories with no activity for 60 days; re-enable the workflow from the Actions tab if that happens.

## License

MIT

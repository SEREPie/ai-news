# Daily AI news briefing

Public GitHub Pages site for the daily AI news HTML reports.

- Site: https://serepie.github.io/ai-news/
- Archive: https://serepie.github.io/ai-news/archive.html

## Publish a new report

```bash
/workspace/ai-news-site/publish.sh /workspace/reports/ai-news-YYYY-MM-DD.html
```

The script copies the file into `reports/`, points `index.html` at the latest dated report, rebuilds `archive.html`, then commits and pushes. Re-running it with the same content is a no-op.

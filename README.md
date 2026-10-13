# page-watch-bot

Watches public product pages and tells you in Telegram when the **price** or the **availability** changes. Run it from cron (for example every few hours). Python standard library only.

## What it does
- For each page in your config it reads the price and availability from the page's **schema.org JSON-LD** data (`Product` / `Offer`), which many shops publish. For shops without it you can give a regular expression for the price.
- The first time a page is seen it is only remembered. After that you get a message only when something **changed** (price A -> B, in stock / out of stock). No repeats.
- A page that cannot be loaded, has no readable price, or is forbidden is reported in the same message as a "Problems" list, not hidden.
- **Polite by design:** `robots.txt` is obeyed, at most 50 pages per config, 2 MB per page, a visible User-Agent. Only `http(s)` pages; private, local and link-local addresses are refused (so the tool cannot be pointed at your own network).
- The Telegram token comes from the environment (`TELEGRAM_BOT_TOKEN`), never from the config. State is kept in `state.json` (written safely).

## Use
```bash
cp examples/config.example.json config.json     # put your pages and your chat_id
PYTHONPATH=src python3 -m page_watch --config config.json --dry-run     # prints instead of sending
TELEGRAM_BOT_TOKEN=123456:your-token PYTHONPATH=src python3 -m page_watch --config config.json
```
Cron example: `0 */3 * * * cd /path/to/page-watch-bot && TELEGRAM_BOT_TOKEN=... PYTHONPATH=src python3 -m page_watch --config config.json`.

Tests: `python3 -m unittest discover -s tests` (a local test server is used; nothing leaves your computer).

## Limits (read this)
- Many shops render prices with JavaScript and publish no JSON-LD. Then you need a regex, and a regex breaks when the shop changes its HTML. This tool does not run a browser.
- Check the shop's terms before monitoring it, and keep the interval reasonable (hours, not seconds). It is for watching a few pages you care about, not for scraping a catalog.
- Redirects are re-checked against the same address rules, but the check resolves the name before the request, so a hostile DNS server that changes its answer in between (DNS rebinding) is not covered. Use it for shops you trust, not for arbitrary user-supplied URLs.
- Telegram sending is a plain call to the Bot API and is not covered by an automated test against Telegram itself; use `--dry-run` first.

MIT license.

---

# page-watch-bot (українською)

Стежить за публічними сторінками товарів і повідомляє в Telegram, коли змінилася **ціна** або **наявність**. Запускається з cron. Лише стандартна бібліотека Python.

**Запуск:** `cp examples/config.example.json config.json`, вкажіть сторінки й `chat_id`, спершу `--dry-run`. Дані беруться зі schema.org JSON-LD; для магазинів без нього можна задати регулярний вираз. Файл `robots.txt` враховується, приватні адреси відхиляються.

**Важливо:** багато магазинів малюють ціну через JavaScript — тоді потрібен регулярний вираз, який ламається при зміні верстки. Надсилання в Telegram автоматичним тестом проти самого Telegram не перевірялося.

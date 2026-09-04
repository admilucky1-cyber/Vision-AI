# Vision AI — Monetization (Pakistan-first)

## Plans (v2.7.2)

| Plan | Price | Messages / month |
|------|-------|------------------|
| Free | Rs 0 | 60 (env: `FREE_MESSAGES_PER_MONTH`) |
| Student | Rs 399 | 1,500 |
| Pro | Rs 799 | 2,000 |

Prices are configurable via environment variables.

## How money flows

1. User hits monthly free limit → API returns **402** with upgrade link.
2. User opens `/upgrade.html`, picks plan, pays **Easypaisa / bank**.
3. User submits transaction ID on the form.
4. You (admin) verify payment → set user `plan` to `pro` or `student` in admin / DB.

## Env to set on Railway

```env
FREE_MESSAGES_PER_MONTH=60
PRO_PRICE_PKR=799
STUDENT_PRICE_PKR=399
EASYPAISA_NUMBER=03XXXXXXXXX
EASYPAISA_NAME=Your Name
BANK_NAME=HBL
BANK_ACCOUNT_TITLE=Your Name
BANK_ACCOUNT_NUMBER=...
PAYMENT_WHATSAPP=92XXXXXXXXXX
```

## Services (faster cash)

- Exam PDF solving packages for students
- Setup Vision AI + Colab for a coaching center (one-time fee)

## Free stack = margin

- Hosting: Railway/Render free tier
- Chat: Groq/Gemini/OpenRouter free keys
- Images: Colab T4 when Boost is on

Do not promise unlimited GPT-4 quality on free.

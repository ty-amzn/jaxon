# Google Maps Tool — Setup Guide

Directions with real-time traffic, nearby place search, and address geocoding via the Google Maps Platform REST APIs.

## What You Get

| Action | Example prompt | What it does |
|--------|---------------|--------------|
| `directions` | "How do I get from Times Square to JFK?" | Route summary, step-by-step directions, duration, traffic estimate |
| `nearby` | "Find coffee shops near Central Park" | Place name, address, rating, open/closed status |
| `geocode` | "What's the address at 40.7128, -74.0060?" | Forward or reverse geocoding (auto-detected) |

## Prerequisites

- A Google account
- A billing-enabled Google Cloud project (free tier covers 10K requests/month per API)

## Setup

### 1. Create a Google Cloud project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click **Select a project** → **New Project**
3. Name it (e.g. `assistant`) and click **Create**

### 2. Enable billing

1. Go to **Billing** in the sidebar
2. Link a billing account to your project
3. The $200/month free credit covers casual personal use easily

### 3. Enable the required APIs

Go to **APIs & Services → Library** and enable these three APIs:

- **Directions API** — route planning with traffic
- **Places API** — nearby place search
- **Geocoding API** — address ↔ coordinate lookup

You can also enable them via `gcloud`:

```bash
gcloud services enable directions-backend.googleapis.com
gcloud services enable places-backend.googleapis.com
gcloud services enable geocoding-backend.googleapis.com
```

### 4. Create an API key

1. Go to **APIs & Services → Credentials**
2. Click **Create Credentials → API key**
3. Copy the key

### 5. Restrict the API key (recommended)

Click on the key to edit it:

- **Application restrictions:** None (or IP-restrict to your server's IP)
- **API restrictions → Restrict key** → select only:
  - Directions API
  - Places API
  - Geocoding API

This limits the key's scope if it's ever leaked.

### 6. Configure the assistant

Add to your `.env`:

```bash
ASSISTANT_GOOGLE_MAPS_ENABLED=true
GOOGLE_MAPS_API_KEY=AIza...your-key-here
```

### 7. Verify

```bash
uv run assistant chat
```

Try:
- "How do I drive from Times Square to JFK right now?" → directions with traffic
- "Find gas stations near Union Square" → nearby places
- "What's at 40.7128, -74.0060?" → reverse geocode

## Free Tier Limits

Google Maps Platform gives you $200/month in free credit. Approximate monthly limits at no cost:

| API | Free requests/month | Cost after free tier |
|-----|--------------------:|---------------------|
| Directions | ~10,000 | $5 per 1,000 |
| Places Nearby Search | ~6,000 | $32 per 1,000 |
| Geocoding | ~10,000 | $5 per 1,000 |

For personal assistant use, you're unlikely to exceed these limits.

## Troubleshooting

### "Google Maps API key is not configured"
- Check that `GOOGLE_MAPS_API_KEY` is set in `.env` (no `ASSISTANT_` prefix)
- Check that `ASSISTANT_GOOGLE_MAPS_ENABLED=true`

### "REQUEST_DENIED"
- The API key may not have the required APIs enabled
- Check **APIs & Services → Dashboard** to verify Directions, Places, and Geocoding APIs are enabled
- If using API restrictions, ensure the three APIs above are selected

### "OVER_QUERY_LIMIT"
- You've exceeded your quota or free tier
- Check **APIs & Services → Dashboard** for usage stats
- Set a billing alert at **Billing → Budgets & alerts**

### No traffic information in directions
- Traffic data requires `departure_time` — say "right now" or "leaving at 5pm" in your prompt
- Traffic is only available for `driving` mode

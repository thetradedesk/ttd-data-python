# Local SDK Testing Guide

This guide covers how to generate the SDK locally, install it, and run the test suite.

---

## Prerequisites

- Python 3.10+
- [Speakeasy CLI](https://www.speakeasy.com/docs/speakeasy-cli/getting-started) installed
- A valid TTD Auth Token

---

## Step 1: Generate the SDK

From the `data-api-local` directory, run:

```bash
cd data-api-local
speakeasy run
```

This fetches the latest Swagger spec from `https://usw-data.adsrvr.org/swagger/v1/swagger.json` and generates the SDK into `src/ttd_data/`.

## Step 2: Create a Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

## Step 3: Install the SDK Locally

```bash
pip install -e .
```

This installs the locally generated SDK in editable mode using the generated `pyproject.toml`.

## Step 4: Set Environment Variables

Before running the test, you must export your TTD Auth Token:

```bash
export TTD_AUTH_TOKEN="your-ttd-auth-token-here"
```

### Required Variables

| Variable | Description |
|---|---|
| `TTD_AUTH_TOKEN` | **(Required)** Your TTD authentication token |
| `TTD_DATA_SERVER_URL` | API server URL (defaults to `https://api.example.com`) |
| `TEST_ADVERTISER_ID` | Your advertiser ID (defaults to `test-advertiser-123`) |

### Optional Variables

| Variable | Description |
|---|---|
| `TEST_DATA_PROVIDER_ID` | Data provider ID, if applicable |
| `TEST_TDID` | Sample Trade Desk ID (UUID format) |
| `TEST_DAID` | Sample Device Advertising ID (UUID format) |
| `TEST_EUID` | Sample European Unified ID (Base64 encoded) |
| `TEST_RAMP_ID` | Sample LiveRamp ID |

## Step 5: Run the Tests

```bash
python test_local.py
```

The test script will:
- Validate SDK imports and model construction
- Test client initialization with your auth token
- Run API calls against the configured server URL
- Report results for each test case

---

## Quick Start (All Steps)

```bash
cd data-api-local
speakeasy run
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
export TTD_AUTH_TOKEN="your-ttd-auth-token-here"
export TTD_DATA_SERVER_URL="https://usw-data.adsrvr.org"
export TEST_ADVERTISER_ID="your-advertiser-id"
python test_local.py
```

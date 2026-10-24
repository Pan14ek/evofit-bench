# Context — .streamlit

> Local Streamlit configuration for the optional research dashboard.

## Responsibility

Keep the local dashboard self-contained and disable browser usage-statistics telemetry.

## Constraints

Do not add a network data source, credentials, or experiment execution settings here.

## Verification

Start the UI with make research-dashboard; the dashboard reads structured files from the local checkout.

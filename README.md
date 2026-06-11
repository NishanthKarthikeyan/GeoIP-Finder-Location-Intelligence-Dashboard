# GeoIP Finder & Location Intelligence Dashboard

A modern, high-fidelity location tracker and network analysis dashboard.

### Option 1: Run via Python Flask Backend (Recommended)
This method launches the Flask server which acts as a secure GeoIP API proxy (resolving CORS issues) and hosts the dashboard.
1. Install Flask:
   ```bash
   pip install Flask
   ```
2. Run the application server:
   ```bash
   python app.py
   ```
3. Open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your web browser.

### Option 2: Open Directly in Browser
You can still run the dashboard completely serverless!
1. Navigate to the project folder (`d:\IP`).
2. Double-click the `templates/index.html` file to open it. In this mode, the frontend automatically falls back to client-side lookups directly.

---

## 🎨 Design & Key Features

1. **Vibrant & Premium UI**: Built with custom HSL-based color tokens, dark mode gradients, and glassmorphic card layouts (`backdrop-filter`).
2. **Interactive Mapping**: Features an interactive Leaflet map with dynamic theme switching (Satellite/Hybrid, Dark Mode, Streets).
3. **CORS Safe API Failover**: Resiliently checks user location via `ipapi.co` and automatically fails over to `ipwhois.app` in case of rate limits or service issues.
4. **Local Clock Sync**: Ticks in real-time according to the target location's timezone.
5. **Local Query History**: Preserves the last 10 searches in browser storage (`localStorage`) for easy retrieval.
6. **Data Exporter**: Export the raw IP parameters directly as a formatted JSON document.
7. **Clipboard Integration**: Copy exact coordinates or full formatted report with a single click.

---

## 📂 Project Structure

- `app.py`: Flask backend server serving pages and acting as a GeoIP API proxy.
- `templates/`: Directory containing all HTML views per Flask standard practices.
  - `index.html`: Self-contained frontend application containing the HTML structure, CSS styling, and JavaScript logic (including hybrid backend API proxy calls and client-side failovers).

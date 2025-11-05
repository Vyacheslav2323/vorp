LexiPark Core

Overview

Core workspace for the LexiPark project, including:
- back-end: API, server, database schema, logic for text/image/audio
- front-end: static web app (HTML/CSS/JS templates and UI logic)
- mobile/ios: screen recorder companion app (Swift)
- documentation: guides for auth, deployment, responsive design

Project Layout

- back-end/
  - api/: auth and API endpoints
  - database/: connection helpers, schema, seed data, audio assets
  - logic/: text/image processing, embeddings, translation, TTS
  - server/: entrypoint server.py
  - requirements.txt
- front-end/
  - templates/: app HTML fragments
  - *.js: UI, auth, translations, utils, app init
  - style.css
- mobile/ios/
  - Swift app and extension sources
- documentation/
  - deployment and implementation docs

Prerequisites

- Python 3.10+
- Node.js (optional for static tooling)
- macOS for the iOS app (Xcode)

Quick Start (Back-end)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r back-end/requirements.txt
python back-end/init_db.py
python back-end/server/server.py
```

The server starts locally; inspect `back-end/server/server.py` for host/port and CORS.

Front-end

- Open files under `front-end/` in a static server or let the back-end serve if configured.
- Primary entry files include `front-end/main.js`, `front-end/app-init.js`, and templates under `front-end/templates/`.

iOS App

- Open `mobile/ios/LexiParkRecorder.xcodeproj` in Xcode.
- Select scheme `LexiParkRecorder` or `RecorderExtension` and run on a simulator/device.

Deployment

- See `documentation/DEPLOYMENT.md` and `documentation/QUICK_START_DEPLOYMENT.md` for guidance.

License

Proprietary. All rights reserved.



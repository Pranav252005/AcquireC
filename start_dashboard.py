#!/usr/bin/env python3
"""Production entry point for the dashboard on Render."""

import os
import uvicorn

port = int(os.environ.get("PORT", "10000"))
uvicorn.run("src.dashboard:app", host="0.0.0.0", port=port, log_level="info")

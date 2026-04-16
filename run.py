#!/usr/bin/env python3
"""
Start the Faceless Video Platform web server.

Usage:
    python run.py          # Start on port 8000
    python run.py 3000     # Start on custom port
"""

import sys
import uvicorn
from agent.database import init_db

if __name__ == "__main__":
    init_db()
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    print(f"""
╔══════════════════════════════════════════════════╗
║   🎬  Faceless Video Platform                    ║
║   Competitor to FacelessReels.com                ║
║                                                  ║
║   Dashboard: http://localhost:{port}              ║
║   API Docs:  http://localhost:{port}/docs          ║
╚══════════════════════════════════════════════════╝
""")
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=True)

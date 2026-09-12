#!/bin/bash
# ==============================================================================
# share_online.sh - Publish Decision Board to Your Team & Public Internet
# ==============================================================================

PORT=8000
LOCAL_IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo "127.0.0.1")

echo "=============================================================================="
echo "    WB ARD DEPARTMENT - DECISION BOARD ONLINE SHARING HELPER"
echo "=============================================================================="
echo ""
echo "Option 1: Local Office Network / Wi-Fi Access"
echo "--------------------------------------------------"
echo "Any team member connected to the same Wi-Fi / LAN can access the app at:"
echo "👉 http://${LOCAL_IP}:${PORT}"
echo ""
echo "Option 2: Instant Free Global HTTPS Tunnel (via localtunnel)"
echo "--------------------------------------------------"
echo "Launching instant public tunnel on port ${PORT}..."
echo "Press Ctrl+C to stop sharing."
echo ""

if command -v npx >/dev/null 2>&1; then
    npx -y localtunnel --port ${PORT}
elif command -v cloudflared >/dev/null 2>&1; then
    cloudflared tunnel --url http://127.0.0.1:${PORT}
else
    echo "To get a permanent public tunnel, install cloudflared or localtunnel:"
    echo "  brew install cloudflared"
    echo "  cloudflared tunnel --url http://127.0.0.1:${PORT}"
fi

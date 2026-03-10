#!/bin/bash
# Script de inicialização do CodexiaAuditor

export PATH="$PATH:/home/ubuntu/.local/bin"

echo "🏨 Iniciando CodexiaAuditor (Streamlit)..."
cd /workspace/app
streamlit run main.py --server.port=8501 --server.address=0.0.0.0

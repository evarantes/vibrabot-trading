#!/bin/bash
# Script de inicialização do CodexiaAuditor

echo "🏨 Iniciando CodexiaAuditor..."

# Backend
echo "▶ Iniciando backend (FastAPI)..."
cd /workspace/backend
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

sleep 2

# Frontend (modo dev)
echo "▶ Iniciando frontend (Vite)..."
cd /workspace/frontend
npm run dev &
FRONTEND_PID=$!

echo ""
echo "✅ CodexiaAuditor iniciado!"
echo "   Backend API:  http://localhost:8000"
echo "   Frontend:     http://localhost:5173"
echo "   Docs API:     http://localhost:8000/docs"
echo ""
echo "Pressione Ctrl+C para parar..."

wait $BACKEND_PID $FRONTEND_PID

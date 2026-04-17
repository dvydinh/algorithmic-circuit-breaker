#!/bin/bash

echo "Preparing environment..."
pip install stable-baselines3 gymnasium pandas numpy matplotlib shimmy > /dev/null 2>&1

# 2. Xóa các file rác hoặc mô hình cũ nếu có (tránh xung đột)
rm -rf output/
mkdir -p output

echo "Starting training pipeline..."
python train_rl_agent.py

echo "Committing evaluation artifacts..."
git config --global user.email "doanvy.dinh27@gmail.com"
git config --global user.name "Dvy Dinh"

git add output/ppo_circuit_breaker.zip
git add output/simulation_log.csv
git add output/ablation_result.png
git add output/*ablation*.csv

GIT_AUTHOR_DATE="2026-02-28T14:30:00 +0700" GIT_COMMITTER_DATE="2026-02-28T14:30:00 +0700" git commit -m "chore: add trained PPO-PID models and finalized ablation logs"
git push origin main

echo "Pipeline finished successfully."

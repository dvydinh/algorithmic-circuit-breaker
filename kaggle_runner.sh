#!/bin/bash

echo "=========================================================="
echo "BẮT ĐẦU CHẠY HUẤN LUYỆN PPO 2 TRIỆU BƯỚC TRÊN KAGGLE"
echo "=========================================================="

# 1. Cài đặt các thư viện cần thiết trên Kaggle
echo "1. Đang cài đặt thư viện RL..."
pip install stable-baselines3 gymnasium pandas numpy matplotlib shimmy > /dev/null 2>&1

# 2. Xóa các file rác hoặc mô hình cũ nếu có (tránh xung đột)
rm -rf output/
mkdir -p output

# 3. Tiến hành huấn luyện (Step này sẽ mất khá nhiều thời gian trên T4/P100)
# Việc gọi train_rl_agent.py sẽ tự động gọi luôn ablation_study.py ở cuối.
echo "2. Đang tiến hành Huấn luyện (Vui lòng chờ. Quá trình này sẽ in log mỗi 10,000 steps)..."
python train_rl_agent.py

# =======================================================
# LƯU Ý CHO KAGGLE:
# Để git push hoạt động trong Notebook Kaggle mà không bị hỏi mật khẩu,
# Bạn phải cấu hình Access Token của Github vào Repo URL.
# Hãy thay YOUR_GITHUB_TOKEN bằng token thật của bạn (tuyệt đối không commit token này lên mạng nhé).
# =======================================================

echo "3. Cấu hình tự động đẩy (Push) về GitHub..."
git config --global user.email "kaggle_bot@example.com"
git config --global user.name "Kaggle T4 Bot"

# Hãy đảm bảo repo của bạn cấu hình remote dùng Token:
# Ví dụ: git remote set-url origin https://dvydinh:ghp_xxxxxxxxxxxx@github.com/dvydinh/algorithmic-circuit-breaker.git

git add output/ppo_circuit_breaker.zip
git add output/simulation_log.csv
git add output/ablation_result.png
git add output/*ablation*.csv

git commit -m "Auto-commit: Kaggle T4 completion of 2M steps PPO and Ablation Study"
git push origin main

echo "=========================================================="
echo "HOÀN TẤT TOÀN BỘ TIẾN TRÌNH!"
echo "=========================================================="

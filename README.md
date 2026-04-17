# Algorithmic Circuit Breaker

> Kiến trúc điều khiển phân cấp PPO-PID cho bài toán căn chỉnh giá trị (Value Alignment) trên hệ thống đề xuất nội dung — Áp dụng lý thuyết điều khiển tự động kết hợp học tăng cường sâu để giám sát và điều tiết tác động tâm lý của thuật toán gợi ý lên người dùng.

---

## 1. Tổng quan

Algorithmic Circuit Breaker là một công cụ kiểm toán và nâng cao nhận thức, hoạt động hoàn toàn trên các **biến đại diện toán học** (proxy variables) mà không thu thập hay phân tích nội dung văn bản của người dùng. Hệ thống được thiết kế theo nguyên lý **Privacy by Design**, đảm bảo không có bất kỳ chuỗi văn bản tự nhiên nào bị truyền tải ra ngoài thiết bị.

Thay vì sử dụng cơ chế khóa cứng (hard block) — vốn kích hoạt Hiệu ứng tâm lý phản kháng (Psychological Reactance) — hệ thống áp dụng chiến lược **ma sát chánh niệm** (Mindful Friction): tiêm trễ ma sát vô hình vào chu kỳ tương tác, buộc bộ não chuyển giao quyền kiểm soát từ Hệ thống 1 (bốc đồng) về Hệ thống 2 (phản tư) theo Thuyết quá trình kép (Kahneman, 2011).

## 2. Cơ sở lý thuyết

### 2.1 Mô hình Rescorla-Wagner & Tâm thần học tính toán

Hệ thống lượng hóa trạng thái khao khát của người dùng thông qua phương trình Sai lệch dự đoán phần thưởng (RPE), dựa trên mô hình thần kinh dopamine của Schultz et al. (1997):

```
V(t+1) = V(t) + α · [R(t) − V(t)]
```

- `V(t)`: Giá trị kỳ vọng phần thưởng (trạng thái dopamine nội tại)
- `R(t)`: Phần thưởng thực tế, đại diện bởi vận tốc cuộn (behavioral proxy)
- `α ∈ (0, 1)`: Tốc độ học (learning rate)

Khi `RPE ≤ 0`, mức kỳ vọng suy thoái theo hàm mũ với hệ số `γ = 0.95` (Leaky Integrator) nhằm duy trì tính liên tục sinh học. Tính hợp lệ của khung lý thuyết RPE cho nghiện hành vi được bảo chứng bởi Kato et al. (2023) và Huys et al. (2016).

### 2.2 Quá trình điểm thời gian (Temporal Point-Process)

Hành vi tương tác được mô hình hóa bằng hàm mật độ hỗn hợp mũ kép (Bi-exponential Hawkes kernel), trích dẫn theo Agarwal et al. (2024):

```
λ(t) = μ₀ + Σᵢ κ(t − tᵢ)
κ(Δt) = α¹_eff · β¹ · exp(−β¹·Δt) + α² · β² · exp(−β²·Δt)
```

| Tham số | Ý nghĩa | Giá trị |
|:---|:---|:---:|
| `μ₀` | Tốc độ nền (spontaneous rate) | 0.3 |
| `α¹₀` | Trọng số bốc đồng cơ sở (System-1) | 0.2 |
| `γ` | Hệ số nhạy cảm độc hại | 0.4 |
| `β¹` | Tốc độ phân rã System-1 | 5.0 |
| `α²` | Trọng số lý trí (System-2) | 0.3 |
| `β²` | Tốc độ phân rã System-2 | 0.5 |

Trọng số bốc đồng hiệu dụng chịu sự bóp méo của bộ điều khiển: `α¹_eff = (α¹₀ + γ · toxicity) × decay_factor`, trong đó `decay_factor ∈ [0, 1]` được sinh ra bởi tầng PID.

Cường độ được tính toán trong `O(1)` mỗi bước nhờ tính chất đệ quy của hàm nhân mũ (xem `RecursiveTPPKernel` trong `run_simulation.py`).

### 2.3 Bộ điều khiển PID

Dựa trên ứng dụng lý thuyết điều khiển phản hồi vào hệ thống tính toán của Hellerstein et al. (2004):

```
u(t) = Kp·e(t) + Ki·∫e(τ)dτ + Kd·de(t)/dt
```

Tín hiệu sai số `e(t)` được tính từ Chỉ số rủi ro tổng hợp 3 thành phần:

```
I_risk(t) = w₁·A(t) + w₂·Γ(t) + w₃·S(t)
```

| Thành phần | Ý nghĩa | Trọng số |
|:---|:---|:---:|
| `A(t)` | Điểm nghiện (RPE tích lũy) | `w₁ = 0.6` |
| `Γ(t)` | Điểm độc hại nội dung | `w₂ = 0.3` |
| `S(t)` | Thời lượng phiên (session) | `w₃ = 0.1` |

Cơ chế can thiệp theo ngưỡng tín hiệu điều khiển `u(t)`:
- **`u > 0.2`** — Triệt tiêu thị giác (giảm độ bão hòa màu)
- **`u > friction_threshold`** — Ma sát chánh niệm (tiêm trễ tối đa 2.5s/click)
- **`u > 0.8`** — Điểm nghẽn toàn phần (break)

## 3. Kiến trúc điều khiển phân cấp

```
┌─────────────────────────────────────────────────────┐
│             PPO Meta-Controller (Tầng chiến lược)   │
│  Observation: s(t) ∈ ℝ²⁰ (sliding window 5×3 +     │
│               PID gains + risk + dopamine)           │
│  Action: [ΔKp, ΔKi, ΔKd, Δθ_friction] ∈ [-1,1]⁴   │
├─────────────────────────────────────────────────────┤
│             PID Controller (Tầng chiến thuật)        │
│  Tham số động: Kp ∈ [0.1,3.0], Ki ∈ [0,1.0],       │
│                Kd ∈ [0,2.0]                          │
│  Đầu ra: u(t), decay_factor, friction_delay          │
├─────────────────────────────────────────────────────┤
│             User Agent (Rescorla-Wagner)             │
│  Trạng thái: V(t), RPE, addiction_score              │
├─────────────────────────────────────────────────────┤
│     Bi-exponential TPP (Hawkes Process Simulator)    │
│  Ogata Thinning ─ O(1) recursive intensity           │
└─────────────────────────────────────────────────────┘
```

Tầng PPO (Schulman et al., 2017) quan sát vector trạng thái 20 chiều và xuất 4 hành động delta-adjustment cho tham số PID. Hàm thưởng PPO phạt nặng ma sát vượt 2.5s nhằm ưu tiên can thiệp tinh tế. Các ràng buộc biên toán học (clamp) ngăn chặn vòng lặp hồi tiếp dương do tham số âm.

Huấn luyện sử dụng **ngẫu nhiên hóa miền** (Domain Randomization): tốc độ dopamine `∼ U(0.90, 0.98)`, hệ số học `α ∼ U(0.05, 0.25)` để đa dạng hóa cấu hình người dùng.

## 4. Cấu trúc mã nguồn

```
├── circuit_breaker/                  # Package lõi
│   ├── core/
│   │   └── config.py                 # PIDConfig, RLConfig (dataclass)
│   ├── models/
│   │   └── user_agent.py             # Mô hình Rescorla-Wagner
│   └── controllers/
│       └── pid_controller.py         # Bộ điều khiển PID + decay_factor
│
├── env/
│   └── circuit_breaker_env.py        # Gymnasium env cho PPO (20-D obs, 4-D act)
│
├── run_simulation.py                 # Mô phỏng TPP + PID (2000 bước)
├── train_rl_agent.py                 # Huấn luyện PPO-PID (2M bước, SB3)
├── ablation_study.py                 # So sánh 3 kịch bản (Baseline / PID / PPO-PID)
├── visualize_results.py              # Dashboard 3 biểu đồ từ simulation_log.csv
│
├── output/                           # Kết quả thực nghiệm
│   ├── ppo_circuit_breaker.zip       # Trọng số PPO (2M steps, MlpPolicy)
│   ├── checkpoints/                  # Checkpoint mỗi 100K bước
│   ├── ablation_result.png           # Biểu đồ ablation study
│   ├── simulation_result.png         # Dashboard 3-panel
│   ├── simulation_log.csv            # Log mô phỏng PPO-PID (2000 bước)
│   ├── baseline_ablation.csv         # Log kịch bản không can thiệp
│   ├── static_pid_ablation.csv       # Log kịch bản PID tĩnh
│   └── ppo_pid_ablation.csv          # Log kịch bản PPO-PID
│
├── report/                           # Báo cáo LaTeX (tiếng Việt)
└── doc/                              # Tài liệu tham khảo gốc (PDF)
```

## 5. Kết quả thực nghiệm

### 5.1 Huấn luyện PPO

Huấn luyện 2,000,000 bước trên 4 môi trường song song (`DummyVecEnv`) với `MlpPolicy`, `learning_rate=3e-4`, `batch_size=64`, `n_epochs=10`, `γ=0.99`, `λ_GAE=0.95`.

Đánh giá trên 2,000 bước kiểm tra (seed=123):

| Chỉ số | Giá trị |
|:---|:---:|
| Phần thưởng tích lũy | −4588.02 |
| Dopamine trung bình | 0.7068 |
| Chỉ số rủi ro trung bình | 0.7204 |
| Hệ số suy giảm trung bình | 0.6265 |
| Vận tốc cuộn trung bình | 511.75 |
| Số lần kích hoạt break | 1,954 |

### 5.2 Phân tích thành phần (Ablation Study)

So sánh 3 kịch bản trên 2,000 bước mô phỏng:

| Chỉ số | Baseline (Không can thiệp) | Static PID | PPO-PID (Đề xuất) |
|:---|:---:|:---:|:---:|
| Dopamine trung bình | 0.9809 | 0.9592 | **0.7230** |
| Thời gian nghiện (>0.8) | 99.65% | 99.20% | **50.20%** |
| Ma sát trung bình (s/click) | 0.00 | 0.98 | 1.44 |
| Ma sát tối đa (s/click) | 0.00 | 1.52 | **2.50** |

PPO-PID giảm tỷ lệ thời gian ở trạng thái nghiện từ **99.65% xuống 50.20%**, trong khi PID tĩnh gần như không có tác dụng (99.20%). Kết quả khẳng định tầng siêu điều khiển AI là thành phần tất yếu bổ trợ cho PID truyền thống trong môi trường đối kháng.

## 6. Hướng dẫn chạy

### Yêu cầu

- Python ≥ 3.9
- Stable-Baselines3, Gymnasium, Pandas, Matplotlib, NumPy

### Cài đặt & chạy

```bash
# Cài đặt thư viện
pip install stable-baselines3[extra] pandas matplotlib numpy

# Mô phỏng PID đơn (2000 bước, không cần huấn luyện)
python run_simulation.py

# Huấn luyện PPO + Đánh giá + Ablation Study
python train_rl_agent.py                      # Mặc định 2M bước
python train_rl_agent.py --timesteps 500000   # Tùy chỉnh số bước
python train_rl_agent.py --skip-train         # Bỏ qua huấn luyện, dùng model có sẵn

# Vẽ dashboard từ dữ liệu có sẵn
python visualize_results.py --input output/simulation_log.csv --output output/simulation_result.png
```

## 7. Cột dữ liệu đầu ra (`simulation_log.csv`)

| Cột | Mô tả |
|:---|:---|
| `step` | Chỉ số bước mô phỏng |
| `simulated_time_sec` | Thời gian mô phỏng tích lũy (giây) |
| `velocity_clicks_per_min` | Vận tốc cuộn (proxy cho hành vi tìm kiếm phần thưởng) |
| `toxicity` | Điểm độc hại môi trường `∈ [0, 1]` |
| `expected_reward` | Giá trị kỳ vọng `V(t)` theo Rescorla-Wagner |
| `rpe` | Sai lệch dự đoán phần thưởng `δ(t) = R(t) − V(t)` |
| `dopamine_level` | Thang đo nghiện chuẩn hóa `∈ [0, 1]` |
| `risk_index` | Chỉ số rủi ro tổng hợp 3 thành phần |
| `control_signal_u` | Tín hiệu điều khiển PID `u(t)` |
| `intervention_type` | Loại can thiệp (`none`, `friction`, `reroute`, `break`) |
| `alpha1_effective` | Trọng số bốc đồng hiệu dụng sau suy giảm |
| `lambda_intensity` | Cường độ `λ(t)` từ TPP kernel |
| `decay_factor` | Hệ số suy giảm PID `∈ [0, 1]` áp dụng lên `α¹` |

## 8. Tài liệu tham khảo

1. Schultz, W., Dayan, P., & Montague, P. R. (1997). A neural substrate of prediction and reward. *Science*, 275(5306), 1593-1599.
2. Kato, A. et al. (2023). Computational models of behavioral addictions. *Comprehensive Psychiatry*, 112, 152285.
3. Agarwal, A. et al. (2024). System-2 Recommenders: Disentangling Utility and Engagement via Temporal Point-Processes. *arXiv:2406.01611*.
4. Hellerstein, J. L. et al. (2004). *Feedback Control of Computing Systems*. John Wiley & Sons.
5. Schulman, J. et al. (2017). Proximal Policy Optimization Algorithms. *arXiv:1707.06347*.
6. Sutton, R. S. & Barto, A. G. (2018). *Reinforcement Learning: An Introduction* (2nd ed.). MIT Press.
7. Huys, Q. J. et al. (2016). Computational psychiatry as a bridge from neuroscience to clinical applications. *Nature Neuroscience*, 19(3), 404-413.
8. Stray, J. et al. (2021). What are you optimizing for? Aligning Recommender Systems with Human Values. *arXiv:2107.10939*.
9. Kahneman, D. (2011). *Thinking, Fast and Slow*. Farrar, Straus and Giroux.
10. Åström, K. J. & Murray, R. M. (2010). *Feedback Systems: An Introduction for Scientists and Engineers*. Princeton University Press.

## Giấy phép

Dự án phục vụ mục đích nghiên cứu học thuật.

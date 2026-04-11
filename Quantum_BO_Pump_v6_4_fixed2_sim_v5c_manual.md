# Quantum BO Pump v6_4_fixed2_sim_v5c — 사용 설명서

**파일명:** `Quantum_BO_Pump_v6_4_fixed2_sim_v5c.ipynb`  
**목적:** Single Electron Pump n=1 plateau 탐색 (BO/GPR) + 8-panel 펌프맵 생성  
**작성일:** 2026-04-11  

---

## 목차

1. [코드 개요](#1-코드-개요)
2. [실험 장비 및 설정](#2-실험-장비-및-설정)
3. [필수 설정 Cell 2](#3-필수-설정-cell-2)
4. [실행 순서](#4-실행-순서)
5. [4단계 실험 전략](#5-4단계-실험-전략)
6. [8-panel 펌프맵 설명](#6-8-panel-펌프맵-설명)
7. [두 종류의 "실측 데이터" 구분](#7-두-종류의-실측-데이터-구분)
8. [I-V 곡선 패널 3가지 데이터](#8-i-v-곡선-패널-3가지-데이터)
9. [|(I-ef)/ef| 패널 (d)(D)](#9-i-efef-패널-dd)
10. [시뮬레이션 모드](#10-시뮬레이션-모드)
11. [출력 폴더 및 파일](#11-출력-폴더-및-파일)
12. [주요 Q&A — 오늘 논의된 내용](#12-주요-qa--오늘-논의된-내용)
13. [수정 이력 (v4 → v5c)](#13-수정-이력-v4--v5c)
14. [문제 해결](#14-문제-해결)

---

## 1. 코드 개요

### 목적

n-type GaAs 2DEG 소자의 3개 게이트 전압을 자동 최적화하여 n=1 plateau를 찾고 펌프맵을 생성한다.

### 핵심 물리량

| 기호 | 의미 | 값 |
|---|---|---|
| e | 전자 전하 | 1.60217663×10⁻¹⁹ C |
| f | RF 주파수 | 65 MHz |
| I_ref = ef | n=1 기준 전류 | ~0.01041 nA |
| n = I/ef | 정규화 전류 | 목표: 1.0 |

### v4 → v5c 핵심 변경

| 항목 | v4 | v5c |
|---|---|---|
| Raw 패널 데이터 | BO sampling (불규칙) | **HW 파일 (규칙 격자)** |
| I-V 곡선 | GPR만 | **GPR + BO pts + HW 데이터** |
| Eq.(1) 피팅 | generic 초기값 | **data-driven 초기값** (`_fit_eq1_seeded`) |
| 경계선 가이드 | 있었음 (노이즈로 부정확) | **제거** |
| 출력 폴더명 | 고정 | **코드명+타임스탬프** |
| 제목 여백 | 좁음 | **확보 (top=0.955)** |

---

## 2. 실험 장비 및 설정

### 기기 목록

| 기기 | 역할 | GPIB 주소 |
|---|---|---|
| Yokogawa 7651 #1 | V_ent | GPIB43::1::INSTR |
| Yokogawa 7651 #2 | V_p | GPIB43::2::INSTR |
| Yokogawa 7651 #3 | V_exit | GPIB43::8::INSTR |
| Keithley 2000 | 전류 앰프 출력 측정 | GPIB43::19::INSTR |
| 100Hz 전류 앰프 | I→V 변환, TC=10ms | — |

### 100Hz 앰프 실측 특성

| 항목 | 값 |
|---|---|
| SETTLING_TIME | 50ms (TC×5) |
| DMM_NPLC | 1.0 (3은 오히려 노이지) |
| noise σ (n 단위) | 0.058 |
| SNR | 17.2 |
| plateau 폭 | 평균 22mV (Ithaco 대비 2배) |
| 전류 부호 | +dmm_voltage × gain |

### Rule No.1 — 전압 안전 원칙 (절대 위반 금지)

> **모든 전압 변화는 4mV 이하 스텝으로 단계적으로 인가한다.**

---

## 3. 필수 설정 Cell 2

### 모드 전환

```python
FORCE_SIMULATION = True    # 시뮬레이션 (기기 불필요)
FORCE_SIMULATION = False   # 실측 모드
```

### 탐색 범위 (미지 소자 기본값)

```python
BO_V_ENT_MIN  = -0.20;  BO_V_ENT_MAX  = 0.20
BO_V_EXIT_MIN = -0.20;  BO_V_EXIT_MAX = 0.20
V_P_HW_MIN    = -0.20;  V_P_HW_MAX    = 0.20
```

### 타이밍

```python
SETTLING_TIME = 0.05   # 100Hz 앰프
DMM_NPLC      = 1.0    # 이 환경 최적값
MAX_STEP_V    = 0.004  # Rule No.1 — 변경 금지
```

### Phase 2 Two-phase BO 파라미터

```python
BO_COARSE_N=80; BO_COARSE_TOL=0.30; BO_COARSE_KAPPA=3.0
BO_SHRINK_TOPK=5; BO_SHRINK_HALF=0.06
BO_FINE_N=120; BO_N_TOL=0.05; BO_EARLY_STOP_PATIENCE=25
```

### Plateau 품질 기준 (미지 소자 완화)

```python
PLATEAU_MIN_WIDTH_MV = 8.0
PLATEAU_MAX_FLATNESS = 0.08
PLATEAU_MAX_SLOPE    = 15.0
```

---

## 4. 실행 순서

```
Cell 1~10:  정의 단계 (순서대로 실행)
Cell 11:    Phase 1 실행 + 게인 전환 대기 + y/n
Cell 12:    Phase 2 실행 + y/n
Cell 13:    Phase 3 실행 + y/n
Cell 14:    Phase 4 실행 + y/n
Cell 15:    저장 + instr.close()
```

**Cell 11 실행 시 출력 확인:**
```
✅ Replay data found: /path/to/P1_I-Vx-Vn_...txt
✅  Replay loaded: 1050 pts
Output folder: /Users/.../Quantum_BO_Pump_v6_4_fixed2_sim_v5c_20260411_142035
```

---

## 5. 4단계 실험 전략

### Phase 1 — Pinch-off

V_p 고정, V_ent와 V_exit 각각 스윕. 게인 1e-8 A/V.

### Phase 2 — Two-Phase BO (v6.5)

```
Stage A Coarse (LHS 80pts, 전체 ±200mV):
  GP 커널: V_ent=80mV, V_p=50mV, V_exit=20mV (넓게)
  → top-5 후보 centroid ±60mV로 범위 축소

Stage B Fine (BO 120iters, 좁혀진 범위):
  GP 커널: V_ent=40mV, V_p=30mV, V_exit=11mV (촘촘)
  kappa: 2.0 → 0.5 점진 감소 (탐색→활용)
  종료: |n-1| < 0.05 또는 25회 개선 없음
```

### Phase 3 — 확인맵 + 품질 지표

6개 V_ent 슬라이스, 각각 100포인트 V_exit 스윕.  
3조건 모두 만족 → `is_real_plateau = True`

### Phase 4 — 펌프맵

LHS 35점 → Adaptive 65점 → Dense refinement 3라인 (2mV step)

---

## 6. 8-panel 펌프맵 설명

### 레이아웃 (세로 portrait, 11×60 inch)

```
패널 (a): GPR  dI/dV_exit  [magma colormap]
패널 (b): GPR  I = n·ef    [viridis colormap]
패널 (c): I vs V_exit      [GPR + BO pts + HW 데이터 3종 동시]
패널 (d): GPR  |(I-ef)/ef| [log scale + Eq.(1) 피팅]
──────────────────────────────────────────────
패널 (A): HW raw  dI/dV_exit  [magma, 실측 직접, 보간 없음]
패널 (B): HW raw  I = n·ef    [viridis, 실측 직접, 보간 없음]
패널 (C): Raw  I vs V_exit    [GPR + BO pts + HW 데이터 3종]
패널 (D): HW raw |(I-ef)/ef|  [log scale + Eq.(1) 피팅]
```

### 컬러맵 규칙 (참조 노트북 `plot_I_sweepVx_stepVn.ipynb` 기준)

| 데이터 | 컬러맵 |
|---|---|
| I = n·ef 히트맵 | **viridis** (어두움=낮은 I, 밝음=높은 I) |
| dI/dV_exit 히트맵 | **magma** |
| I-V 곡선 | **plasma** (V_ent별 색상 구분) |

### 제목과 패널 간격

```python
gs = gridspec.GridSpec(8, 1, hspace=0.55, top=0.955, ...)
fig.text(0.5, 0.970, ...)   # 메인 제목
fig.text(0.5, 0.963, ...)   # 부제목
```
`top=0.955`로 설정하여 제목과 패널 (a) 사이에 충분한 공백을 확보한다.

---

## 7. 두 종류의 "실측 데이터" 구분

이 코드에서 "실측 데이터"라는 말이 두 가지 의미로 사용된다.

| 구분 | 설명 | 분포 | 변수 |
|---|---|---|---|
| **BO 샘플링 데이터** | Phase 4에서 BO 알고리즘이 선택한 위치에서 측정 | 불규칙 861pts | `X_meas`, `n_meas` |
| **하드웨어 실측 데이터** | Yokogawa+Keithley로 규칙 격자 직접 스캔 | 규칙 1050pts (50×21) | `instr._raw_pivot_n` |

### 왜 Raw 패널에 BO 데이터를 쓰면 안 되는가?

BO adaptive sampling은 plateau 탐색에 최적화되어 있어서 n=1 근처에 점이 집중되고 n=0, n=2 영역에는 점이 거의 없다. 이를 pivot_table로 변환하면 대부분이 NaN이 되어 히트맵이 읽기 불가능해진다.

**해결책:** Raw 패널 (A)(B)에는 반드시 HW 파일 데이터(규칙 격자)를 사용한다.

### HW 데이터 저장 위치

`_init_sim()`에서 replay 파일 로드 시 자동 저장:

```python
instr._raw_pivot_n    # pivot: index=V_ent, columns=V_exit
instr._raw_pivot_dI   # dI/dVexit pivot
instr._raw_Ve         # V_ent 배열
instr._raw_Vx         # V_exit 배열
instr._raw_n          # n 배열
```

---

## 8. I-V 곡선 패널 3가지 데이터

패널 (c)와 (C)에 3종의 데이터를 동시에 표시한다.

| 스타일 | 데이터 | 레전드 |
|---|---|---|
| 파란 실선 + 밴드 | GPR mean ± 1σ | `'GPR mean'` |
| 빨간 채운 원 | BO 샘플링 포인트 | `'BO sampling pts'` |
| 초록 빈 원 | HW 실측 데이터 | `'HW measured'` |

### BO 샘플링 포인트가 plateau 중심에 적은 이유

이것은 **정상적이고 의도된 동작**이다.

```
BO acquisition function (LCB) = GP_mean - κ × GP_std

n=1 plateau 중심:
  → cost = |n-1| ≈ 0  (이미 최적)
  → GP_mean 낮음, GP_std 낮음 (이미 충분히 탐색됨)
  → acquisition 값이 낮아 재방문 유인 없음

n=0→1, n=1→2 경계 (사면):
  → 불확실성(GP_std) 높음
  → acquisition 값이 높아 BO가 적극 탐색
```

따라서 I-V 커브에서 빨간 원이 plateau 중심보다 양쪽 경사면에 더 많이 분포하는 것이 정상이다.

---

## 9. |(I-ef)/ef| 패널 (d)(D)

### 패널 (d) — GPR 기반

Full V_exit 범위에서 GPR 예측값을 사용하므로 minimum 양쪽이 대칭적으로 표시된다.

```
검정 점 = GPR (sampled pts region)   ← BO 측정점 위치
파란 원 = GPR mean (full range)      ← 전체 V_exit 범위 GPR
빨간 선 = Eq.(1) fit to raw         ← GPR 값에 피팅
빨간 사각형 = BO sampling pts        ← 오버레이
```

### 패널 (D) — HW raw 기반

HW raw 데이터를 **그대로** 사용하고, Eq.(1)만 raw 데이터 중심으로 정확하게 피팅한다.

```
검정 점 = HW measured                ← raw 데이터 그대로
파란 원 = HW measured (ref)          ← 동일한 raw 데이터 (참조선)
빨간 선 = Eq.(1) fit to raw         ← raw에 직접 피팅
```

**목적:** HW raw 데이터의 pumping error ratio를 추산한다.

### `_fit_eq1_seeded` — data-driven 초기값

기존 `_fit_eq1`은 generic 초기값(데이터 분위수)을 사용해 Eq.(1) minimum이 raw 데이터 minimum과 어긋났다. `_fit_eq1_seeded`는 raw 데이터에서 직접 plateau 위치를 찾아 초기값으로 사용한다.

```python
err   = |n - 1.0|
mid   = argmin(err)                    # plateau 중심 인덱스
left  = 왼쪽 탐색: err > 0.3 지점 → V1_seed
right = 오른쪽 탐색: err > 0.3 지점 → V2_seed
# 4가지 시작점으로 최적화 → minimum이 raw 데이터와 일치
```

---

## 10. 시뮬레이션 모드

### Cell 11 경로 설정

```python
_path_candidates = [
    '/Users/namkim/Library/CloudStorage/Dropbox/실험일지/2026 BO code/P1_I-Vx-Vn_...txt',
    # 추가 경로를 여기에 넣으세요
]
cfg.SIM_DATA_PATH = None
for _p in _path_candidates:
    if Path(_p).exists():
        cfg.SIM_DATA_PATH = _p; break
instr = InstrumentController(cfg)   # 반드시 재생성
```

### Replay 파일 구조

```
Col0: V_ent  (V)   50개 고유값, step ≈ 5mV
Col1: V_exit (V)   21개 고유값 per slice
Col2: I_nA   (nA)
총계: 1050pts (50×21 규칙 격자)
V_p: 파일에 없음 → V_p=0.20V 고정 해석
```

---

## 11. 출력 폴더 및 파일

### 폴더명 (Cell 11 자동 설정)

```
Quantum_BO_Pump_v6_4_fixed2_sim_v5c_20260411_142035/
```

### 저장 파일 목록

| 파일 | 내용 |
|---|---|
| `phase1_pinchoff_{ts}.png` | Phase 1 pinch-off 플롯 |
| `phase2_bo_{ts}.png` | Phase 2 BO cost history |
| `phase3_confirmation_{ts}.png` | Phase 3 확인맵 + 품질 표 |
| `pump_map_8panel_{ts}.png` | Phase 4 8-panel 펌프맵 |
| `phase1_V_ent_{ts}.csv` | Phase 1 V_ent 스윕 데이터 |
| `phase1_V_exit_{ts}.csv` | Phase 1 V_exit 스윕 데이터 |
| `phase2_bo_{ts}.csv` | Phase 2 전체 BO 이력 |
| `phase3_map_{ts}.csv` | Phase 3 확인맵 데이터 |
| `phase3_quality_{ts}.csv` | Plateau 품질 지표 |
| `phase4_pumpmap_{ts}.csv` | Phase 4 펌프맵 데이터 |
| `summary_{ts}.json` | 실험 요약 |

---

## 12. 주요 Q&A — 오늘 논의된 내용

### Q. Raw 패널 히트맵이 왜 읽기 어려웠나?

BO sampling 데이터가 불규칙하게 분포되어 있어서 pivot_table로 변환하면 NaN 구멍이 많이 생기고, 이를 보간(griddata, kNN)해도 BO가 탐색하지 않은 영역(n=0, n=2)에서 부정확한 값이 외삽된다.

**해결:** Raw 패널에 HW 파일 데이터(규칙 격자 1050pts)를 직접 사용.

### Q. kNN이 해결책이 될 수 있지 않나?

kNN은 불규칙 샘플링에서 NaN 없이 smooth한 결과를 줄 수 있다. 그러나 BO 데이터를 아무리 보간해도 애초에 측정이 없는 영역(n=2 근처)은 정확하게 표현할 수 없다. 근본 해결책은 HW 규칙 격자 데이터를 사용하는 것이다.

### Q. "실측 데이터"가 두 가지 의미로 쓰인다?

맞다. 하나는 BO 알고리즘이 선택한 위치에서 측정한 **BO 샘플링 데이터**, 다른 하나는 Yokogawa+Keithley로 규칙 격자를 직접 스캔한 **하드웨어 실측 데이터**. 혼동을 피하기 위해 이 매뉴얼에서는 항상 구분해서 표기한다.

### Q. BO sampling 포인트가 n=1 plateau 중심에 왜 적나?

BO의 LCB acquisition function이 이미 탐색된 (cost가 낮은) 영역을 재방문하지 않기 때문이다. n=1 plateau 중심은 이미 cost≈0이므로 BO는 불확실한 경계 영역을 선호한다. 이는 정상적이고 의도된 동작이다.

### Q. 경계선(plateau boundary guideline)을 포기한 이유?

dI/dVexit에서 각 V_ent 행의 peak를 찾아 경계선으로 사용했으나, 측정 노이즈로 인해 peak가 잘못된 V_exit에서 검출된다. Gaussian smoothing을 적용해도 히트맵 색상 강도와 일치하지 않는다. 이 문제는 현재 데이터 노이즈 수준에서 해결이 불가능하다.

### Q. 패널 (D)에서 Eq.(1) fit이 raw 데이터 minimum과 맞지 않은 이유?

기존 코드가 smoothed 데이터를 n_fitted로 전달하고 여기에 Eq.(1)을 피팅했기 때문이다. 패널 (D)의 목적은 HW raw 데이터의 pumping error를 추산하는 것이므로 raw 데이터에 직접 피팅해야 한다. `_fit_eq1_seeded`를 도입하여 raw 데이터의 minimum 위치를 초기값으로 사용하면 해결된다.

### Q. 제목이 패널 (a)와 겹쳐 보이는 이유?

GridSpec의 `top=0.975`로 설정되어 있어 첫 패널이 너무 위에서 시작하기 때문이다. `top=0.955`로 낮추고 제목 y 좌표를 0.970/0.963으로 조정하면 충분한 여백이 생긴다.

---

## 13. 수정 이력 (v4 → v5c)

### v4 → v5 (raw 패널 개선 1차)

- Raw 패널에 kNN 회귀 도입
- pivot_table/groupby 제거 시도
- plateau 경계선 추가 (후에 제거)

### v5 → v5b (HW 데이터 직접 사용)

- `_init_sim()`에 `_raw_pivot_n`, `_raw_pivot_dI` 저장 추가
- Raw 패널 (A)(B): HW 파일 pivot 직접 사용 (seaborn heatmap)
- 패널 (c)(C): GPR + BO pts + HW 데이터 3종 동시 표시
- 패널 (D): HW raw 데이터 직접 사용

### v5b → v5c (피팅 및 마무리)

- `_fit_eq1_seeded` 추가: V1/V2 초기값을 raw 데이터 minimum에서 추출
- `_draw_ef_panel`: Eq.(1)을 nl_raw에 직접 피팅 (스무딩 제거)
- 패널 (D) 레이블 수정: `'HW measured'`, `'Eq.(1) fit to raw'`
- 경계선 가이드 전면 제거 (`_find_boundaries`, `_draw_bnd_pixel` 삭제)
- 출력 폴더명: 코드명 + 타임스탬프로 자동 명명
- Figure 여백: `top=0.955`, 제목 y=0.970/0.963

---

## 14. 문제 해결

| 증상 | 원인 | 해결 |
|---|---|---|
| Raw 히트맵 불선명 | BO 데이터 불균일 분포 | HW 파일 pivot 사용 |
| Eq.(1) minimum 불일치 | generic 초기값 또는 스무딩 데이터 | `_fit_eq1_seeded` + raw 데이터 |
| 제목이 패널에 겹침 | GridSpec top=0.975 | top=0.955, y=0.970/0.963 |
| IndexError: gradient | 단일 포인트 V_ent 그룹 | `len(grp) >= 2` 가드 |
| SyntaxError: unterminated | form-feed \x0c 문자 | chr(12) 직접 교체 |
| SIM_DATA_PATH 미설정 | Cell 11 경로 못 찾음 | `_path_candidates` 리스트에 추가 |
| "Fitted mean" = "Measured" | 같은 배열 두 번 전달 | GPR 또는 별도 참조값 전달 |
| BO pts가 plateau 중심에 없음 | 정상 BO 동작 | 문제 아님 (섹션 8 참조) |

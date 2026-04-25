# STYLE_GUIDE.md — per-panel plot style control

Layer C 후처리 플롯(`fig_E1`, `fig_E2`, `fig_C`, `fig_M1`, `fig_M2`, `fig_T`) 의
figure 크기, 라벨/틱/범례 글자크기, 심볼 크기, 범례 위치 등을 **패널별로**
제어하는 방법 매뉴얼입니다.

> **모든 그림 스타일은 `plot_publication.py` 한 곳에서만 편집합니다.**
> `main.py` 는 더이상 스타일에 손댈 필요 없습니다.

---

## 1. 구조 개요

```
plot_publication.py
   └── class PlotStyle
          ├── 전역 기본값 (fig_w, fig_h, label_size, ms, …)
          ├── PANELS = { 'E1': {...override only...}, 'E2': {...}, ... }
          └── PlotStyle.for_panel('E1')  →  defaults + PANELS['E1'] 적용된 인스턴스
                                        ↓
main.py:           st_E1 = PlotStyle.for_panel('E1')
                   fig   = fig_E1_eta_extrapolation(..., st=st_E1)
```

- `PlotStyle` 의 클래스 변수 = "모든 패널의 기본값".
- `PlotStyle.PANELS['E1'] = {...}` = "E1 에서만 다르게 할 필드".
- 기재하지 않은 필드는 `PlotStyle` 의 기본값을 그대로 사용합니다.
- `for_panel(key)` 가 자동으로 `defaults + override` 를 합쳐 인스턴스를 만들어 줍니다.

---

## 2. 제어 가능한 필드 전체 목록 (`PlotStyle`)

### 2.1  Figure 크기 (인치)

| field   | 기본값 | 설명                                                        |
| ------- | ------ | ----------------------------------------------------------- |
| `fig_w` | `7.0`  | 가로. APL single = 3.37, double = 7.0.                      |
| `fig_h` | `3.6`  | 세로. 아래 여백(범례 bbox)을 고려해 여유 있게.             |

### 2.2  글자 크기 (pt)

| field         | 기본값 | 설명                                   |
| ------------- | ------ | -------------------------------------- |
| `label_size`  | `9`    | x/y 축 라벨.                           |
| `tick_size`   | `8`    | 틱 숫자.                               |
| `legend_size` | `8`    | 범례 항목.                             |
| `title_size`  | `9`    | 축 타이틀.                             |
| `cbar_size`   | `8`    | 컬러바 틱.                             |
| `annot_size`  | `8`    | 본문 annotation. audit 은 `-2` 적용됨. |
| `panel_size`  | `11`   | 패널 라벨 "(E1)" 등.                   |
| `font_family` | `Arial`| 전체 폰트 패밀리.                      |

### 2.3  선 / 마커

#### 선 굵기

| field        | 기본값 | 설명                              |
| ------------ | ------ | --------------------------------- |
| `lw`         | `1.2`  | 일반 선.                          |
| `lw_model`   | `1.5`  | fit 모델 곡선 (Schoinas/Seo).     |
| `lw_asym`    | `1.0`  | 점근선 / 기준선.                  |
| `lw_contour` | `0.8`  | η_noise 컨투어.                   |

#### 데이터 심볼 크기 (시리즈별 분리)

| field              | 기본값 | 사용처            | 설명                                         |
| ------------------ | ------ | ----------------- | -------------------------------------------- |
| `ms_bo`            | `3`    | E1, E2            | BO-sampled η scatter (회색 동그라미).        |
| `ms_gpr_grid`      | `3`    | E1                | GPR grid η scatter (파란 사각형).            |
| `ms_fit_pts`       | `5`    | E1                | fit point highlight (빨간 빈 동그라미).      |
| `ms_best`          | `12`   | E1, M1, M2        | "best point" 노란/검은 별.                   |
| `ms_schoinas_star` | `12`   | E2                | Schoinas η_E^min 별 (darkred).               |
| `ms_seo_star`      | `12`   | E2                | Seo η_E^min 별 (darkblue).                   |
| `ms_bo_iv`         | `5`    | C                 | I-vs-V_exit 의 BO 샘플링 점 (빨간 채움).     |
| `ms_phase4`        | `3`    | M2                | phase4 stage 마커 (lhs/rhs/top/bot/center/grid). |
| `ms_bo_history`    | `18`   | M2                | BO 이력 scatter — `s=` 값(면적 기반, 다른 ms 와 단위 다름). |

> **주의** — `ms_bo_history` 만 `scatter` 의 `s=` (면적, 단위 pt²) 입니다.
> 다른 모든 `ms_*` 는 `plot()` 의 `markersize` (단위 pt). 즉 비슷한 시각
> 크기를 위해서는 `ms_bo_history ≈ (markersize)²` 정도가 됩니다.
> 예: `ms=5` 와 비슷하게 보이려면 `ms_bo_history ≈ 25`.

#### Legacy aliases (사용 비권장)

| field      | 기본값 | 비고                                                           |
| ---------- | ------ | -------------------------------------------------------------- |
| `ms`       | `3`    | 과거 일반 scatter. 현재 코드에서 직접 참조 안 함.              |
| `ms_fit`   | `5`    | 과거 fit-pt/I-V 공용. 현재 `ms_fit_pts` / `ms_bo_iv` 로 분리.  |

### 2.4  패널 라벨 "(E1)" 배치

| field              | 기본값           | 설명                                         |
| ------------------ | ---------------- | -------------------------------------------- |
| `panel_label`      | `True`           | `False` → 패널 라벨 자체를 숨김.             |
| `panel_label_text` | `None`           | `None` → 함수 기본값. 문자열로 치환 가능.    |
| `panel_label_x`    | `0.02`           | axes 좌표 (0=좌, 1=우).                      |
| `panel_label_y`    | `0.97`           | axes 좌표 (0=하, 1=상).                      |
| `panel_label_ha`   | `'left'`         | horizontal align.                            |
| `panel_label_va`   | `'top'`          | vertical align.                              |

### 2.5  범례 제어

| field                   | 기본값              | 설명                                                       |
| ----------------------- | ------------------- | ---------------------------------------------------------- |
| `legend_loc`            | `'upper center'`    | matplotlib loc.                                            |
| `legend_ncol`           | `3`                 | 열 개수.                                                   |
| `legend_bbox_to_anchor` | `(0.5, -0.34)`      | 축 바깥 앵커. `None` 이면 bbox 미사용(axes 안쪽 배치).    |
| `legend_framealpha`     | `0.92`              | 범례 박스 투명도.                                          |
| `legend_handlelength`   | `None`              | 마커/선 길이. None=matplotlib 기본.                        |
| `legend_handletextpad`  | `None`              | 마커–텍스트 간격.                                         |
| `legend_labelspacing`   | `None`              | 항목 간 세로 간격.                                         |
| `legend_borderpad`      | `None`              | 내부 여백.                                                 |
| `legend_borderaxespad`  | `0.3`               | axes 과의 거리.                                            |

### 2.6  타이틀 & 감사(audit) 스트립

| field              | 기본값             | 설명                                                                |
| ------------------ | ------------------ | ------------------------------------------------------------------- |
| `show_title`       | `True`             | 축 타이틀 on/off.                                                   |
| `title_pad`        | `8`                | 타이틀–축 간격.                                                     |
| `audit_show`       | `True`             | 감사 스트립 on/off.                                                 |
| `audit_loc`        | `'figure'`         | `'figure'` / `'axes_top'` / `'off'`. 좌표계 결정 (위/아래는 `audit_y` + `audit_va` 로). |
| `audit_x`          | `0.5`              | 텍스트 기준점 x. **figure**: 페이지 좌표 [0..1] (0=좌, 1=우); **axes_top**: 축 박스 좌표 (0=축 좌단, 1=축 우단). |
| `audit_y`          | `0.005`            | 텍스트 기준점 y. 같은 좌표계 (0=하단, 1=상단). **figure 모드에서 0 근처 = 페이지 바닥, 1 근처 = 페이지 상단.** |
| `audit_ha`         | `'center'`         | 가로 정렬: `'left'`/`'center'`/`'right'` — 텍스트의 어느 부분을 `audit_x` 에 맞출지. |
| `audit_va`         | `'bottom'`         | 세로 정렬: `'bottom'`/`'center'`/`'top'` — 텍스트의 어느 부분을 `audit_y` 에 맞출지. |
| `audit_size_delta` | `-2`               | 폰트 크기 = `max(annot_size + delta, 5)`. 더 음수면 더 작게.        |
| `audit_color`      | `'#555555'`        | 텍스트 색.                                                          |

**`(audit_x, audit_y)` 의 의미** — 이 두 값은 `matplotlib.Figure.text(x, y, ...)`
또는 `Axes.text(x, y, ...)` 에 그대로 전달되는 **텍스트 기준점 좌표**입니다.
`audit_ha`/`audit_va` 가 텍스트 박스의 어느 모서리·중심을 그 좌표에 정렬할지
결정합니다. 예:
- `audit_x=0.01, audit_ha='left'` → 텍스트 **왼쪽 끝**이 그림 1% 위치에 (좌측 정렬).
- `audit_x=0.5,  audit_ha='center'` → 텍스트 **중앙**이 그림 50% 위치에 (가운데 정렬).
- `audit_y=0.005, audit_va='bottom'` → 텍스트 **밑변**이 그림 0.5% 높이에.

> **좌표계는 `audit_loc` 가 결정** — `figure` 일 땐 페이지 전체 [0..1] 좌표,
> `axes_top` 일 땐 축 박스 [0..1+] 좌표. 모드를 바꾸면 `audit_x`/`audit_y` 도
> 함께 조정해야 합니다 (§7.7 참고).
>
> **`figure` 모드에서 위/아래 선택**: 위치는 오직 `audit_y` 와 `audit_va` 가
> 결정합니다. 별도의 "top/bottom" 모드 없음.
> - 페이지 **바닥**: `audit_y=0.005` + `audit_va='bottom'`
> - 페이지 **상단**: `audit_y=0.995` + `audit_va='top'`
> - 가운데: `audit_y=0.5` + `audit_va='center'`

### 2.7  Page margin (tight_layout 이후 덮어쓰기)

| field           | 기본값 | 설명                                                               |
| --------------- | ------ | ------------------------------------------------------------------ |
| `bottom_margin` | `None` | 그림 바닥에서 axes 까지 비울 비율 [0..1]. 키울수록 x-라벨이 위로.   |
| `top_margin`    | `None` | 그림 상단에서 axes 까지의 위치 (1 에 가까울수록 axes 가 위로 큼).  |
| `left_margin`   | `None` | 좌측 여백 (axes 시작 x 좌표).                                      |
| `right_margin`  | `None` | 우측 여백 (axes 끝 x 좌표).                                        |

`None` 이면 matplotlib 의 `tight_layout(pad=0.4)` 결과를 그대로 사용합니다.
값이 있으면 `tight_layout(pad=0.4, rect=(L, B, R, T))` 로 호출되어, 페이지의
`(left, bottom, right, top)` 분수 좌표로 정의된 사각형 안에 axes/colorbar/
legend 등이 **함께** 재배치됩니다. (예전 버전은 `subplots_adjust` 를 썼는데,
이는 메인 axes 만 옮겨서 colorbar 가 따로 노는 문제가 있었습니다 — 특히
M2 처럼 colorbar 가 2개인 경우.)
사용처:

- **x-축 라벨–페이지 바닥 사이 여백 키우기** → `bottom_margin = 0.12` (12%)
- **페이지 상단 audit 와 타이틀이 겹칠 때** → `top_margin = 0.92` (위 8% 비움)
- **컬러바가 우측에서 잘릴 때** → `right_margin = 0.92`

> **주의** — `savefig(bbox_inches='tight')` 가 다시 한번 외곽을 잘라내므로,
> 너무 큰 여백을 주면 PDF/PNG 의 실제 페이지 크기가 의도보다 작아질 수 있습니다.
> 0.05–0.20 범위에서 시작해 시각 확인하며 조정하세요.

### 2.8  출력

| field     | 기본값          | 설명                                          |
| --------- | --------------- | --------------------------------------------- |
| `out_fmt` | `['pdf','png']` | 저장 포맷 (CLI `--no-pdf` 등으로도 변경됨).   |
| `dpi`     | `300`           | 래스터 출력 해상도.                           |
| `out_dir` | `None`          | 보통 CLI 가 런 폴더 옆 `_postplot` 에 지정.   |

---

## 3. 사용법 — `plot_publication.py` 의 `PlotStyle.PANELS` 를 편집

```python
# plot_publication.py  ──  class PlotStyle 안쪽
class PlotStyle:
    fig_w  = 7.0
    fig_h  = 3.6        # ← 전역 기본값. 모든 패널의 출발점.
    label_size = 9
    legend_ncol = 3
    # ... (생략) ...

    PANELS = {
        'E1': {                           # ← E1 만 fig_h = 3.8
            'fig_h': 3.8,
        },
        'E2': {
            'fig_h': 3.6,
            'legend_ncol': 2,
        },
        'C': {
            'fig_h': 4.4,
            'legend_bbox_to_anchor': (0.5, -0.22),
        },
        'M1': {
            'fig_h': 4.2,
            'legend_loc': 'upper right',
            'legend_ncol': 1,
            'legend_bbox_to_anchor': None,    # ← 안쪽 배치
            'audit_loc': 'axes_top',
        },
        'M2': { ... },
        'T':  { ... },
    }
```

바꾸고 싶은 패널 키(`E1`/`E2`/`C`/`M1`/`M2`/`T`) 아래에 `PlotStyle` 의
필드 이름을 그대로 적습니다. **다른 패널에 영향 없음, main.py 수정 불필요.**

```bash
python main.py <run_dir>
```

다시 실행하면 반영됩니다.

> **전역 기본값을 바꾸고 싶다면** — 예: 모든 패널을 한꺼번에 더 크게 →
> `class PlotStyle` 의 `fig_w` / `fig_h` 자체를 수정하고, **`PANELS` 의
> 해당 키에서 `fig_w` / `fig_h` 줄을 지우세요.** PANELS 에 적힌 값은
> 항상 클래스 기본값을 덮어쓰므로, 안 지우면 기본값 변경이 패널에
> 도달하지 않습니다 (§7 주의사항 참고).

---

## 4. 레시피 모음

### 4.1  E1 을 APL single-column (3.37") 로

```python
'E1': {
    'fig_w': 3.37, 'fig_h': 2.8,
    'label_size': 8, 'tick_size': 7, 'legend_size': 7,
    'legend_ncol': 1,
    'legend_loc': 'lower right',
    'legend_bbox_to_anchor': None,   # axes 안쪽
    'audit_loc': 'off',
},
```

### 4.2  범례를 axes 안쪽으로 이동

```python
'E2': {
    'legend_loc': 'lower right',
    'legend_bbox_to_anchor': None,   # ★ 반드시 None
    'legend_ncol': 1,
    'audit_loc': 'axes_top',
},
```

### 4.3  심볼/모델 곡선 두껍게 (발표용)

```python
'E1': {
    'ms_bo': 5, 'ms_gpr_grid': 5,
    'ms_fit_pts': 9, 'ms_best': 18,
    'lw_model': 2.2, 'lw_asym': 1.4,
},
'E2': {
    'ms_bo': 5,
    'ms_schoinas_star': 18, 'ms_seo_star': 18,
    'lw_model': 2.2,
},
'C': {
    'ms_bo_iv': 8,
    'lw': 1.8,
},
'M2': {
    'ms_phase4': 6,
    'ms_bo_history': 36,    # scatter s= 는 면적 기반 → 약 (6)² 수준
    'ms_best': 18,
},
```

### 4.4  글자 전부 크게 (프로젝터 슬라이드용)

```python
'C': {
    'fig_w': 9.0, 'fig_h': 5.4,
    'label_size': 12, 'tick_size': 11, 'legend_size': 11,
    'title_size': 13, 'panel_size': 14, 'cbar_size': 11,
    'ms_bo_iv': 7,
},
```

### 4.5  패널 라벨을 축 바깥 상단 왼쪽으로

```python
'E1': {
    'panel_label_x': -0.10,
    'panel_label_y':  1.06,
    'panel_label_ha': 'left',
    'panel_label_va': 'bottom',
},
```

### 4.6  타이틀 완전 제거 (논문 그림 용)

```python
'E1': { 'show_title': False, 'audit_loc': 'off' },
'E2': { 'show_title': False, 'audit_loc': 'off' },
```

### 4.7  범례 줄 간격/핸들 길이 촘촘하게

```python
'M2': {
    'legend_handlelength': 1.5,
    'legend_handletextpad': 0.3,
    'legend_labelspacing':  0.2,
    'legend_borderpad':     0.3,
},
```

### 4.8  범례를 axes 안쪽 임의 위치로 (E1/E2 예시)

```python
# 우상단 안쪽 — fit 곡선이 좌하단을 차지하는 fig_E1 에 적합
'E1': {
    'legend_loc': 'upper right',
    'legend_bbox_to_anchor': (0.98, 0.98),
    'legend_ncol': 1,
},
# 좌하단 안쪽 — fig_E2 의 빈 공간 활용
'E2': {
    'legend_loc': 'lower left',
    'legend_bbox_to_anchor': (0.02, 0.02),
    'legend_ncol': 1,
},
# 자유 위치 (axes 70%, 65%)
'M1': {
    'legend_loc': 'center',
    'legend_bbox_to_anchor': (0.70, 0.65),
    'legend_ncol': 1,
},
```
좌표 의미와 헷갈리는 점은 §5 표·해설 참고.

### 4.9  Audit 텍스트 위치/크기 조정 — x축과 겹칠 때

기본값은 그림 맨 아래(`fig coord (0.5, 0.005)`, center, 작은 회색).
키 큰 그림(`fig_h=7.0+`)에서는 x-label 과 audit 줄이 가까워져 겹쳐 보일 수
있습니다. 다음 중 하나로 해결:

```python
# (a) 그림 안에서 audit 를 더 아래로 — fig_y 를 0 근처로 (savefig bbox=tight 가 패딩 추가)
'E1': {
    'audit_y': 0.001,           # 거의 figure 하단
    'audit_size_delta': -3,     # 폰트도 더 작게
},

# (b) audit 를 왼쪽 정렬해 x-label 의 가운데 영역과 어긋나게
'E1': {
    'audit_x': 0.01,
    'audit_ha': 'left',
},

# (c) audit 를 axes 위쪽으로 옮기기 (타이틀 없을 때 유용)
'E1': {
    'audit_loc': 'axes_top',
    'audit_x': 0.01, 'audit_y': 1.02, 'audit_ha': 'left',
    'show_title': False,        # 타이틀과 충돌 방지
},

# (d) audit 자체를 끄기 (논문용 정식 그림)
'E1': { 'audit_show': False },
# 또는
'E1': { 'audit_loc': 'off' },
```

### 4.10  Audit 를 페이지 **상단** 으로

```python
'E1': {
    'audit_loc': 'figure',
    'audit_x': 0.01, 'audit_y': 0.995,
    'audit_ha': 'left', 'audit_va': 'top',
    'audit_size_delta': -3,
    'top_margin': 0.92,            # 타이틀과 겹치면 axes 를 좀 더 내려
}
```

핵심은 `audit_y` 를 1 근처로 + `audit_va='top'`. 모드는 `'figure'` 하나뿐이며,
위/아래는 좌표값으로만 결정합니다. (별도의 `figure_top` 모드는 더이상 없음.)

### 4.11  x-축 라벨이 페이지 바닥에 너무 붙을 때

```python
'E1': {
    'fig_h': 6.0,
    'bottom_margin': 0.12,    # 바닥에서 12% 만큼 axes 를 위로
}
```

`bottom_margin` 은 0–1 범위의 figure 분수 좌표입니다. 0.08 부터 시작해서
0.02 단위로 키우며 시각 확인하세요.

### 4.12  PNG 만 저장, DPI 600 (CLI)

```bash
python main.py <run_dir> --no-pdf
```

---

## 5. 범례 배치 — `legend_loc` × `legend_bbox_to_anchor`

### 5.0  ⚠️  요소별 좌표계 비교 (꼭 먼저 읽기)

같은 0..1 분수 좌표라도 **요소마다 기준이 다릅니다.** 이걸 안 맞추면
"왜 이 위치가 나오지?" 하는 혼란이 자주 생깁니다.

| 요소         | 좌표계 기본값                  | (0,0) 의 의미      | (1,1) 의 의미      | 좌표계 변경 |
| ------------ | ------------------------------ | ------------------ | ------------------ | ----------- |
| **legend**   | **axes 좌표** [0..1+]          | axes 박스 좌하단    | axes 박스 우상단    | (현재 미노출 — figure 좌표 쓰려면 코드 수정 필요) |
| **audit**    | `audit_loc` 가 결정             | `'figure'`: 페이지 좌하단 / `'axes_top'`: 축 박스 좌하단 | `'figure'`: 페이지 우상단 / `'axes_top'`: 축 박스 우상단 | `audit_loc` 한 필드로 토글 |
| **panel_label** | **axes 좌표** [0..1+]      | axes 박스 좌하단    | axes 박스 우상단    | (코드에 박혀 있음 — 변경 불가) |

**핵심 차이의 의미:**

- `legend_bbox_to_anchor = (0.5, -0.34)` →
  axes 박스의 (50%, -34%) → axes **바로 아래 외부** (axes 따라다님).
- `audit_x = 0.5, audit_y = 0.005` (`audit_loc='figure'`) →
  페이지의 (50%, 0.5%) → **페이지 바닥 중앙** (axes 위치와 무관).

같은 `(0.5, 0.005)` 값도 legend 에 넣으면 "axes 박스의 절반 높이의 0.5%
지점 = axes 거의 바닥 안쪽" 이 되고, audit 에 넣으면 "페이지 거의 바닥"
이 됩니다. **수치는 같지만 기준점이 다릅니다.**

**왜 이렇게 비대칭으로 두었나** — matplotlib 관례:
- Legend 는 데이터 옆에 붙는 것이 일반적이라 axes 추종이 자연스럽고,
- Audit/footer 는 페이지 가장자리에 고정하는 것이 일반적이라 figure
  기준이 자연스럽기 때문. 두 요소를 같은 좌표계로 강제하면 오히려
  사용성이 떨어집니다.

> **실전 팁** — 위치를 옮길 때는 먼저 "이게 axes 기준인가 page 기준인가" 부터
> 떠올리세요. 그 다음에야 (x, y) 숫자를 손봅니다. 표 §5.2 / 표 §2.6 의 좌표
> 예시는 모두 각자의 좌표계 기준입니다.

### 5.1  두 파라미터의 역할

`ax.legend(loc=..., bbox_to_anchor=(x, y))` 의 의미:

- `legend_bbox_to_anchor = (x, y)` — **앵커 점의 좌표** (axes 분수 좌표계).
  - `(0, 0)` = axes 좌하단, `(1, 1)` = axes 우상단,
  - `(0.5, -0.34)` = axes 아래 (외부), `(1.05, 0.5)` = axes 우측(외부).
  - **`None` 이면** bbox 비활성화 → matplotlib 이 `legend_loc` 만 보고 자동 배치.
- `legend_loc` — **범례 박스의 어느 모서리**를 그 앵커 점에 맞출지.
  - 즉 `loc='upper right'` + `bbox_to_anchor=(0.98, 0.98)` →
    "범례의 우상단 모서리"를 "axes 의 (98%, 98%) 점"에 위치.

> **두 값을 함께 봐야** 위치가 정해집니다. 한쪽만 바꾸면 의도와 다르게 동작.

### 5.2  자주 쓰는 조합 표

| 원하는 위치                      | `legend_loc`     | `legend_bbox_to_anchor`         |
| -------------------------------- | ---------------- | ------------------------------- |
| 안쪽 우상단 (논문 일반)           | `'upper right'`  | `(0.98, 0.98)` 또는 `None`      |
| 안쪽 좌상단                       | `'upper left'`   | `(0.02, 0.98)` 또는 `None`      |
| 안쪽 우하단                       | `'lower right'`  | `(0.98, 0.02)` 또는 `None`      |
| 안쪽 좌하단                       | `'lower left'`   | `(0.02, 0.02)` 또는 `None`      |
| 안쪽 자유 위치 (예: 70%, 65%)     | `'center'`       | `(0.70, 0.65)`                  |
| 외부 하단 중앙 (현 default)       | `'upper center'` | `(0.5, -0.34)`                  |
| 외부 상단 중앙                    | `'lower center'` | `(0.5, 1.05)`                   |
| 외부 우측 중앙                    | `'center left'`  | `(1.02, 0.5)`                   |
| 외부 좌측 중앙                    | `'center right'` | `(-0.02, 0.5)`                  |
| 자동 (matplotlib 알아서)          | `'best'`         | `None`                          |

### 5.3  핵심 헷갈림 포인트

1. **"안쪽 임의 위치"** → `loc='center'` + `bbox_to_anchor=(x, y)` 가 가장 직관적.
   `loc` 가 `'upper right'` 면 박스 우상단 기준이라 좌표 해석이 한 박스 만큼 어긋남.
2. **`None` vs 값** — 코너 4개 (upper/lower × left/right) 는
   `bbox_to_anchor=None` 만으로도 "안쪽 그 코너"에 붙습니다.
   `(0.98, 0.98)` 처럼 명시하면 가장자리 여백을 직접 제어 가능.
3. **외부에 두려면** y 가 `(0,1)` 범위를 벗어나야 합니다 (위: `>1`, 아래: `<0`).
   x 도 마찬가지 (좌: `<0`, 우: `>1`).

---

## 6. 새 필드 추가하기

1. `plot_publication.py` 의 `class PlotStyle` 본문에 클래스 변수 추가.
2. 헬퍼(`_place_legend`/`_place_audit`/`_panel_label`) 또는 각 `fig_*` 에서
   `st.<new_field>` 로 참조.
3. 이 문서 §2 표에 한 줄 추가.
4. 필요하면 `PlotStyle.PANELS` 의 해당 패널에 override 예시 추가.

---

## 7. ⚠️  주의사항 (꼭 읽어주세요)

### 7.1  `PANELS[key]` 값은 **항상** 클래스 기본값을 이깁니다

`for_panel('E1')` 은 `setattr(st, k, v)` 로 PANELS dict 항목을 덮어씌웁니다.
그러므로 **`class PlotStyle.fig_h = 7.6` 으로 바꿔도, `PANELS['E1']` 에
`'fig_h': 3.8` 줄이 남아 있으면 출력은 3.8 입니다.**

원하는 동작별 처방:

| 의도                          | 처방                                                   |
| ----------------------------- | ------------------------------------------------------ |
| 모든 패널을 한꺼번에 변경     | `class PlotStyle` 기본값만 수정 + `PANELS` 의 해당 key 줄 삭제 |
| 한 패널만 다르게              | `PANELS['E1']` 에 항목 추가/수정                       |
| 한 패널을 디폴트로 되돌리고 싶음 | `PANELS['E1']` 에서 그 필드 줄 삭제                  |

### 7.2  `legend_bbox_to_anchor` 와 `legend_loc` 의 짝

axes **안쪽**에 범례를 두려면 **반드시** `'legend_bbox_to_anchor': None`
을 함께 넣어야 합니다. None 이 아니면 외부 앵커가 우선되어 axes 바깥으로
밀려납니다. (`legend_loc='upper right'` 만 단독으로 적으면 효과 없음.)

```python
# ✅
'M1': {
    'legend_loc': 'upper right',
    'legend_bbox_to_anchor': None,
}

# ❌ (PlotStyle 의 (0.5,-0.34) 가 그대로 적용되어 바깥으로 나감)
'M1': {
    'legend_loc': 'upper right',
}
```

### 7.3  `fig_h` 가 너무 작으면 범례가 잘립니다

기본값은 범례를 axes 아래(`bbox_to_anchor=(0.5,-0.34)`)에 둡니다.
`fig_h` 를 3.0 미만으로 줄이면 범례가 그림 밖으로 잘릴 수 있습니다.
이런 경우 §4.2 처럼 axes 안쪽 배치로 같이 전환하세요.

### 7.4  `audit_loc='axes_top'` + `show_title=True` 충돌

축 위(`axes_top`)에 audit 줄을 두면 타이틀과 겹칠 수 있습니다. M1/M2 처럼
타이틀이 필수가 아니거나 짧은 경우에만 사용하고, 길이가 긴 2-line 타이틀
(fig_C 등)에서는 기본값(`'figure'`) 또는 `'off'` 를 쓰세요.

### 7.5  CLI 의 `--no-pdf` / `dpi` 는 PANELS 와 별개

`out_fmt`, `dpi` 는 main.py 에서 CLI 인자로 덮어씌워집니다 (모든 패널 공통).
패널별로 다른 dpi / 포맷이 필요하면 `PANELS['E1']['dpi'] = 600` 식으로
넣으면 됩니다 (이 경우 main.py 의 CLI 적용 라인이 그 값을 또 덮어쓰는 점만
유의 — 현재 코드는 `st.dpi` / `st.out_fmt` 를 base 에서 패널 인스턴스로
복사합니다).

### 7.6  `ms_bo_history` 만 단위가 다름 (M2)

`fig_M2` 의 BO 이력은 `ax.scatter()` 로 그려지므로 `s=` 인자가 **면적
(pt²)** 입니다. 다른 `ms_*` 필드(`ax.plot()` 의 `markersize`)는 **선형
(pt)** 입니다. 같은 시각 크기를 원하면 `ms_bo_history ≈ markersize²` 로
환산하세요. 예: `ms=5` 와 비슷한 점 → `ms_bo_history=25`.

### 7.7  Audit 좌표는 `audit_loc` 모드에 묶임

`audit_loc='figure'` 이면 `(audit_x, audit_y)` 는 **페이지 좌표**
(`[0,1]`, 페이지 전체 기준), `audit_loc='axes_top'` 이면 **축 좌표**
(`[0,1+]`, 축 박스 기준)입니다.

모드만 바꾸고 좌표를 그대로 두면 audit 가 엉뚱한 곳에 갑니다.
예: 기본값 `(0.5, 0.005)` 인 채 `audit_loc='axes_top'` 으로 바꾸면
audit 가 axes 안쪽 거의 바닥(`y=0.005`)에 그려져 데이터와 겹침.

→ 모드 바꾸면 `audit_x`/`audit_y`/`audit_ha`/`audit_va` 같이 갱신.
일반적인 짝:
- `figure` (페이지 바닥): `(0.5, 0.005)`  + `ha='center'`, `va='bottom'`
- `figure` (페이지 상단): `(0.01, 0.995)` + `ha='left'`,   `va='top'`
- `axes_top`            : `(0.01, 1.02)`  + `ha='left'`,   `va='bottom'`

`audit_loc` 의 허용값은 `'figure' | 'axes_top' | 'off'` 셋뿐입니다.
이 외의 문자열을 넣으면 **`ValueError` 가 즉시 발생**합니다 — 예전의
`'figure_bottom'`/`'figure_top'` 도 더이상 받지 않으니 (`'figure'` 로
교체) 주의.

### 7.8  큰 그림에서 audit 가 x-label 과 겹치는 경우

`fig_h ≥ 7.0` 처럼 세로가 큰 그림은 tight_layout 이 axes 를 거의 끝까지
펼치므로 x-label 과 fig-bottom audit (`y≈0.005`) 사이 여백이 거의 없어
겹쳐 보입니다. 처방은 §4.9 (a–d) 또는 §4.11 (`bottom_margin`) 참고.

### 7.11  `*_margin` 사용 시 `bbox_inches='tight'` 가 자동 해제

`savefig(bbox_inches='tight')` 는 페이지 여백을 다시 잘라내므로, 일부러
만든 `bottom_margin` 을 무효화합니다(겉보기에 axes 가 페이지 중앙으로 떠
보이고 colorbar 와 어긋남). `_save()` 는 마진 필드가 하나라도 설정되어
있으면 자동으로 `bbox_inches=None` 으로 저장 — 결과 파일 크기는 정확히
`fig_w × fig_h` 인치가 됩니다.

마진을 안 쓰는 패널(C, M1, T 등)은 종전처럼 `bbox_inches='tight'` 로
저장되어 외곽 여백이 자동 트림됩니다.

### 7.10  `bottom_margin` / `top_margin` 은 `tight_layout(rect=...)` 으로 적용

`_apply_style()` 은 마진 값이 하나라도 있으면 `tight_layout(pad=0.4,
rect=(L,B,R,T))` 한 번으로 호출합니다. 이 사각형 안에 axes + colorbar +
legend 가 **함께** 들어가도록 matplotlib 이 재배치합니다.

너무 작게(예: `bottom=0.02`) 주면 x-label 이 잘리고, 너무 크게(예: `bottom=0.40`)
주면 axes 영역이 좁아집니다. 0.08–0.18 정도가 일반적인 안전 구간입니다.

> **왜 `subplots_adjust` 대신 `tight_layout(rect=)` 인가** — `subplots_adjust`
> 는 메인 subplot 의 위치만 손보고 `fig.colorbar(..., ax=ax)` 로 만든
> colorbar 축은 같이 옮겨주지 않습니다. M2 처럼 colorbar 가 2개인 그림에서
> axes 가 페이지 중앙으로 떠 보이고 colorbar 와 어긋나는 현상의 원인.
> `tight_layout(rect=)` 은 colorbar 까지 포함해 한 번에 맞춰 잡아 줍니다.

### 7.9  새 패널 추가 시

`fig_*` 함수를 새로 만들었다면 `PANELS` 에 그 패널의 키를 추가하세요.
누락하면 `PANELS.get(key, {})` 가 빈 dict 를 반환해 모든 필드가 클래스
기본값으로 갑니다 (오류는 안 나지만, 의도와 다를 수 있음).

끝.

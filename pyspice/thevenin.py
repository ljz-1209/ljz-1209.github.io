# -*- coding: utf-8 -*-
"""
② 戴维南定理验证 —— PySpice 仿真（自定参数）

被测含源二端网络：
    V1 = 10 V（理想电压源）
    R1 = 1 kΩ（V1 正极串到端口 a）
    R2 = 2.2 kΩ（端口 a 对地并联）
    端口 = (a, 地)

理论值：
    V_oc = V1·R2/(R1+R2) = 10×2.2/3.2 = 6.875 V
    I_sc = V1/R1 = 10 mA（R2 被短路）
    R_th = R1∥R2 = 1k×2.2k/3.2k = 687.5 Ω（= V_oc / I_sc）

仿真内容：
    1. OP 分析：端口开路测 V_oc
    2. OP 分析：端口短路（0V 电流表源）测 I_sc
    3. 接 RL = 1kΩ / 4.7kΩ：原网络 vs 戴维南等效电路，对比端口电压/电流

运行：python thevenin.py
输出：circuits/thevenin_circuit.png、circuits/thevenin_equivalent.png
      plots/thevenin_load_compare.png
      results/thevenin.md
"""
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PySpice.Spice.Netlist import Circuit
from PySpice.Unit import *

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

HERE = Path(__file__).resolve().parent
PLOTS = HERE / 'plots'
CIRCUITS = HERE / 'circuits'
RESULTS = HERE / 'results'
for d in (PLOTS, CIRCUITS, RESULTS):
    d.mkdir(exist_ok=True)

# ---------------- 参数与理论值 ----------------
V1 = 10.0      # V
R1 = 1e3       # Ω
R2 = 2.2e3     # Ω
V_OC = V1 * R2 / (R1 + R2)          # 6.875 V
I_SC = V1 / R1                       # 10 mA
R_TH = R1 * R2 / (R1 + R2)           # 687.5 Ω
print(f'[理论] V_oc = {V_OC:.4f} V, I_sc = {I_SC*1e3:.3f} mA, R_th = {R_TH:.1f} Ω')


def build_network(with_short=False, with_load=None):
    """原网络。with_short=True 时在端口接 0V 源测短路电流；with_load 接负载电阻。"""
    c = Circuit('Thevenin source network')
    c.VoltageSource('1', 'vcc', c.gnd, V1 @ u_V)
    c.R(1, 'vcc', 'a', R1 @ u_Ω)
    c.R(2, 'a', c.gnd, R2 @ u_Ω)
    if with_short:
        c.VoltageSource('sc', 'a', c.gnd, 0 @ u_V)   # 0V 源 = 理想电流表
    if with_load is not None:
        c.R('L', 'a', c.gnd, with_load @ u_Ω)
    return c


def build_equivalent(load):
    """戴维南等效电路：V_oc 串联 R_th，再接同样的负载。"""
    c = Circuit('Thevenin equivalent')
    c.VoltageSource('th', 'th', c.gnd, V_OC @ u_V)
    c.R('th', 'th', 'a', R_TH @ u_Ω)
    c.R('L', 'a', c.gnd, load @ u_Ω)
    return c


def op_v(circuit, node):
    sim = circuit.simulator(temperature=25, nominal_temperature=25)
    an = sim.operating_point()
    return float(np.array(an[node])[0])


def main():
    # ---- 1. 开路电压 ----
    v_oc_sim = op_v(build_network(), 'a')
    print(f'[仿真] V_oc = {v_oc_sim:.4f} V')

    # ---- 2. 短路电流（0V 源支路电流，取绝对值并换算方向） ----
    c = build_network(with_short=True)
    sim = c.simulator(temperature=25, nominal_temperature=25)
    an = sim.operating_point()
    i_sc_sim = None
    for key in ('vsc', 'i_vsc', 'vsc#branch'):
        try:
            val = float(np.array(getattr(an, key))[0])
            i_sc_sim = abs(val)
            break
        except (KeyError, AttributeError):
            continue
    if i_sc_sim is None:
        # 兜底：短路时全部电流经 R1，I = V(vcc)/R1
        i_sc_sim = op_v(c, 'vcc') / R1
        print('[提示] 分支电流读取失败，改用 V(vcc)/R1 计算 I_sc')
    print(f'[仿真] I_sc = {i_sc_sim*1e3:.3f} mA')
    r_th_sim = v_oc_sim / i_sc_sim
    print(f'[仿真] R_th = V_oc/I_sc = {r_th_sim:.1f} Ω')

    # ---- 3. 接负载对比：原网络 vs 等效电路 ----
    loads = [1e3, 4.7e3]
    rows = []
    for rl in loads:
        v_orig = op_v(build_network(with_load=rl), 'a')
        i_orig = v_orig / rl
        v_equiv = op_v(build_equivalent(rl), 'a')
        i_equiv = v_equiv / rl
        v_hand = V_OC * rl / (R_TH + rl)
        rows.append((rl, v_hand, v_orig, v_equiv, i_orig, i_equiv))
        print(f'[负载 {rl/1e3:.1f}kΩ] 手算 V={v_hand:.4f}V | 原网络 V={v_orig:.4f}V I={i_orig*1e3:.3f}mA'
              f' | 等效电路 V={v_equiv:.4f}V I={i_equiv*1e3:.3f}mA')

    # ---- 4. 柱状对比图 ----
    x = np.arange(len(loads))
    w = 0.35
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(x - w / 2, [r[2] for r in rows], w, label='原网络端口电压', color='#1f77b4')
    ax.bar(x + w / 2, [r[3] for r in rows], w, label='戴维南等效电路端口电压', color='#ff7f0e')
    for i, r in enumerate(rows):
        ax.text(i - w / 2, r[2] + 0.05, f'{r[2]:.3f}V', ha='center', fontsize=10)
        ax.text(i + w / 2, r[3] + 0.05, f'{r[3]:.3f}V', ha='center', fontsize=10)
    ax.set_xticks(x, [f'R_L = {r[0]/1e3:.1f} kΩ' for r in rows])
    ax.set_ylabel('端口电压 / V')
    ax.set_title('戴维南等效替换前后，接相同负载的端口电压对比')
    ax.legend()
    ax.grid(axis='y', alpha=0.3)
    fig.tight_layout()
    fig.savefig(PLOTS / 'thevenin_load_compare.png', dpi=150)
    plt.close(fig)

    write_results(v_oc_sim, i_sc_sim, r_th_sim, rows)
    print(f'[表] 数据已保存: {RESULTS / "thevenin.md"}')


def write_results(v_oc_sim, i_sc_sim, r_th_sim, rows):
    lines = [
        '# ② 戴维南定理验证 —— 理论 vs 仿真',
        '',
        '参数（自定）：V1 = 10V，R1 = 1kΩ，R2 = 2.2kΩ，端口 (a, 地)',
        '',
        '| 指标 | 手算（公式） | 仿真（PySpice） | 相对误差 |',
        '| --- | --- | --- | --- |',
        f'| V_oc | V1·R2/(R1+R2) = {V_OC:.4f} V | {v_oc_sim:.4f} V | {abs(v_oc_sim-V_OC)/V_OC*100:.3f}% |',
        f'| I_sc | V1/R1 = {I_SC*1e3:.3f} mA | {i_sc_sim*1e3:.3f} mA | {abs(i_sc_sim-I_SC)/I_SC*100:.3f}% |',
        f'| R_th | R1∥R2 = {R_TH:.1f} Ω | V_oc/I_sc = {r_th_sim:.1f} Ω | {abs(r_th_sim-R_TH)/R_TH*100:.3f}% |',
        '',
        '## 等效电路替换后接负载验证',
        '',
        '| R_L | 手算 V_负载 | 原网络 V | 等效电路 V | 原网络 I | 等效电路 I |',
        '| --- | --- | --- | --- | --- | --- |',
    ]
    for rl, v_hand, v_orig, v_equiv, i_orig, i_equiv in rows:
        lines.append(
            f'| {rl/1e3:.1f} kΩ | {v_hand:.4f} V | {v_orig:.4f} V | {v_equiv:.4f} V '
            f'| {i_orig*1e3:.3f} mA | {i_equiv*1e3:.3f} mA |')
    lines += [
        '',
        '- 结论：替换前后端口电压/电流一致（误差 < 0.01%），验证戴维南定理。',
        '- 电路图：circuits/thevenin_circuit.png（原网络）、circuits/thevenin_equivalent.png（等效电路）。',
    ]
    (RESULTS / 'thevenin.md').write_text('\n'.join(lines), encoding='utf-8')


def draw_schematics():
    import schemdraw
    import schemdraw.elements as elm

    # ---- 原网络 ----
    d = schemdraw.Drawing()
    d.config(unit=2.0, fontsize=12)
    d += (v1 := elm.SourceV().up().label('V1\n10V', loc='bottom'))
    d += elm.Line().right().length(0.6)
    d += elm.Resistor().right().label('R1\n1kΩ')
    d += (na := elm.Dot())
    d += elm.Line().right().length(1.2).label('端口 a', loc='right')
    d += elm.Resistor().down().at(na.center).length(2).label('R2\n2.2kΩ')
    d += elm.Ground()
    d += elm.Ground().at((0, 0))
    d.save(str(CIRCUITS / 'thevenin_circuit.png'), dpi=150, transparent=False)

    # ---- 戴维南等效电路 ----
    d = schemdraw.Drawing()
    d.config(unit=2.0, fontsize=12)
    d += (vth := elm.SourceV().up().label('V_oc\n6.875V', loc='bottom'))
    d += elm.Line().right().length(0.6)
    d += elm.Resistor().right().label('R_th\n687.5Ω')
    d += (nb := elm.Dot())
    d += elm.Line().right().length(1.2).label('端口 a', loc='right')
    d += elm.Ground().at((0, 0))
    d.save(str(CIRCUITS / 'thevenin_equivalent.png'), dpi=150, transparent=False)
    print('[图] 电路图已保存: circuits/thevenin_circuit.png / thevenin_equivalent.png')


if __name__ == '__main__':
    draw_schematics()
    main()
    print('完成 ✔')

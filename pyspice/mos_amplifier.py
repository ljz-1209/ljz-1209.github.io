# -*- coding: utf-8 -*-
"""
③ NMOS 共源极放大电路 —— PySpice 仿真（按题固定参数）

给定：VDD=5V、Rg1=60kΩ、Rg2=40kΩ、Rd=2kΩ、Cb1 视为足够大（取 10µF）
      NMOS 模型参数 K=0.8mA/V²、V_th=1V、λ=0.02/V；输入 vi=10mV/1kHz 正弦波

实现说明（重要）：ngspice level-1 模型中 I_D = (KP/2)·(W/L)·(V_GS-V_th)²·(1+λV_DS)，
题目给的 K=0.8mA/V² 对应 KP·(W/L)/2，故取 KP=1.6mA/V²、W=L=1µm。

手算（忽略 λ 的教材常规法）：
    V_GS = VDD·Rg2/(Rg1+Rg2) = 5×40/100 = 2 V        （栅极无电流，分压）
    I_D  = K(V_GS-V_th)² = 0.8m×1 = 0.8 mA
    V_DS = VDD - I_D·Rd = 5 - 1.6 = 3.4 V
    饱和判断：V_DS(3.4V) > V_GS-V_th(1V) → 饱和区 ✓
    gm   = 2K(V_GS-V_th) = 1.6 mS；Av = -gm·Rd = -3.2
手算（含 λ 修正，与仿真同口径）：
    联立 I_D = K(V_GS-V_th)²(1+λV_DS) 与 V_DS = VDD - I_D·Rd
    → I_D ≈ 0.8527 mA，V_DS ≈ 3.2946 V
    gm = 2K(V_GS-V_th)(1+λV_DS) ≈ 1.705 mS；ro = 1/(λI_D) ≈ 58.6 kΩ
    Av = -gm·(Rd∥ro) ≈ -3.30

运行：python mos_amplifier.py
输出：circuits/mos_amplifier_circuit.png
      plots/mos_transient.png、plots/mos_transfer.png
      results/mos_amplifier.md
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

# ---------------- 题目给定参数 ----------------
VDD = 5.0
RG1, RG2 = 60e3, 40e3
RD = 2e3
K = 0.8e-3      # mA/V²
VTH = 1.0
LAM = 0.02

# ---------------- 手算 ----------------
VGS_H = VDD * RG2 / (RG1 + RG2)                    # 2 V
ID_H = K * (VGS_H - VTH) ** 2                      # 0.8 mA（忽略 λ）
VDS_H = VDD - ID_H * RD                            # 3.4 V（忽略 λ）
GM_H = 2 * K * (VGS_H - VTH)                       # 1.6 mS
AV_H = -GM_H * RD                                  # -3.2（忽略 λ，忽略 ro）

# 含 λ 修正：ID = K(VGS-Vth)²(1+λVDS)，VDS = VDD - ID·Rd
a = K * (VGS_H - VTH) ** 2
ID_L = a * (1 + LAM * VDD) / (1 + LAM * a * RD)    # 由两式联立消去 VDS
VDS_L = VDD - ID_L * RD
GM_L = 2 * K * (VGS_H - VTH) * (1 + LAM * VDS_L)
RO_L = 1 / (LAM * ID_L)
AV_L = -GM_L * (RD * RO_L / (RD + RO_L))

print(f'[手算-忽略λ] V_GS={VGS_H:.3f}V  I_D={ID_H*1e3:.3f}mA  V_DS={VDS_H:.3f}V  gm={GM_H*1e3:.3f}mS  Av={AV_H:.3f}')
print(f'[手算-含λ]   I_D={ID_L*1e3:.3f}mA  V_DS={VDS_L:.4f}V  gm={GM_L*1e3:.3f}mS  ro={RO_L/1e3:.1f}kΩ  Av={AV_L:.3f}')


# ---------------- 电路 ----------------
def build_amp():
    c = Circuit('NMOS common-source amplifier')
    # K = KP·(W/L)/2 = 1.6m/2 = 0.8mA/V²
    c.model('NMOS1', 'NMOS', level=1, kp=1.6e-3, vto=VTH, **{'lambda': LAM})
    c.VoltageSource('dd', 'vdd', c.gnd, VDD @ u_V)
    c.R('d', 'vdd', 'd', RD @ u_Ω)
    c.R('g1', 'vdd', 'g', RG1 @ u_Ω)
    c.R('g2', 'g', c.gnd, RG2 @ u_Ω)
    c.SinusoidalVoltageSource('src', 'vin', c.gnd,
                              offset=0 @ u_V, amplitude=10 @ u_mV, frequency=1 @ u_kHz)
    c.Capacitor('b1', 'vin', 'g', 10 @ u_uF)   # Cb1：隔直耦合，1kHz 下阻抗≈16Ω ≪ 24kΩ
    c.MOSFET(1, 'd', 'g', c.gnd, c.gnd, model='NMOS1', w=1 @ u_um, l=1 @ u_um)
    return c


def operating_point():
    c = build_amp()
    sim = c.simulator(temperature=25, nominal_temperature=25)
    an = sim.operating_point()
    v_gs = float(np.array(an['g'])[0])            # 源极接地 → V(g) 即 V_GS
    v_ds = float(np.array(an['d'])[0])
    i_d = (VDD - v_ds) / RD
    sat = v_ds > (v_gs - VTH)
    print(f'[仿真OP] V_GS={v_gs:.4f}V  I_D={i_d*1e3:.3f}mA  V_DS={v_ds:.4f}V  饱和区={sat}')
    return v_gs, i_d, v_ds, sat


def transient():
    c = build_amp()
    sim = c.simulator(temperature=25, nominal_temperature=25)
    an = sim.transient(step_time=2 @ u_us, end_time=5 @ u_ms)

    t = np.array(an.time) * 1e3
    vin = np.array(an['vin']) * 1e3   # mV
    vout = np.array(an['d'])          # V

    # 取最后 2ms 稳态测增益（统一用 mV）
    m = t >= 3.0
    vin_pp = vin[m].max() - vin[m].min()
    vout_mv = vout * 1e3
    vout_pp = vout_mv[m].max() - vout_mv[m].min()
    corr = np.corrcoef(vin[m], vout_mv[m])[0, 1]
    av_sim = -(vout_pp / vin_pp) if corr < 0 else (vout_pp / vin_pp)
    gm_sim = abs(av_sim) / (RD * RO_L / (RD + RO_L))   # 由 Av 与 ro 反推
    print(f'[仿真AC] 输入 {vin_pp:.2f}mVpp → 输出 {vout_pp:.2f}mVpp，Av = {av_sim:.3f}（反相）')
    print(f'[仿真AC] 反推 gm = {gm_sim*1e3:.3f} mS')

    fig, ax = plt.subplots(figsize=(9, 5))
    # 输出去掉直流（约3.29V）后与输入同轴对比，才能看清反相放大
    vout_ac = (vout - vout[m].mean()) * 1e3
    ax.plot(t, vout_ac, lw=2, color='#d62728', label=f'输出 v_out 交流分量（隔直，DC≈{vout.mean():.2f}V）')
    ax.plot(t, vin, lw=1.6, color='#1f77b4', label='输入 v_in（10mV/1kHz）')
    ax.axhline(0, color='gray', ls=':', lw=0.8)
    ax.set_xlabel('时间 t / ms')
    ax.set_ylabel('电压 / mV')
    ax.set_title('NMOS 共源放大：输入/输出波形（输出反相放大，增益≈-3.3）')
    ax.legend(loc='upper right')
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(PLOTS / 'mos_transient.png', dpi=150)
    plt.close(fig)
    return av_sim, gm_sim, vin_pp, vout_pp


def transfer_curve():
    """直流传输特性：固定 V_DS=3.4V 扫 V_GS，验证平方律与 Q 点（用 1Ω 采样电阻测 I_D）"""
    vgs_list = np.arange(0, 3.001, 0.05)
    ids = []
    for vg in vgs_list:
        c = Circuit('MOS transfer sweep')
        c.model('NMOS1', 'NMOS', level=1, kp=1.6e-3, vto=VTH, **{'lambda': LAM})
        c.VoltageSource('gs', 'g', c.gnd, float(vg) @ u_V)
        c.VoltageSource('ds', 'dt', c.gnd, VDS_H @ u_V)
        c.R('sense', 'dt', 'd', 1 @ u_Ω)
        c.MOSFET(1, 'd', 'g', c.gnd, c.gnd, model='NMOS1', w=1 @ u_um, l=1 @ u_um)
        sim = c.simulator(temperature=25, nominal_temperature=25)
        an = sim.operating_point()
        ids.append((float(np.array(an['dt'])[0]) - float(np.array(an['d'])[0])) / 1.0)
    ids = np.array(ids)

    theory = np.where(vgs_list > VTH,
                      K * (vgs_list - VTH) ** 2 * (1 + LAM * VDS_H), 0.0)

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(vgs_list, ids * 1e3, lw=2, color='#d62728', label='仿真 I_D-V_GS（V_DS=3.4V）')
    ax.plot(vgs_list, theory * 1e3, lw=1.4, ls='--', color='#1f77b4',
            label='理论 K(V_GS−V_th)²(1+λV_DS)')
    ax.plot(VGS_H, ID_H * 1e3, 'o', ms=9, color='g')
    ax.annotate(f'Q 点 ({VGS_H:.1f}V, {ID_H*1e3:.2f}mA)', xy=(VGS_H, ID_H * 1e3),
                xytext=(VGS_H + 0.3, ID_H * 1e3 + 0.3),
                arrowprops=dict(arrowstyle='->', color='g'), color='g')
    ax.axvline(VTH, color='gray', ls=':', lw=1)
    ax.text(VTH + 0.03, 0.05, 'V_th=1V', color='gray')
    ax.set_xlabel('V_GS / V')
    ax.set_ylabel('I_D / mA')
    ax.set_title('NMOS 转移特性曲线与静态工作点')
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(PLOTS / 'mos_transfer.png', dpi=150)
    plt.close(fig)
    print('[图] 转移特性曲线已保存: plots/mos_transfer.png')


def draw_schematic():
    import schemdraw
    import schemdraw.elements as elm

    d = schemdraw.Drawing()
    d.config(unit=2.0, fontsize=11)

    # NMOS：源极在下接地，漏极在上
    d += (q := elm.NMos(bulk=False).at((5, 0)).label('T', loc='bottom'))
    d += elm.Ground().at(q.source)

    # 漏极 → Rd → VDD
    d += elm.Line().at(q.drain).up(0.3)
    d += elm.Resistor().up().label('Rd\n2kΩ')
    d += (nv := elm.Dot())
    d += elm.Line().at(nv.center).right(1.2).label('$V_{DD}$=5V\n$V_{out}$=v_d', loc='right')

    # 栅极偏置：VDD → Rg1 → 栅节点 → Rg2 → 地
    d += elm.Line().at(nv.center).left(4.5)
    d += (n1 := elm.Dot())
    d += elm.Resistor().at(n1.center).down().toy(q.gate).label('Rg1\n60kΩ')
    d += (ng := elm.Dot())
    d += elm.Line().at(ng.center).right().tox(q.gate)
    d += elm.Line().at(q.gate).left().tox(ng.center.x)
    d += elm.Resistor().at(ng.center).down().toy(0).label('Rg2\n40kΩ', loc='bottom')
    d += elm.Ground()

    # 输入耦合 Cb1 → 栅节点
    d += elm.Capacitor().at(ng.center).left().label('Cb1\n10µF', loc='bottom')
    d += (vs := elm.SourceSin().down().length(2))
    d += elm.Ground().at(vs.end)
    d += elm.Label().at(vs.center).label('$v_i$\n10mV/1kHz', loc='left', ofst=0.25)

    d.save(str(CIRCUITS / 'mos_amplifier_circuit.png'), dpi=150, transparent=False)
    print('[图] 电路图已保存: circuits/mos_amplifier_circuit.png')


def write_results(v_gs, i_d, v_ds, sat, av_sim, gm_sim, vin_pp, vout_pp):
    lines = [
        '# ③ NMOS 共源放大 —— 理论 vs 仿真',
        '',
        '参数（按题固定）：VDD=5V，Rg1=60kΩ，Rg2=40kΩ，Rd=2kΩ，Cb1=10µF（足够大），',
        'NMOS：K=0.8mA/V²，V_th=1V，λ=0.02/V（ngspice level-1：KP=1.6m，W=L=1µm）',
        '',
        '## 静态工作点（直流 OP）',
        '',
        '| 指标 | 手算·忽略λ（教材法） | 手算·含λ修正 | 仿真（PySpice OP） |',
        '| --- | --- | --- | --- |',
        f'| V_GS | {VGS_H:.3f} V | {VGS_H:.3f} V（分压不受λ影响） | {v_gs:.4f} V |',
        f'| I_D | {ID_H*1e3:.3f} mA | {ID_L*1e3:.3f} mA | {i_d*1e3:.3f} mA |',
        f'| V_DS | {VDS_H:.3f} V | {VDS_L:.4f} V | {v_ds:.4f} V |',
        f'| 饱和区判断 | V_DS>V_GS−V_th ✓ | V_DS>V_GS−V_th ✓ | {"V_DS>V_GS−V_th ✓" if sat else "✗"} |',
        '',
        '## 小信号参数与增益',
        '',
        '| 指标 | 手算·忽略λ | 手算·含λ | 仿真 |',
        '| --- | --- | --- | --- |',
        f'| gm | {GM_H*1e3:.2f} mS | {GM_L*1e3:.2f} mS | {gm_sim*1e3:.2f} mS（由 Av 反推） |',
        f'| ro | ∞（忽略λ） | {RO_L/1e3:.1f} kΩ | —（模型即含 λ） |',
        f'| Av | {AV_H:.2f} | {AV_L:.3f} | {av_sim:.3f} |',
        '',
        f'- 实测：输入 {vin_pp:.2f} mVpp → 输出 {vout_pp:.2f} mVpp，输出与输入反相，约放大 {abs(av_sim):.2f} 倍。',
        '- 结论：含 λ 的手算与仿真一致；忽略 λ 时 I_D/V_DS 偏差约 6%，增益偏差来自 ro 的分流。',
        '- 波形：plots/mos_transient.png；转移特性：plots/mos_transfer.png。',
    ]
    (RESULTS / 'mos_amplifier.md').write_text('\n'.join(lines), encoding='utf-8')
    print(f'[表] 数据已保存: {RESULTS / "mos_amplifier.md"}')


if __name__ == '__main__':
    draw_schematic()
    v_gs, i_d, v_ds, sat = operating_point()
    av_sim, gm_sim, vin_pp, vout_pp = transient()
    transfer_curve()
    write_results(v_gs, i_d, v_ds, sat, av_sim, gm_sim, vin_pp, vout_pp)
    print('完成 ✔')

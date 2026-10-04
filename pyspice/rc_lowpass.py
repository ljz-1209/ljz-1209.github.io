# -*- coding: utf-8 -*-
"""
① RC 低通滤波电路 —— PySpice 仿真（自定参数：R = 1 kΩ，C = 1 µF）

理论值：
    时间常数   τ  = R·C = 1 ms
    截止频率   fc = 1/(2πRC) ≈ 159.15 Hz

仿真内容：
    1. 瞬态分析：1 V / 200 Hz 方波输入，观察充放电指数曲线（叠加理论解析曲线）
    2. 交流分析：10 Hz ~ 1 MHz 扫频，画波特图，标注 -3dB 点

运行：python rc_lowpass.py
输出：plots/rc_lowpass_transient.png
      plots/rc_lowpass_bode.png
      circuits/rc_lowpass_circuit.png   （schemdraw 绘制的电路图）
      results/rc_lowpass.md             （理论 vs 仿真数据表）
"""
from pathlib import Path
import math

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
R_VAL = 1e3      # Ω
C_VAL = 1e-6     # F
TAU = R_VAL * C_VAL            # 1 ms
FC = 1 / (2 * math.pi * R_VAL * C_VAL)   # ≈ 159.15 Hz
print(f'[理论] τ = {TAU*1e3:.3f} ms ， fc = {FC:.2f} Hz')


# ---------------- 电路定义 ----------------
def build_pulse_circuit():
    c = Circuit('RC low-pass filter (transient)')
    # 1V 方波：周期 5 ms（200 Hz），脉宽 2.5 ms，边沿 1 µs
    c.PulseVoltageSource('src', 'vin', c.gnd,
                         initial_value=0 @ u_V, pulsed_value=1 @ u_V,
                         pulse_width=2.5 @ u_ms, period=5 @ u_ms,
                         rise_time=1 @ u_us, fall_time=1 @ u_us)
    c.R(1, 'vin', 'vout', R_VAL @ u_Ω)
    c.C(1, 'vout', c.gnd, C_VAL @ u_F)
    return c


def build_ac_circuit():
    c = Circuit('RC low-pass filter (AC sweep)')
    c.VoltageSource('src', 'vin', c.gnd, 'DC 0 AC 1')  # 小信号 1V 扫频源
    c.R(1, 'vin', 'vout', R_VAL @ u_Ω)
    c.C(1, 'vout', c.gnd, C_VAL @ u_F)
    return c


# ---------------- 瞬态分析 ----------------
def transient():
    c = build_pulse_circuit()
    sim = c.simulator(temperature=25, nominal_temperature=25)
    an = sim.transient(step_time=10 @ u_us, end_time=15 @ u_ms)

    t = np.array(an.time) * 1e3                      # ms
    vin = np.array(an['vin'])
    vout = np.array(an['vout'])

    # 理论解析曲线（分段常值输入的一阶系统精确解：ZOH 递推）
    dt = 10e-6
    v_theory = np.zeros_like(vin)
    for k in range(1, len(vin)):
        v_theory[k] = vin[k] + (v_theory[k - 1] - vin[k]) * math.exp(-dt / TAU)

    # 仿真提取 τ：以输入上升沿中点为 t=0，输出升到 63.2% 的时刻即 τ
    i_start = np.argmax(vin > 0.5)
    i_63 = np.argmax(vout > 0.632 * 1.0)
    tau_sim = (t[i_63] - t[i_start]) * 1e-3
    print(f'[仿真] τ = {tau_sim*1e3:.3f} ms')

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(t, vin, lw=1.2, color='#888', label='输入 v_in（1V 方波 200Hz）')
    ax.plot(t, vout, lw=2.0, color='#d62728', label='仿真输出 v_out')
    ax.plot(t, v_theory, lw=1.4, ls='--', color='#1f77b4', label='理论输出（τ=RC 解析解）')
    ax.axhline(0.632, color='g', ls=':', lw=1)
    ax.annotate('63.2% → τ', xy=(t[i_63], 0.632), xytext=(t[i_63] + 1.2, 0.68),
                arrowprops=dict(arrowstyle='->', color='g'), color='g')
    ax.set_xlabel('时间 t / ms')
    ax.set_ylabel('电压 / V')
    ax.set_title(f'RC 低通滤波：方波响应（R=1kΩ, C=1µF, τ={TAU*1e3:.0f}ms）')
    ax.legend(loc='lower right')
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(PLOTS / 'rc_lowpass_transient.png', dpi=150)
    plt.close(fig)
    return tau_sim


# ---------------- 交流分析（波特图） ----------------
def ac_sweep():
    c = build_ac_circuit()
    sim = c.simulator(temperature=25, nominal_temperature=25)
    an = sim.ac(start_frequency=10 @ u_Hz, stop_frequency=1 @ u_MHz,
                number_of_points=200, variation='dec')

    f = np.array(an.frequency)
    h = np.array(an['vout'])
    mag_db = 20 * np.log10(np.abs(h))
    phase = np.degrees(np.angle(h))

    # 仿真提取 fc：增益首次跌破 -3dB 的频率（线性插值）
    i3 = np.argmax(mag_db < -3.0)
    f1, f2 = f[i3 - 1], f[i3]
    m1, m2 = mag_db[i3 - 1], mag_db[i3]
    fc_sim = f1 + (f2 - f1) * (-3.0 - m1) / (m2 - m1)
    print(f'[仿真] fc = {fc_sim:.2f} Hz（-3dB）')

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 7), sharex=True)
    ax1.semilogx(f, mag_db, lw=2, color='#1f77b4')
    ax1.axhline(-3, color='r', ls=':', lw=1)
    ax1.axvline(FC, color='g', ls=':', lw=1)
    ax1.annotate(f'-3dB @ {fc_sim:.1f} Hz', xy=(fc_sim, -3), xytext=(fc_sim * 3, -8),
                 arrowprops=dict(arrowstyle='->', color='r'), color='r')
    ax1.set_ylabel('增益 / dB')
    ax1.set_title('RC 低通滤波波特图（fc 理论 ≈ 159.15 Hz）')
    ax1.grid(which='both', alpha=0.3)

    ax2.semilogx(f, phase, lw=2, color='#ff7f0e')
    ax2.axvline(FC, color='g', ls=':', lw=1)
    ax2.set_xlabel('频率 f / Hz')
    ax2.set_ylabel('相位 / °')
    ax2.grid(which='both', alpha=0.3)

    fig.tight_layout()
    fig.savefig(PLOTS / 'rc_lowpass_bode.png', dpi=150)
    plt.close(fig)
    return fc_sim


# ---------------- 电路图（schemdraw 绘制） ----------------
def draw_schematic():
    import schemdraw
    import schemdraw.elements as elm

    d = schemdraw.Drawing()
    d.config(unit=2.0, fontsize=12)
    d += (src := elm.SourceSin().up())
    d += elm.Line().right().length(0.6)
    d += elm.Resistor().right().label('R\n1kΩ')
    d += (nd := elm.Dot())
    d += elm.Line().right().length(1.4).label('$v_{out}$', loc='right')
    d += elm.Capacitor().down().at(nd.center).label('C\n1µF')
    d += elm.Ground()
    d += elm.Ground().at((0, 0))
    d += elm.Label().at(src.center).label('$v_{in}$\n1V 方波 200Hz', loc='left', ofst=0.2)
    d.save(str(CIRCUITS / 'rc_lowpass_circuit.png'), dpi=150, transparent=False)
    print(f'[图] 电路图已保存: {CIRCUITS / "rc_lowpass_circuit.png"}')


# ---------------- 结果汇总 ----------------
def write_results(tau_sim, fc_sim):
    lines = [
        '# ① RC 低通滤波 —— 理论 vs 仿真',
        '',
        '参数：R = 1 kΩ，C = 1 µF（自定）',
        '',
        '| 指标 | 手算（公式） | 仿真（PySpice） | 相对误差 |',
        '| --- | --- | --- | --- |',
        f'| 时间常数 τ | RC = 1.000 ms | {tau_sim*1e3:.3f} ms | {abs(tau_sim-TAU)/TAU*100:.2f}% |',
        f'| 截止频率 fc | 1/(2πRC) = {FC:.2f} Hz | {fc_sim:.2f} Hz（-3dB 法） | {abs(fc_sim-FC)/FC*100:.2f}% |',
        '',
        '- τ 仿真提取方法：以方波上升沿中点为起点，输出升到 63.2% 所用时间。',
        '- fc 仿真提取方法：波特图中增益首次跌破 -3dB 处（线性插值）。',
        '- 波形：plots/rc_lowpass_transient.png；波特图：plots/rc_lowpass_bode.png。',
    ]
    (RESULTS / 'rc_lowpass.md').write_text('\n'.join(lines), encoding='utf-8')
    print(f'[表] 数据已保存: {RESULTS / "rc_lowpass.md"}')


if __name__ == '__main__':
    draw_schematic()
    tau_sim = transient()
    fc_sim = ac_sweep()
    write_results(tau_sim, fc_sim)
    print('完成 ✔')

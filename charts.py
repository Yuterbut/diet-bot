"""Графики для отчётов диетолога (matplotlib, backend Agg — сервер без дисплея)."""

import io

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


def week_kcal_chart(series: list[tuple[str, int]], target_kcal: int | None) -> bytes:
    """series — список (дата ISO, ккал) за последние 7 дней, по порядку. Возвращает PNG-байты."""
    labels = [d[5:] for d, _ in series]  # "MM-DD"
    values = [kcal for _, kcal in series]

    colors = ["#e74c3c" if target_kcal and v > target_kcal * 1.1 else "#2ecc71" for v in values]

    fig, ax = plt.subplots(figsize=(7, 4), dpi=120)
    ax.bar(labels, values, color=colors)
    if target_kcal:
        ax.axhline(target_kcal, color="#3498db", linestyle="--", linewidth=1.5,
                    label=f"Норма {target_kcal} ккал")
        ax.legend(loc="upper right")
    ax.set_ylabel("ккал")
    ax.set_title("Калории за неделю")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)
    return buf.read()

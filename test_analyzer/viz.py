import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime   # <-- aqui!

def _plot_time_series(stats, title):
    dates = [datetime.fromisoformat(item["date"]) for item in stats]
    code  = [item["code_lines"] for item in stats]
    test  = [item["test_lines"] for item in stats]

    plt.figure()
    plt.plot(dates, code, label="Código modificado")
    plt.plot(dates, test, label="Testes modificados")
    ax = plt.gca()
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
    plt.xlabel("Data")
    plt.ylabel("Linhas modificadas")
    plt.title(title)
    plt.legend()
    plt.gcf().autofmt_xdate()
    plt.tight_layout()
    plt.show()

def plot_commit_evolution(commit_stats):
    _plot_time_series(commit_stats, "Evolução de linhas modificadas em Commits")

def plot_pr_evolution(pr_stats):
    _plot_time_series(pr_stats, "Evolução de linhas modificadas em PRs")

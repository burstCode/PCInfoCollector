import info_collector

def main() -> None:
    general_info = info_collector.collect_general_info()
    environment_info = info_collector.collect_environment_info()
    hardware_info = info_collector.collect_hardware_info()
    processes_info = info_collector.collect_top_processes()
    logs_info = info_collector.analyze_logs()

    all_data = {
        "general": general_info,
        "environment": environment_info,
        "hardware": hardware_info,
        "processes": processes_info,
        "logs": logs_info
    }

    report_html = info_collector.generate_html_report(all_data)

    info_collector.save_report(report_html)

    print("Отчет сохранен в report.html")


if __name__ == "__main__":
    main()

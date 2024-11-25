import os
import platform
import psutil
import subprocess

from datetime import datetime


def collect_general_info() -> dict:
    """ Сбор общей информации для отчета """
    info = {
        "date_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "pc_name": platform.node(),
        "user_name": os.getlogin(),
        "sudo": "Yes" if os.geteuid() == 0 else "No",
        "os": platform.system(),
        "kernel": platform.release(),
        "uptime": datetime.now() - datetime.fromtimestamp(psutil.boot_time())
    }

    return info

def collect_environment_info() -> dict:
    """ Сбор информации об окружении """

    info = {}

    info["desktop_env"] = os.environ.get("XDG_CURRENT_DESKTOP", "Unknown")

    try:
        xrandr_output = \
            subprocess.check_output(
                "xrandr | grep '*' | awk '{print $1}'", shell=True, text=True).strip()
        info["resolution"] = xrandr_output if xrandr_output else "Unknown"
    except subprocess.CalledProcessError:
        info["resolution"] = "Unknown"
    
    info["shell"] = os.environ.get("SHELL", "Unknown")

    return info

def collect_hardware_info() -> dict:
    """ Сбор информации об аппаратном обеспечении """

    info = {}
    
    info["cpu"] = {
        "name": platform.processor(),
        "frequency": f"{psutil.cpu_freq().max:.2f} MHz" if psutil.cpu_freq() else "Unknown",
        "cores": psutil.cpu_count(logical=False),
        "threads": psutil.cpu_count(logical=True),
    }
    
    virtual_memory = psutil.virtual_memory()
    swap_memory = psutil.swap_memory()
    info["ram"] = {
        "total": f"{round(virtual_memory.total / (1024 ** 3), 2)} GB",
        "used": f"{round(virtual_memory.used / (1024 ** 3), 2)} GB",
        "swap_total": f"{round(swap_memory.total / (1024 ** 3), 2)} GB",
        "swap_used": f"{round(swap_memory.used / (1024 ** 3), 2)} GB",
    }
    
    info["disks"] = [
        {
            "device": partition.device,
            "mountpoint": partition.mountpoint,
            "fstype": partition.fstype,
            "free_space": f"{round(psutil.disk_usage(partition.mountpoint).free / (1024 ** 3), 2)} GB"
        }
        for partition in psutil.disk_partitions(all=False)
    ]
    
    try:
        lspci_output = subprocess.check_output("lspci | grep -i vga", shell=True, text=True).strip()
        info["gpu"] = lspci_output if lspci_output else "None"
    except subprocess.CalledProcessError:
        info["gpu"] = "None"

    return info

def collect_top_processes() -> dict:
    """ Сбор информации о наиболее ресурсоемких приложениях """

    logical_cores = psutil.cpu_count(logical=True)

    info = {}

    for proc in psutil.process_iter(['cpu_percent']):
        try:
            proc.cpu_percent(interval=None) 
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    top_cpu_processes = sorted(
        psutil.process_iter(['pid', 'name', 'cpu_percent']),
        key=lambda p: p.info.get('cpu_percent', 0),
        reverse=True
    )[1:6]

    info["cpu"] = [
        {
            "pid": p.info.get('pid'),
            "name": p.info.get('name', 'Unknown'),
            "cpu": p.info.get('cpu_percent', 0) / logical_cores
        }
        for p in top_cpu_processes
    ]

    top_memory_processes = sorted(
        psutil.process_iter(['pid', 'name', 'memory_percent']),
        key=lambda p: p.info.get('memory_percent', 0),
        reverse=True
    )[:5]

    info["memory"] = [
        {
            "pid": p.info.get('pid'),
            "name": p.info.get('name', 'Unknown'),
            "memory": round(p.info.get('memory_percent', 0), 2)
        }
        for p in top_memory_processes
    ]

    return info

def analyze_logs() -> dict:
    """ Анализ системных логов """

    info = {}

    try:
        log_output = subprocess.check_output("journalctl --no-pager -o short-iso", shell=True, text=True).splitlines()
        
        info["success"] = sum("systemd" in log.lower() and "Started" in log for log in log_output)
        info["warnings"] = sum("warning" in log.lower() for log in log_output)
        info["errors"] = sum("error" in log.lower() for log in log_output)
        
        return info
    except subprocess.CalledProcessError:
        return {"success": 0, "warnings": 0, "errors": 0}

def generate_html_report(data: dict) -> str:
    """ Генерация содержимого HTML-отчета """

    disks_html = "".join(
        f"<tr><td>{disk['device']}</td><td>{disk['mountpoint']}</td><td>{disk['fstype']}</td><td>{disk['free_space']}</td></tr>"
        for disk in data['hardware']['disks']
    )

    top_cpu_html = "".join(
        f"<tr><td>{p['pid']}</td><td>{p['name']}</td><td>{p['cpu']}%</td></tr>"
        for p in data['processes']['cpu']
    )
    top_memory_html = "".join(
        f"<tr><td>{p['pid']}</td><td>{p['name']}</td><td>{p['memory']}%</td></tr>"
        for p in data['processes']['memory']
    )

    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Системный отчет</title>
        <style>
            body {{ font-family: Arial, sans-serif; }}
            h1, h2 {{ color: #333; }}
            table {{ width: 100%; border-collapse: collapse; }}
            th, td {{ border: 1px solid #ccc; padding: 8px; text-align: left; }}
            th {{ background-color: #f4f4f4; }}
        </style>
    </head>
    <body>
        <h1>Отчет о системе</h1>
        <h2>Общая информация</h2>
        <table>
            <tr><th>Свойство</th><th>Значение</th></tr>
            <tr><td>Дата и время</td><td>{data['general']['date_time']}</td></tr>
            <tr><td>Наименование компьютера</td><td>{data['general']['pc_name']}</td></tr>
            <tr><td>Имя пользователя</td><td>{data['general']['user_name']} (sudo: {data['general']['sudo']})</td></tr>
            <tr><td>Операционная система</td><td>{data['general']['os']}</td></tr>
            <tr><td>Ядро</td><td>{data['general']['kernel']}</td></tr>
            <tr><td>Время работы</td><td>{data['general']['uptime']}</td></tr>
        </table>

        <h2>Информация об окружении</h2>
        <table>
            <tr><th>Свойство</th><th>Значение</th></tr>
            <tr><td>Графическая оболочка</td><td>{data['environment']['desktop_env']}</td></tr>
            <tr><td>Разрешение экрана</td><td>{data['environment']['resolution']}</td></tr>
            <tr><td>Оболочка</td><td>{data['environment']['shell']}</td></tr>
        </table>

        <h2>Информация об аппаратном обеспечении</h2>
        <table>
            <tr><th>Компонент</th><th>Значение</th></tr>
            <tr><td>Процессор</td><td>{data['hardware']['cpu']['name']} ({data['hardware']['cpu']['frequency']}), {data['hardware']['cpu']['cores']} ядра(-ер) / {data['hardware']['cpu']['threads']} потока(-ов)</td></tr>
            <tr><td>Оперативная память</td><td>Всего: {data['hardware']['ram']['total']}, Использовано: {data['hardware']['ram']['used']}, Swap: {data['hardware']['ram']['swap_total']} (Использовано: {data['hardware']['ram']['swap_used']})</td></tr>
            <tr><td>Видеокарта</td><td>{data['hardware']['gpu']}</td></tr>
        </table>
        <h3>Информация о диске</h3>
        <table>
            <tr><th>Устройство</th><th>Точка монтирования</th><th>Файловая система</th><th>Свободное пространство</th></tr>
            {disks_html}
        </table>

        <h2>Наиболее ресурсоемкие процессы</h2>
        <h3>По использованию процессора</h3>
        <table>
            <tr><th>Идентификатор процесса (PID)</th><th>Наименование</th><th>Использование процессора (%)</th></tr>
            {top_cpu_html}
        </table>
        <h3>По использованию оперативной памяти</h3>
        <table>
            <tr><th>Идентификатор процесса (PID)</th><th>Наименование</th><th>Использование памяти (%)</th></tr>
            {top_memory_html}
        </table>

        <h2>Анализ логов</h2>
        <table>
            <tr><th>Категория</th><th>Количество</th></tr>
            <tr><td>Успехи</td><td>{data['logs']['success']}</td></tr>
            <tr><td>Предупреждения</td><td>{data['logs']['warnings']}</td></tr>
            <tr><td>Ошибки</td><td>{data['logs']['errors']}</td></tr>
        </table>
    </body>
    </html>
    """

    return html


def save_report(html: str) -> None:
    """ Сохранение отчета на диск с датой и временем в названии """
    filename = datetime.now().strftime("%Y-%m-%d %H_%M_%S") + ".html"
    with open(filename, 'w') as file:
        file.write(html)

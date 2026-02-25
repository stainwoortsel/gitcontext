import json
from datetime import datetime


# Автоматически добавлять в каждый ответ AI
def auto_log_ota(thought, action, result, files):
    log = {
        "timestamp": datetime.now().isoformat(),
        "thought": thought,
        "action": action,
        "result": result,
        "files_affected": files
    }

    # Сохраняем во временный файл
    with open(".gitcontext/temp/ota_log.json", "a") as f:
        json.dump(log, f)
        f.write("\n")

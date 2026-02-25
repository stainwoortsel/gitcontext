#!/usr/bin/env python3
# git-context.py

import os
import json
import yaml
import hashlib
from datetime import datetime
from pathlib import Path
import shutil


class GitContext:
    def __init__(self, repo_path='.'):
        self.repo_path = Path(repo_path)
        self.context_path = self.repo_path / '.gitcontext'
        self.current_branch = self._get_current_branch()

    def init(self):
        """Инициализирует .gitcontext"""
        self.context_path.mkdir(exist_ok=True)
        (self.context_path / 'contexts' / 'main' / 'current').mkdir(parents=True, exist_ok=True)
        (self.context_path / 'contexts' / 'main' / 'history').mkdir(parents=True, exist_ok=True)
        (self.context_path / 'archive').mkdir(exist_ok=True)

        # Создаем индекс
        index = {
            'branches': ['main'],
            'current': 'main',
            'created': datetime.now().isoformat()
        }
        with open(self.context_path / 'index.yaml', 'w') as f:
            yaml.dump(index, f)

        # Создаем начальный контекст main
        self._init_branch_context('main')

        print("✓ GitContext initialized in .gitcontext/")

    def branch(self, name):
        """Создает новую ветку контекста"""
        branch_path = self.context_path / 'contexts' / 'branches' / name
        branch_path.mkdir(parents=True, exist_ok=True)
        (branch_path / 'current').mkdir(exist_ok=True)
        (branch_path / 'history').mkdir(exist_ok=True)
        (branch_path / 'current' / 'ota-logs').mkdir(exist_ok=True)

        # Инициализируем пустой контекст для ветки
        self._init_branch_context(name, parent=self.current_branch)

        # Копируем текущий контекст как основу (опционально)
        parent_context = self._load_current_context()
        self._save_context(name, parent_context)

        # Обновляем индекс
        with open(self.context_path / 'index.yaml', 'r') as f:
            index = yaml.safe_load(f)
        index['branches'].append(name)
        index['current'] = name
        with open(self.context_path / 'index.yaml', 'w') as f:
            yaml.dump(index, f)

        self.current_branch = name
        print(f"✓ Switched to new context branch: {name}")

    def commit(self, message):
        """Создает чекпоинт контекста"""
        # Генерируем ID коммита
        commit_id = hashlib.sha256(
            f"{datetime.now()}{message}".encode()
        ).hexdigest()[:8]

        # Сохраняем текущий контекст в историю
        current = self._load_current_context()
        commit_data = {
            'id': commit_id,
            'message': message,
            'timestamp': datetime.now().isoformat(),
            'context': current,
            'ota_logs': self._collect_recent_ota_logs()
        }

        # Сохраняем в history
        commit_path = self.context_path / 'contexts' / self.current_branch / 'history' / f'commit_{commit_id}'
        commit_path.mkdir(exist_ok=True)

        with open(commit_path / 'commit.yaml', 'w') as f:
            yaml.dump(commit_data, f)

        # Обновляем summary.md (короткая версия для быстрого чтения)
        self._update_summary(current, commit_id, message)

        print(f"✓ Commit {commit_id}: {message}")

    def merge(self, branch_name, squash=True):
        """Сливает ветку в текущую со схлопыванием контекста"""
        if squash:
            # 1. Загружаем всю историю ветки
            branch_context = self._load_branch_history(branch_name)

            # 2. Анализируем OTA-логи для извлечения:
            #    - Ключевых решений
            #    - Отвергнутых альтернатив
            #    - Итогового результата
            analysis = self._analyze_branch_history(branch_context)

            # 3. Сохраняем полный контекст в архив
            archive_name = f"{branch_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            archive_path = self.context_path / 'archive' / archive_name
            archive_path.mkdir(parents=True)

            # Копируем все данные ветки в архив
            branch_source = self.context_path / 'contexts' / 'branches' / branch_name
            if branch_source.exists():
                shutil.copytree(branch_source, archive_path / 'full-context')

            # 4. Сохраняем суммаризированную версию в архив для справки
            with open(archive_path / 'summary.md', 'w') as f:
                f.write(f"# Merge Summary: {branch_name}\n\n")
                f.write(f"Merged: {datetime.now().isoformat()}\n\n")
                f.write("## Key Decisions\n")
                for d in analysis['decisions']:
                    f.write(f"- {d}\n")
                f.write("\n## Rejected Alternatives\n")
                for a in analysis['rejected']:
                    f.write(f"- {a}\n")

            # 5. Обновляем текущий контекст (main) с результатами
            current = self._load_current_context()
            current['merged_branches'] = current.get('merged_branches', [])
            current['merged_branches'].append({
                'branch': branch_name,
                'date': datetime.now().isoformat(),
                'decisions': analysis['decisions'],
                'rejected': analysis['rejected']
            })

            # Обновляем metadata.yaml с ключевыми решениями
            self._save_context(self.current_branch, current)

            # 6. Удаляем ветку (опционально)
            self._delete_branch(branch_name)

            print(f"✓ Merged {branch_name} into {self.current_branch} (context squashed)")
            print(f"  Full context archived to: .gitcontext/archive/{archive_name}/")
        else:
            # Обычное слияние без схлопывания
            self._simple_merge(branch_name)

    def _analyze_branch_history(self, branch_context):
        """Анализирует историю ветки для извлечения ключевой информации"""

        # Здесь будем использовать LLM для анализа
        # Но для proof-of-concept сделаем простой парсинг

        decisions = []
        rejected = []
        ota_logs = []

        # Собираем все OTA-логи
        for commit in branch_context['commits']:
            ota_logs.extend(commit.get('ota_logs', []))

        # TODO: Использовать LLM для анализа OTA-логов
        # Пока заглушка:
        decisions = [
            "Использовать JWT вместо session-based auth",
            "Кэшировать токены в Redis на 15 минут"
        ]
        rejected = [
            "Session-based auth отклонена из-за scalability issues",
            "Кэширование на 60 минут отклонено из-за security"
        ]

        return {
            'decisions': decisions,
            'rejected': rejected,
            'ota_count': len(ota_logs)
        }

    def _smart_squash(self, branch_name):
        """Использует LLM для интеллектуального схлопывания контекста"""

        # Собираем все данные ветки
        branch_data = self._collect_branch_data(branch_name)

        # Формируем промпт для LLM
        prompt = f"""
        Проанализируй историю разработки ветки {branch_name} и извлеки:

        1. Ключевые архитектурные решения (что было решено и почему)
        2. Отвергнутые альтернативы (что пробовали, но не подошло)
        3. Итоговый результат (что получилось в итоге)
        4. Критические инсайты (неочевидные открытия)

        История разработки:
        {json.dumps(branch_data, indent=2)}

        Верни структурированный ответ в формате JSON.
        """

        # TODO: Вызов LLM API
        # Пока возвращаем заглушку
        return {
            'decisions': [...],
            'rejected': [...],
            'result': '...',
            'insights': [...]
        }
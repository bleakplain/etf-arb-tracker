#!/usr/bin/env python3
"""
ETF套利项目日报生成器
每天22:00自动推送当日工作进展

工作原理：
1. 检查当天是否有git提交（00:00-23:59）
2. 如果有提交，生成日报并推送
3. 如果没有提交，不推送（避免空消息）
"""

import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path


def get_today_commits(project_dir: str) -> list:
    """获取今天的git提交记录"""
    cmd = [
        'git', 'log',
        '--since=today',
        '--until=tomorrow',
        '--pretty=format:%h|%ad|%s',
        '--date=format:%Y-%m-%d',
    ]

    try:
        result = subprocess.run(
            cmd,
            cwd=project_dir,
            capture_output=True,
            text=True,
            check=True
        )

        commits = []
        for line in result.stdout.strip().split('\n') if result.stdout.strip() else []:
            parts = line.split('|')
            if len(parts) == 3:
                commits.append({
                    'hash': parts[0],
                    'date': parts[1],
                    'message': parts[2]
                })

        return commits
    except subprocess.CalledProcessError as e:
        print(f"Git命令执行失败: {e}")
        return []


def generate_report(commits: list) -> str:
    """生成日报文本"""
    if not commits:
        return ""

    # 按类型分组
    categories = {
        'feat': [],
        'fix': [],
        'refactor': [],
        'test': [],
        'perf': [],
        'docs': [],
        'chore': [],
        'other': []
    }

    for commit in commits:
        msg = commit['message']
        # 解析提交类型 (feat:, fix:, refactor: 等)
        if ':' in msg:
            type_prefix, content = msg.split(':', 1)
            type_name = type_prefix.strip().split('(')[0]  # 提取主要类型（去除括号中的子模块）

            if type_name in categories:
                categories[type_name].append(content.strip())
            else:
                categories['other'].append(msg)
        else:
            categories['other'].append(msg)

    # 生成报告
    today = datetime.now().strftime('%Y-%m-%d')
    report = f"【📅 ETF套利项目日报 | {today}】\n\n"

    # 按优先级输出
    if categories['feat']:
        report += "✨ **新功能**\n"
        for item in categories['feat']:
            report += f"- {item}\n"
        report += "\n"

    if categories['fix']:
        report += "🐛 **问题修复**\n"
        for item in categories['fix']:
            report += f"- {item}\n"
        report += "\n"

    if categories['perf']:
        report += "⚡ **性能优化**\n"
        for item in categories['perf']:
            report += f"- {item}\n"
        report += "\n"

    if categories['test']:
        report += "🧪 **测试改进**\n"
        for item in categories['test']:
            report += f"- {item}\n"
        report += "\n"

    if categories['refactor']:
        report += "🔧 **代码重构**\n"
        for item in categories['refactor']:
            report += f"- {item}\n"
        report += "\n"

    if categories['docs']:
        report += "📄 **文档更新**\n"
        for item in categories['docs']:
            report += f"- {item}\n"
        report += "\n"

    if categories['chore']:
        report += "🔨 **日常维护**\n"
        for item in categories['chore']:
            report += f"- {item}\n"
        report += "\n"

    if categories['other']:
        report += "📝 **其他**\n"
        for item in categories['other']:
            report += f"- {item}\n"
        report += "\n"

    report += "\n---\n\n**整理：Jude 🦞**"

    return report


def main():
    """主函数"""
    project_dir = Path(__file__).parent.parent

    print(f"检查项目目录: {project_dir}")

    # 获取今天的提交
    commits = get_today_commits(str(project_dir))

    if not commits:
        print("今天没有新的提交，不推送日报")
        sys.exit(0)  # 退出码0表示正常（不需要推送）

    print(f"今天有 {len(commits)} 个提交")

    # 生成日报
    report = generate_report(commits)
    print(f"生成的日报:\n{report}")

    # 这里返回报告内容，由调用方决定如何推送
    # 由于是通过cron调用，报告会通过session传递
    print("\n" + "="*50)
    print("REPORT_TO_SEND:")
    print("="*50)
    print(report)
    print("="*50)


if __name__ == "__main__":
    main()

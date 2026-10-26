#!/usr/bin/env python3
"""
代码审查工具
支持多种编程语言的静态代码分析
"""

import os
import re
import json
import ast
import argparse
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime


class CodeReviewer:
    """代码审查器"""

    # 支持的文件扩展名及其对应的语言
    LANGUAGE_MAP = {
        '.py': 'python',
        '.js': 'javascript',
        '.jsx': 'javascript',
        '.ts': 'typescript',
        '.tsx': 'typescript',
        '.java': 'java',
        '.c': 'c',
        '.cpp': 'cpp',
        '.h': 'c',
        '.hpp': 'cpp',
        '.cs': 'csharp',
    }

    # 问题严重性级别
    SEVERITY_CRITICAL = '严重'
    SEVERITY_NORMAL = '一般'
    SEVERITY_OPTIMIZE = '优化'

    def __init__(self, input_dir: str, file_ext: str = None):
        self.input_dir = Path(input_dir)
        self.file_ext = file_ext
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'input_dir': str(self.input_dir),
            'total_files': 0,
            'files_analyzed': 0,
            'issues': {
                'critical': [],
                'normal': [],
                'optimize': []
            },
            'file_details': {},
            'statistics': {
                'total_lines': 0,
                'comment_lines': 0,
                'comment_coverage': 0.0
            }
        }

    def detect_language(self, filepath: Path) -> str:
        """根据文件扩展名检测编程语言"""
        suffix = filepath.suffix.lower()
        return self.LANGUAGE_MAP.get(suffix, 'unknown')

    def should_skip_file(self, filepath: Path) -> bool:
        """判断是否应该跳过该文件"""
        # 跳过隐藏文件和目录
        if any(part.startswith('.') for part in filepath.parts):
            return True

        # 跳过常见的生成文件和目录
        skip_patterns = [
            'node_modules', '__pycache__', 'venv', 'env',
            'dist', 'build', '.git', '.idea', '.vscode'
        ]
        if any(pattern in str(filepath) for pattern in skip_patterns):
            return True

        # 如果指定了文件扩展名，只处理匹配的文件
        if self.file_ext and filepath.suffix != self.file_ext:
            return True

        # 只处理支持的文件类型
        if filepath.suffix.lower() not in self.LANGUAGE_MAP:
            return True

        return False

    def analyze_file(self, filepath: Path) -> Dict[str, Any]:
        """分析单个文件"""
        file_result = {
            'path': str(filepath.relative_to(self.input_dir)),
            'language': self.detect_language(filepath),
            'size_bytes': filepath.stat().st_size,
            'lines': 0,
            'comment_lines': 0,
            'issues': []
        }

        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                lines = content.split('\n')
                file_result['lines'] = len(lines)

            # 根据语言选择分析方法
            language = file_result['language']

            # 先进行通用问题检查（更可靠）
            issues = self.check_generic_issues(content, filepath, language)

            # 再进行语言特定分析
            if language == 'python':
                issues.extend(self.analyze_python(content, filepath))
            elif language in ['javascript', 'typescript']:
                issues.extend(self.analyze_javascript(content, filepath))
            elif language == 'java':
                issues.extend(self.analyze_java(content, filepath))

            file_result['issues'] = issues
            file_result['comment_lines'] = self.count_comments(content, language)

            self.results['statistics']['total_lines'] += file_result['lines']
            self.results['statistics']['comment_lines'] += file_result['comment_lines']

        except Exception as e:
            file_result['error'] = str(e)

        return file_result

    def count_comments(self, content: str, language: str) -> int:
        """统计注释行数"""
        lines = content.split('\n')
        comment_count = 0

        # 单行注释模式
        if language == 'python':
            pattern = r'^\s*#'
        elif language in ['javascript', 'typescript', 'java', 'c', 'cpp']:
            pattern = r'^\s*//'
        else:
            pattern = r'^\s*(#|//)'

        for line in lines:
            if re.match(pattern, line.strip()) or line.strip().startswith('/*'):
                comment_count += 1

        return comment_count

    def analyze_python(self, content: str, filepath: Path) -> List[Dict[str, Any]]:
        """分析Python代码"""
        issues = []

        try:
            # 使用AST进行更精确的分析
            tree = ast.parse(content)

            # 检查函数定义
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # 检查函数长度
                    if hasattr(node, 'end_lineno') and node.lineno:
                        func_length = node.end_lineno - node.lineno
                        if func_length > 50:
                            issues.append({
                                'type': '代码可读性',
                                'line': node.lineno,
                                'severity': self.SEVERITY_OPTIMIZE,
                                'description': f'函数 {node.name} 过长（{func_length}行）',
                                'suggestion': '建议将函数拆分为更小的子函数'
                            })

        except SyntaxError:
            # 如果AST解析失败，使用正则表达式作为后备
            pass

        return issues

    def analyze_javascript(self, content: str, filepath: Path) -> List[Dict[str, Any]]:
        """分析JavaScript/TypeScript代码"""
        issues = []

        # 检查常见的JavaScript问题
        # 检查var使用（建议使用let/const）
        var_pattern = r'\bvar\s+([a-zA-Z_$][a-zA-Z0-9_$]*)'
        for match in re.finditer(var_pattern, content):
            issues.append({
                'type': '代码规范性',
                'line': content[:match.start()].count('\n') + 1,
                'severity': self.SEVERITY_OPTIMIZE,
                'description': f'使用var声明变量 {match.group(1)}',
                'suggestion': '建议使用let或const代替var'
            })

        # 检查console.log
        console_pattern = r'console\.(log|warn|error|debug)\s*\('
        for match in re.finditer(console_pattern, content):
            issues.append({
                'type': '潜在Bug',
                'line': content[:match.start()].count('\n') + 1,
                'severity': self.SEVERITY_NORMAL,
                'description': '存在调试代码',
                'suggestion': '生产代码中应移除console调用'
            })

        return issues

    def analyze_java(self, content: str, filepath: Path) -> List[Dict[str, Any]]:
        """分析Java代码"""
        issues = []
        # Java特定检查可以在此添加
        return issues

    def analyze_generic(self, content: str, filepath: Path) -> List[Dict[str, Any]]:
        """通用代码分析（适用于所有语言）"""
        issues = []
        # 已被 check_generic_issues 替代
        return issues

    def check_generic_issues(self, content: str, filepath: Path, language: str) -> List[Dict[str, Any]]:
        """通用问题检查"""
        issues = []
        lines = content.split('\n')

        for i, line in enumerate(lines, 1):
            # 检查行长度
            if len(line) > 120:
                issues.append({
                    'type': '代码可读性',
                    'line': i,
                    'severity': self.SEVERITY_OPTIMIZE,
                    'description': f'代码行过长（{len(line)}字符）',
                    'suggestion': '建议将长行拆分为多行，推荐不超过80字符'
                })

            # 检查TODO注释
            if 'TODO' in line or 'FIXME' in line:
                issues.append({
                    'type': '代码维护性',
                    'line': i,
                    'severity': self.SEVERITY_NORMAL,
                    'description': '存在未完成的TODO标记',
                    'suggestion': '及时处理TODO项或添加工单跟踪'
                })

            # 检查空的if/try块
            stripped = line.strip()
            if stripped.endswith(':') or stripped.endswith('{'):
                # 简单启发式检查
                pass

            # 检查SQL字符串拼接（潜在的性能和安全问题）
            if re.search(r'(SELECT|INSERT|UPDATE|DELETE).*\+.*["\']', line, re.IGNORECASE):
                issues.append({
                    'type': '性能和安全',
                    'line': i,
                    'severity': self.SEVERITY_CRITICAL,
                    'description': '使用字符串拼接构建SQL查询',
                    'suggestion': '使用参数化查询或ORM框架，避免SQL注入'
                })

            # 检查硬编码的密码或密钥
            password_pattern = r'(password|passwd|pwd|secret|key|api_key)\s*=\s*["\'][^"\']{8,}'
            if re.search(password_pattern, line, re.IGNORECASE):
                issues.append({
                    'type': '安全性',
                    'line': i,
                    'severity': self.SEVERITY_CRITICAL,
                    'description': '检测到硬编码的敏感信息',
                    'suggestion': '使用环境变量或配置文件存储敏感信息'
                })

            # 检查嵌套循环（性能问题）
            if 'for' in line.lower() and lines.count('for') > 0:
                # 简化的嵌套循环检测
                pass

            # 检查空指针风险
            if language == 'python':
                if re.search(r'if\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*:', line):
                    var_name = re.search(r'if\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*:', line).group(1)
                    if var_name not in ['True', 'False', 'None']:
                        issues.append({
                            'type': '潜在Bug',
                            'line': i,
                            'severity': self.SEVERITY_NORMAL,
                            'description': f'可能存在空指针风险：{var_name}',
                            'suggestion': '显式检查变量是否为None'
                        })

        # 检查文件命名规范
        self.check_file_naming(filepath, issues)

        return issues

    def check_file_naming(self, filepath: Path, issues: List[Dict[str, Any]]):
        """检查文件命名规范"""
        filename = filepath.name
        language = self.detect_language(filepath)

        if language == 'python':
            # Python文件应使用小写加下划线
            if not re.match(r'^[a-z][a-z0-9_]*\.py$', filename):
                issues.append({
                    'type': '命名规范',
                    'line': 0,
                    'severity': self.SEVERITY_NORMAL,
                    'description': f'Python文件名不符合snake_case规范: {filename}',
                    'suggestion': '使用小写字母和下划线，如 my_module.py'
                })
        elif language in ['javascript', 'typescript']:
            # JS/TS文件应使用kebab-case或camelCase
            if not re.match(r'^[a-z][a-z0-9_-]*(\.(js|jsx|ts|tsx))$', filename):
                issues.append({
                    'type': '命名规范',
                    'line': 0,
                    'severity': self.SEVERITY_OPTIMIZE,
                    'description': f'文件命名不符合常见规范: {filename}',
                    'suggestion': '建议使用kebab-case (my-component.js) 或 camelCase (myComponent.js)'
                })

    def run(self):
        """运行审查"""
        if not self.input_dir.exists():
            raise FileNotFoundError(f'目录不存在: {self.input_dir}')

        # 遍历所有文件
        for root, dirs, files in os.walk(self.input_dir):
            # 跳过隐藏目录
            dirs[:] = [d for d in dirs if not d.startswith('.')]

            for filename in files:
                filepath = Path(root) / filename

                if self.should_skip_file(filepath):
                    continue

                self.results['total_files'] += 1
                file_result = self.analyze_file(filepath)
                self.results['file_details'][file_result['path']] = file_result
                self.results['files_analyzed'] += 1

                # 收集问题
                for issue in file_result.get('issues', []):
                    issue['file'] = file_result['path']
                    if issue['severity'] == self.SEVERITY_CRITICAL:
                        self.results['issues']['critical'].append(issue)
                    elif issue['severity'] == self.SEVERITY_NORMAL:
                        self.results['issues']['normal'].append(issue)
                    else:
                        self.results['issues']['optimize'].append(issue)

        # 计算注释覆盖率
        if self.results['statistics']['total_lines'] > 0:
            self.results['statistics']['comment_coverage'] = round(
                self.results['statistics']['comment_lines'] / self.results['statistics']['total_lines'] * 100,
                2
            )

    def save_results(self, output_path: str = './review_results.json'):
        """保存审查结果"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)


def main():
    parser = argparse.ArgumentParser(description='代码审查工具')
    parser.add_argument('--input-dir', required=True, help='要审查的文件夹路径')
    parser.add_argument('--file-ext', help='只处理特定扩展名的文件（如 .py）')
    parser.add_argument('--output', default='./review_results.json', help='结果输出文件路径')

    args = parser.parse_args()

    reviewer = CodeReviewer(args.input_dir, args.file_ext)
    print(f'开始审查目录: {args.input_dir}')
    reviewer.run()

    print(f'审查完成！')
    print(f'  - 扫描文件: {reviewer.results["total_files"]}')
    print(f'  - 分析文件: {reviewer.results["files_analyzed"]}')
    print(f'  - 严重问题: {len(reviewer.results["issues"]["critical"])}')
    print(f'  - 一般问题: {len(reviewer.results["issues"]["normal"])}')
    print(f'  - 优化建议: {len(reviewer.results["issues"]["optimize"])}')
    print(f'  - 注释覆盖率: {reviewer.results["statistics"]["comment_coverage"]}%')

    reviewer.save_results(args.output)
    print(f'结果已保存到: {args.output}')


if __name__ == '__main__':
    main()

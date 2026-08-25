import os
import re
import json
import sys
import subprocess
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Callable, Dict, Optional, Any


# 注意：不导入 function_tool，browser_operator 直接执行脚本


@dataclass
class SkillMetadata:
    """元数据层：始终加载"""
    name: str
    description: str
    folder_path: Path
    has_scripts: bool = False
    tool_bindings: List[str] = field(default_factory=list)
    mcp_bindings: List[str] = field(default_factory=list)


@dataclass
class SkillInstruction:
    """指令层：按需加载"""
    content: str
    source_file: Path

    @classmethod
    def load(cls, folder_path: Path) -> Optional['SkillInstruction']:
        md_files = list(folder_path.glob("*.md"))
        if not md_files:
            return None

        source_file = md_files[0]
        content = source_file.read_text(encoding='utf-8')
        return cls(content=content, source_file=source_file)


@dataclass
class SkillResources:
    """资源层：按需中的按需"""
    scripts: Dict[str, Path] = field(default_factory=dict)
    tools: List[Callable] = field(default_factory=list)
    mcp_servers: List[Any] = field(default_factory=list)

    def execute_script(self, script_name: str, params: Dict[str, Any], verbose: bool = False) -> str:
        """直接执行脚本"""
        if script_name not in self.scripts:
            return f"错误: 脚本 {script_name} 不存在"

        script_path = self.scripts[script_name]

        if verbose:
            print(f"\n   🚀 直接执行脚本:")
            print(f"      路径: {script_path}")
            print(f"      参数: {json.dumps(params, ensure_ascii=False)}")

        try:
            # 使用 CREATE_NO_WINDOW 避免控制台窗口闪烁（Windows）
            kwargs = {}
            if sys.platform == 'win32':
                kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW

            result = subprocess.run(
                [sys.executable, str(script_path), json.dumps(params, ensure_ascii=False)],
                capture_output=True,
                text=True,
                timeout=30,  # 给足够时间
                encoding='utf-8',
                errors='replace',  # 🔥 关键：替换无法解码的字符
                **kwargs
            )

            if verbose:
                print(f"      返回码: {result.returncode}")
                # 只打印安全的内容
                safe_stdout = result.stdout[:200].encode('ascii', 'replace').decode('ascii')
                print(f"      输出: {safe_stdout}...")

            if result.returncode == 0:
                try:
                    # 尝试从输出中提取 JSON（可能有多行，取最后一行）
                    lines = result.stdout.strip().split('\n')
                    json_line = None
                    for line in reversed(lines):
                        line = line.strip()
                        if line and line.startswith('{') and line.endswith('}'):
                            json_line = line
                            break

                    if json_line:
                        output = json.loads(json_line)
                        return output.get("message", f"脚本执行成功: {script_name}")
                    else:
                        return result.stdout.strip() or "执行成功"

                except json.JSONDecodeError:
                    return result.stdout.strip()
            else:
                return f"脚本执行失败: {result.stderr[:500]}"

        except subprocess.TimeoutExpired:
            return f"脚本执行超时: {script_name}"
        except Exception as e:
            return f"脚本执行异常: {str(e)}"


class Skill:
    """渐进式披露的 Skill"""

    def __init__(self, metadata: SkillMetadata):
        self.metadata = metadata
        self._instruction: Optional[SkillInstruction] = None
        self._resources: Optional[SkillResources] = None
        self._tool_registry: Dict[str, Callable] = {}
        self._mcp_registry: Dict[str, Any] = {}

    @property
    def name(self) -> str:
        return self.metadata.name

    @property
    def description(self) -> str:
        return self.metadata.description

    @property
    def instruction(self) -> str:
        """指令层：第一次访问时才加载"""
        if self._instruction is None:
            print(f"   📥 [渐进披露] 加载指令层: {self.name}")
            self._instruction = SkillInstruction.load(self.metadata.folder_path)
            if self._instruction is None:
                raise FileNotFoundError(f"Skill {self.name} 未找到 .md 文件")
        return self._instruction.content

    @property
    def resources(self) -> SkillResources:
        """资源层：第一次访问时才构建"""
        if self._resources is None:
            print(f"   📥 [渐进披露] 加载资源层: {self.name}")
            self._resources = self._build_resources()
        return self._resources

    def _build_resources(self) -> SkillResources:
        """构建资源层：绑定工具、发现脚本（脚本不转为 Tool，保持直接执行）"""
        res = SkillResources()

        # 1. 绑定常规工具（用于 local_knowledge, web_search）
        for tool_name in self.metadata.tool_bindings:
            if tool_name in self._tool_registry:
                res.tools.append(self._tool_registry[tool_name])
                print(f"      🔧 绑定工具: {tool_name}")

        # 2. 绑定 MCP
        for mcp_name in self.metadata.mcp_bindings:
            if mcp_name in self._mcp_registry:
                res.mcp_servers.append(self._mcp_registry[mcp_name])
                print(f"      🔌 绑定 MCP: {mcp_name}")

        # 3. 发现脚本（保持为路径，不转为 SDK Tool）
        # 🔥 browser_operator 直接执行，不包装为 function_tool
        scripts_dir = self.metadata.folder_path / "scripts"
        if scripts_dir.exists():
            for script_file in scripts_dir.glob("*.py"):
                res.scripts[script_file.stem] = script_file
                print(f"      📜 发现脚本: {script_file.name}（直接执行，不转 Tool）")

        return res

    def register_tool(self, name: str, func: Callable):
        self._tool_registry[name] = func
        return self

    def register_mcp(self, name: str, client: Any):
        self._mcp_registry[name] = client
        return self

    def is_loaded(self, level: str = "instruction") -> bool:
        if level == "metadata":
            return True
        elif level == "instruction":
            return self._instruction is not None
        elif level == "resources":
            return self._resources is not None
        return False


class ProgressiveSkillLoader:
    """渐进式 Skill 加载器"""

    def __init__(self, skills_dir: str = None):
        if skills_dir is None:
            # backend/skills（infrastructure/ai/skill_loader.py 往上两级是 backend）
            self.skills_dir = Path(__file__).parent.parent.parent / "skills"
        else:
            self.skills_dir = Path(skills_dir)

        self._skills: Dict[str, Skill] = {}
        self._tool_registry: Dict[str, Callable] = {}
        self._mcp_registry: Dict[str, Any] = {}

    def register_tool(self, name: str, func: Callable):
        self._tool_registry[name] = func
        return self

    def register_mcp(self, name: str, client: Any):
        self._mcp_registry[name] = client
        return self

    def load_metadata(self) -> Dict[str, Skill]:
        """阶段0：仅加载元数据层"""
        if not self.skills_dir.exists():
            raise FileNotFoundError(f"Skill 目录不存在: {self.skills_dir}")

        for skill_folder in self.skills_dir.iterdir():
            if skill_folder.is_dir() and not skill_folder.name.startswith('__'):
                metadata = self._parse_metadata(skill_folder)
                if metadata:
                    skill = Skill(metadata)
                    for name, func in self._tool_registry.items():
                        skill.register_tool(name, func)
                    for name, client in self._mcp_registry.items():
                        skill.register_mcp(name, client)

                    self._skills[skill.name] = skill
                    print(f"✅ [元数据层] 加载 Skill: {skill.name}")

        print(f"📦 共加载 {len(self._skills)} 个 Skills（仅元数据）")
        return self._skills

    def _parse_metadata(self, skill_folder: Path) -> Optional[SkillMetadata]:
        skill_name = skill_folder.name.replace('_skill', '')

        md_files = list(skill_folder.glob("*.md"))
        if not md_files:
            return None

        md_file = md_files[0]

        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                header = f.read(500)
        except Exception:
            header = ""

        description = self._extract_description(header, skill_name)
        tool_bindings = self._extract_bindings(header, 'tools')
        mcp_bindings = self._extract_bindings(header, 'mcp_servers')
        has_scripts = (skill_folder / "scripts").exists()

        return SkillMetadata(
            name=skill_name,
            description=description,
            folder_path=skill_folder,
            has_scripts=has_scripts,
            tool_bindings=tool_bindings,
            mcp_bindings=mcp_bindings
        )

    def _extract_description(self, header: str, default_name: str) -> str:
        if header.startswith('---'):
            match = re.search(r'description:\s*(.+)', header)
            if match:
                return match.group(1).strip()

        lines = header.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('# '):
                return line[2:].strip()
            if line.startswith('## '):
                return line[3:].strip()

        return f"Skill {default_name}"

    def _extract_bindings(self, header: str, key: str) -> List[str]:
        pattern = rf'{key}:\s*(.+)'
        match = re.search(pattern, header)
        if match:
            return [x.strip() for x in match.group(1).split(',') if x.strip()]
        return []

    def get_skill(self, name: str) -> Optional[Skill]:
        return self._skills.get(name)

    def load_skill_full(self, name: str) -> Optional[Skill]:
        """完整加载指定 Skill（渐进披露：触发指令层和资源层加载）"""
        skill = self._skills.get(name)
        if skill is None:
            return None

        # 触发 property 加载
        _ = skill.instruction
        _ = skill.resources

        return skill

    def list_skills_metadata(self) -> str:
        """生成 Skill 目录（仅元数据，供 Selector Agent 使用）"""
        lines = ["\n## 【Skill 列表】仅名称和描述，先选择再加载详情\n"]
        for skill in self._skills.values():
            status = "📦" if skill.is_loaded("instruction") else "⏳"
            lines.append(f"- **{skill.name}** {status}: {skill.description}")
        return "\n".join(lines)


def load_skills_progressive(
        skills_dir: str = None,
        tools: Dict[str, Callable] = None,
        mcp_servers: Dict[str, Any] = None
) -> ProgressiveSkillLoader:
    """
    便捷函数：创建渐进式 Skill 加载器
    """
    loader = ProgressiveSkillLoader(skills_dir)

    if tools:
        for name, func in tools.items():
            loader.register_tool(name, func)

    if mcp_servers:
        for name, client in mcp_servers.items():
            loader.register_mcp(name, client)

    return loader
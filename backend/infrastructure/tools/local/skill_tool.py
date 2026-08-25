"""
Skill 按需加载工具
模型在系统提示词里被要求：先判断用户需求属于哪个技能场景，
再调用 load_skill 工具把对应技能（一份 markdown 指令）加载进对话，
然后严格按技能内容执行。技能文件放在 backend/skills/<name>_skill/SKILL.md。
"""
from agents import function_tool
from infrastructure.ai.skill_loader import ProgressiveSkillLoader
from infrastructure.logging.logger import logger

# 模块加载时扫描 skills/ 目录，得到技能目录（仅元数据层）
_loader = ProgressiveSkillLoader()
_SKILLS = _loader.load_metadata()  # Dict[str, Skill]


def _build_catalog() -> str:
    """生成技能目录文本，注入工具描述供模型决策"""
    lines = []
    for name, skill in _SKILLS.items():
        lines.append(f"- `{name}`：{skill.description}")
    return "\n".join(lines)


_SKILL_CATALOG = _build_catalog()

_LOAD_SKILL_DOCSTRING = f"""
【按需加载技能】根据用户需求动态加载专业工作技能（Skill）。

可用技能：
{_SKILL_CATALOG}

使用规则：
1. 先判断用户需求属于哪个技能场景（销售售前 or 售后技术）
2. 调用本工具加载对应技能，参数 skill_name 传技能名（如 "sales" 或 "aftersales"）
3. 加载成功后，严格按返回的技能内容执行；技能中要求查知识库时再调用 query_rag_knowledge

Args:
    skill_name: 技能名称
"""


@function_tool(description_override=_LOAD_SKILL_DOCSTRING)
async def load_skill(skill_name: str) -> str:
    """
    加载指定技能并返回其完整指令内容。

    Args:
        skill_name: 技能名称
    """
    skill = _SKILLS.get(skill_name)
    if skill is None:
        available = "、".join(_SKILLS.keys())
        return f"❌ 技能 '{skill_name}' 不存在。可用技能: {available}"

    logger.info(f"[Skill] 加载技能: {skill_name}")
    # 去掉 YAML frontmatter（description 已在工具描述里，模型不需要重复看到）
    content = skill.instruction
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            content = parts[2].strip()
    return content

from pathlib import Path
from infrastructure.logging.logger import logger

def load_prompt(prompt_name: str) -> str:
    """
        从 prompts 目录加载提示词文件。

        Args:
            prompt_name: 提示词文件名（不需要加后缀名）

        Returns:
            提示词文件的具体内容
    """
    try:

        current_dir = Path(__file__).parent  # infrastructure/ai/
        prompts_dir = current_dir.parent.parent / "prompts"  # app/prompts/
        
        file_path = prompts_dir / f"{prompt_name}.md"
        
        if not file_path.exists():
            file_path = prompts_dir / f"{prompt_name}.txt"
            
        if not file_path.exists():
            error_msg = f"在 {prompts_dir} 目录下未找到名为 '{prompt_name}' 的提示词文件"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)
            
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            logger.debug(f"成功加载提示词: {prompt_name}")
            return content
            
    except Exception as e:
        logger.error(f"加载提示词 '{prompt_name}' 时发生错误: {str(e)}")
        raise

from .base_model import BaseModel
from .qwen_model import QwenModel
from .wenxin_model import WenxinModel

def get_model(model_type: str, api_key: str) -> BaseModel:
    """
    根据模型类型获取对应的模型实例
    
    Args:
        model_type (str): 模型类型 ('qwen' 或 'wenxin')
        api_key (str): API密钥
        
    Returns:
        BaseModel: 模型实例
    """
    if not api_key:
        raise ValueError("API密钥不能为空")
        
    if model_type == 'qwen':
        return QwenModel(api_key)
    elif model_type == 'wenxin':
        return WenxinModel(api_key)
    else:
        raise ValueError(f"不支持的模型类型: {model_type}") 
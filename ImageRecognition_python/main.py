import json

from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import torch
from PIL import Image
from transformers import AutoModel, AutoTokenizer
import os
import logging

# 初始化日志记录
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

model = None
tokenizer = None

# 从config.json中读取配置
with open('config.json') as config_file:
    config = json.load(config_file)

upload_save= config['upload_save']
cache_dir = config['cache_dir']
# 初始化FastAPI应用
app = FastAPI()

def load_model_and_tokenizer():
    global model, tokenizer
    try:
        model = AutoModel.from_pretrained(
            'openbmb/MiniCPM-Llama3-V-2_5',#文件路径保存在c:\\user\\xxx\\.cache\\huggingface\\hub
            trust_remote_code=True,
            torch_dtype=torch.float16,
            cache_dir=cache_dir
        ).to('cuda' if torch.cuda.is_available() else 'cpu')
        logger.info("Model loaded successfully.")
    except Exception as e:
        logger.error(f"Error loading model: {e}")
        model = None

    try:
        tokenizer = AutoTokenizer.from_pretrained(
            'openbmb/MiniCPM-Llama3-V-2_5',
            trust_remote_code=True,
            cache_dir=cache_dir
        )
        logger.info("Tokenizer loaded successfully.")
    except Exception as e:
        logger.error(f"Error loading tokenizer: {e}")
        tokenizer = None


@app.post("/recognize_image")
async def recognize_image(file: UploadFile = File(...), query: str = Form(...)):
    if file.filename == '':
        raise HTTPException(status_code=400, detail="No selected file")

    # 保存临时图像文件
    temp_image_path = os.path.join(upload_save, file.filename)
    with open(temp_image_path, "wb") as buffer:
        buffer.write(file.file.read())

    # 加载模型和分词器（如未加载）
    if model is None or tokenizer is None:
        load_model_and_tokenizer()

    if model is None or tokenizer is None:
        raise HTTPException(status_code=500, detail="Model or tokenizer could not be loaded.")

    try:
        # 去除问题前缀内容
        if query.lower().startswith('前缀内容'):
            query = query[3:].strip()

        # 图像处理和模型推理
        image = Image.open(temp_image_path).convert('RGB')
        msgs = [{'role': 'user', 'content': query}]
        response = model.chat(
            image=image,
            msgs=msgs,
            tokenizer=tokenizer,
            sampling=True,
            temperature=0.7
        )
        result_text = response if isinstance(response, str) else "未能识别图像内容。"

        return JSONResponse(content={"text": result_text}, status_code=200)
    except Exception as e:
        logger.error(f"Error during image recognition: {e}")
        raise HTTPException(status_code=500, detail="Image recognition failed.")

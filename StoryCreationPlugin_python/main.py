import json

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
import requests

app = FastAPI()

# 从config.json中读取配置
with open('config.json') as config_file:
    config = json.load(config_file)

ollama_url = config['ollama_url']

headers = {'Content-Type': 'application/json; charset=utf-8'}

def call_model(prompt, content):
    messages = [{"role": "system", "content": prompt}, {"role": "user", "content": content}]
    llama_data = {
        "model": "ollama模型",
        "messages": messages,
        "stream": False
    }
    try:
        response = requests.post(ollama_url, headers=headers, json=llama_data)
        response.raise_for_status()
        result = response.json().get('message', {}).get('content', '')
        return result
    except requests.exceptions.RequestException as e:
        print(f"请求模型时出错: {e}")
        return None

@app.post('/generate_outline')
async def generate_outline(request: Request):
    data = await request.json()
    theme = data.get('theme', '')
    if not theme:
        raise HTTPException(status_code=400, detail="缺少故事主题。")

    prompt = (
        f"你是一个故事作家。请根据以下主题生成一个故事大纲：{theme}。\n"
        "请确保大纲包含故事的主要情节、角色设置和关键事件。"
    )
    outline = call_model(prompt, theme)
    if not outline:
        raise HTTPException(status_code=500, detail="无法生成故事大纲。")

    return JSONResponse(content={"outline": outline})

@app.post('/generate_storyline')
async def generate_storyline(request: Request):
    data = await request.json()
    outline = data.get('outline', '')
    if not outline:
        raise HTTPException(status_code=400, detail="缺少故事大纲。")

    prompt = (
        f"基于以下故事大纲，生成一个详细的故事线：{outline}。\n"
        "请确保故事线包含主要的情节发展和关键事件的详细描述。"
    )
    storyline = call_model(prompt, outline)
    if not storyline:
        raise HTTPException(status_code=500, detail="无法生成故事线。")

    return JSONResponse(content={"storyline": storyline})

@app.post('/generate_story')
async def generate_story(request: Request):
    data = await request.json()
    outline = data.get('outline', '')
    storyline = data.get('storyline', '')
    if not outline or not storyline:
        raise HTTPException(status_code=400, detail="缺少故事大纲或故事线。")

    prompt = (
        f"根据以下故事大纲和故事线，生成一个完整的故事：\n\n"
        f"故事大纲：{outline}\n\n"
        f"故事线：{storyline}\n\n"
        "请确保每一部分的故事内容非常的详细且深入，整体内容的字数保持在1000字以上，包括丰富的描述和对话。"
    )
    story = call_model(prompt, outline + storyline)
    if not story:
        raise HTTPException(status_code=500, detail="无法生成完整的故事内容。")

    return JSONResponse(content={"story": story})


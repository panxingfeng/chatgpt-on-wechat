# encoding:utf-8
import json

import arxiv
import fitz  # PyMuPDF
import requests
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
import logging

# 从config.json中读取配置
with open('config.json') as config_file:
    config = json.load(config_file)

ollama_url= config['ollama_url']

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建 FastAPI 应用
app = FastAPI()

# 从 arXiv 搜索论文
def search_arxiv(query):
    client = arxiv.Client()
    search = arxiv.Search(
        query=query,
        max_results=3,
        sort_by=arxiv.SortCriterion.Relevance
    )

    papers = []
    for result in client.results(search):
        paper_info = {
            "title": result.title,
            "authors": [author.name for author in result.authors],
            "abstract": result.summary,
            "url": result.pdf_url
        }
        papers.append(paper_info)

    return papers


# 从 PDF 提取文本
def extract_text_from_pdf(pdf_url):
    response = requests.get(pdf_url)
    with open("paper.pdf", "wb") as f:
        f.write(response.content)

    doc = fitz.open("paper.pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    return text


# 使用 OLLAMA 生成中文摘要
def summarize_in_chinese(article_text):
    headers = {'Content-Type': 'application/json; charset=utf-8'}
    messages = [{
        "role": "system",
        "content": f"文章：\n{article_text}\n\n请用中文总结上文内容，并提炼出核心要点,进行详细的分析,让普通人也能看明白。"
    }]
    data = {
        "model": "ollama模型",
        "messages": messages,
        "stream": True
    }

    response = requests.post(ollama_url, headers=headers, json=data, stream=True)
    if response.status_code == 200:
        try:
            complete_message = ""
            for line in response.iter_lines():
                if line:
                    try:
                        decoded_line = line.decode('utf-8')
                        message = json.loads(decoded_line)
                        content = message.get('message', {}).get('content', '')
                        complete_message += content
                    except json.JSONDecodeError:
                        logger.error("JSON Decode Error: Unable to parse line as JSON.")
            return complete_message
        except Exception as e:
            logger.error(f"Error processing response: {e}")
            return "分析过程中出现解析错误。"
    elif response.status_code == 403:
        logger.error("Access denied: Please check your API endpoint and credentials.")
        return "访问被拒绝，请检查您的API端点和凭证。"
    else:
        logger.error(f"Request failed with status: {response.status_code}")
        return f"请求失败，错误代码：{response.status_code}"


# 综合处理函数
def process_query(query):
    results = search_arxiv(query)
    processed_results = []
    for paper in results:
        # logger.info(f"Title: {paper['title']}")
        # logger.info(f"Abstract: {paper['abstract']}")
        # logger.info(f"PDF URL: {paper['url']}\n")

        # 提取 PDF 文本并生成中文摘要
        article_text = extract_text_from_pdf(paper['url'])
        chinese_summary = summarize_in_chinese(article_text)
        if chinese_summary:
            logger.info(f"Chinese Summary: {chinese_summary}\n")
        processed_results.append({
            "title": paper['title'],
            "abstract": paper['abstract'],
            "pdf_url": paper['url'],
            "chinese_summary": chinese_summary
        })
    return processed_results


@app.post("/api/paperSearch")
async def search_and_summarize(request: Request):
    data = await request.json()
    query = data.get('query', '')
    if not query:
        raise HTTPException(status_code=400, detail="No query provided")

    results = process_query(query)
    return JSONResponse(content=results)


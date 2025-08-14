import asyncio

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from src.scrap import scrap_batch
from src.db import conn_db
import uvicorn

templates = Jinja2Templates(directory="src/resourse/pages")
app = FastAPI()


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):

    cursor = conn_db.Conn()

    items = cursor.get_contents()
    items = sorted(items, key= lambda x: (x.date, x.title))

    if not items:
        return RedirectResponse(url="/false")
    
    cursor.close()
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "items": items
    })

@app.get("/false")
def fail_data(request: Request):
    return templates.TemplateResponse("fail_load.html", {"request":request})


async def asd(): 
        return await scrap_batch()

if __name__ == "__main__":
    a = conn_db.Conn()
    for i in asyncio.run(asd()):
        a.insert_contents(i)

    a.using_redis_info()

    uvicorn.run(app, host="127.0.0.1", port = 8000)

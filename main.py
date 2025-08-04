from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from src.scrap import scrap_linkar, scrap_allfor, scrap_wivity
import uvicorn
templates = Jinja2Templates(directory="src/resourse/pages")
app = FastAPI()


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):

    
    # items = scrap_allfor()
    # items.extend(await scrap_linkar())
    
    items = await scrap_wivity()

    if not items:
        return RedirectResponse(url="/false")
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "items": items  # deque → list 로 변환하여 전달
    })

@app.get("/false")
def fail_data(request: Request):
    return templates.TemplateResponse("fail_load.html", {"request":request})

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port = 8000)